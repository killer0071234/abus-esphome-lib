#pragma once
#include "esphome/core/component.h" // Component base class
#include "esphome/core/log.h"
#include "esphome/components/network/util.h"

#include "esphome/core/automation.h"
#include "esphome/core/defines.h"
#include <vector>

#include "esphome.h"
#include "lwip/err.h"
#include "lwip/sockets.h"
#include "lwip/sys.h"
#include <lwip/netdb.h>
#include "abus_helper.h"
#include "esp_netif.h"
#ifdef USE_SENSOR
#include "esphome/components/sensor/sensor.h"
#endif
#ifdef USE_BINARY_SENSOR
#include "esphome/components/binary_sensor/binary_sensor.h"
#endif

static const char *const TAGS = "abus";

namespace abus_ns {

    // A socket this component listens for, and the sensors its values are published to
    struct ReceiveSocket {
        uint8_t socket_id = 0;
        std::vector<ab_type> layout;  // data types in the order they are expected in the packet
#ifdef USE_SENSOR
        std::vector<std::pair<uint8_t, esphome::sensor::Sensor *>> sensors;  // index in layout, sensor
#endif
#ifdef USE_BINARY_SENSOR
        std::vector<std::pair<uint8_t, esphome::binary_sensor::BinarySensor *>> binary_sensors;
#endif
    };

    class abus_socket : public esphome::Component {
        protected:
            uint16_t port = 8442;
            int sock_ = -1;
            std::vector<ReceiveSocket> receive_sockets_;

            ReceiveSocket *find_receive_socket_(uint8_t socket_id) {
                for (auto &rs : this->receive_sockets_) {
                    if (rs.socket_id == socket_id)
                        return &rs;
                }
                return nullptr;
            }

            // The component and its sensors are set up in any order, so create the socket on first use
            ReceiveSocket &get_or_add_receive_socket_(uint8_t socket_id) {
                ReceiveSocket *rs = this->find_receive_socket_(socket_id);
                if (rs != nullptr)
                    return *rs;
                this->receive_sockets_.emplace_back();
                this->receive_sockets_.back().socket_id = socket_id;
                return this->receive_sockets_.back();
            }
        public:
        void loop() override {
            // 1. Check whether WiFi is connected
            if (!esphome::network::is_connected()) {
                if (sock_ != -1) {
                    close(sock_);
                    sock_ = -1;
                }
                return; 
            }

            // 2. Create the socket only when needed
            if (sock_ < 0) {
                this->setup_socket();
            }

            // 3. Regular receive code: handle a few waiting packets per loop
            if (sock_ >= 0) {
                char rx_buffer[128];
                uint32_t own_address = this->get_own_address();
                for (int i = 0; i < 8; i++) {
                    struct sockaddr_storage source_addr;
                    socklen_t socklen = sizeof(source_addr);
                    int len = recvfrom(sock_, rx_buffer, sizeof(rx_buffer), 0, (struct sockaddr *)&source_addr, &socklen);
                    if (len <= 0)
                        break;
                    // Ignore our own broadcasts
                    auto *source = (struct sockaddr_in *)&source_addr;
                    if (source->sin_family == AF_INET && source->sin_addr.s_addr == own_address)
                        continue;
                    this->process_packet(rx_buffer, len);
                }
            }
        }

        void setup_socket() {
            struct sockaddr_in dest_addr;
            dest_addr.sin_addr.s_addr = htonl(INADDR_ANY);
            dest_addr.sin_family = AF_INET;
            dest_addr.sin_port = htons(this->port);

            // 1. Create the socket
            sock_ = socket(AF_INET, SOCK_DGRAM, IPPROTO_IP);
            if (sock_ < 0) {
                ESP_LOGE(TAGS, "Socket creation failed: errno %d", errno);
                return;
            }

            // 2. Enable the broadcast option (required for sending to 255.255.255.255)
            int broadcast_enable = 1;
            if (setsockopt(sock_, SOL_SOCKET, SO_BROADCAST, &broadcast_enable, sizeof(broadcast_enable)) < 0) {
                ESP_LOGE(TAGS, "Could not set SO_BROADCAST: errno %d", errno);
                close(sock_);
                sock_ = -1;
                return;
            }

            // 3. Enable port reuse (prevents "Address already in use" errors)
            int reuse = 1;
            setsockopt(sock_, SOL_SOCKET, SO_REUSEADDR, &reuse, sizeof(reuse));

            // 4. Switch to non-blocking mode
            fcntl(sock_, F_SETFL, O_NONBLOCK);

            // 5. Bind
            if (bind(sock_, (struct sockaddr *)&dest_addr, sizeof(dest_addr)) < 0) {
                ESP_LOGE(TAGS, "Bind failed: errno %d", errno);
                close(sock_);
                sock_ = -1;
            } else {
                ESP_LOGI(TAGS, "Socket successfully bound for broadcast on port %d", this->port);
            }
        }

        // Add the next data type to the layout of a receive socket
        void add_receive_value(uint8_t socket_id, ab_type type) {
            this->get_or_add_receive_socket_(socket_id).layout.push_back(type);
        }

#ifdef USE_SENSOR
        void add_sensor(uint8_t socket_id, uint8_t index, esphome::sensor::Sensor *sens) {
            this->get_or_add_receive_socket_(socket_id).sensors.push_back({index, sens});
        }
#endif

#ifdef USE_BINARY_SENSOR
        void add_binary_sensor(uint8_t socket_id, uint8_t index, esphome::binary_sensor::BinarySensor *sens) {
            this->get_or_add_receive_socket_(socket_id).binary_sensors.push_back({index, sens});
        }
#endif

        void dump_config() override {
            ESP_LOGCONFIG(TAGS, "ABUS Socket:");
            ESP_LOGCONFIG(TAGS, "  Port: %d", this->port);
            for (const auto &rs : this->receive_sockets_) {
                ESP_LOGCONFIG(TAGS, "  Receive socket %d: %d values, %d bytes", rs.socket_id, (int)rs.layout.size(),
                              ab_getLayoutSize(rs.layout));
            }
        }

        void process_packet(char* recbuf, size_t len) {
            if (!ab_checkValidPacket(recbuf, len))
                return;
            ab_header header = ab_getHeader(recbuf, len);
            // we only handle socket messages
            if (header.dir != 1u || header.typ == 0u)
                return;

            ReceiveSocket *rs = this->find_receive_socket_(header.typ);
            if (rs == nullptr) {
                ESP_LOGV(TAGS, "Ignoring socket %d from %" PRIu32 ": not configured", header.typ, header.from);
                return;
            }

            std::vector<ab_value> values;
            if (!ab_getValues(recbuf, len, header, rs->layout, values))
                return;
            ESP_LOGD(TAGS, "Received socket %d from %" PRIu32 " with %d values", header.typ, header.from, (int)values.size());

#ifdef USE_SENSOR
            for (auto &entry : rs->sensors) {
                if (entry.first < values.size())
                    entry.second->publish_state((float)values[entry.first].value);
            }
#endif
#ifdef USE_BINARY_SENSOR
            for (auto &entry : rs->binary_sensors) {
                if (entry.first < values.size())
                    entry.second->publish_state(values[entry.first].value != 0.0);
            }
#endif
        }

        // Own IPv4 address (network byte order), 0 if not connected
        uint32_t get_own_address() {
            esp_netif_ip_info_t ip_info;
            esp_netif_t *netif = esp_netif_get_handle_from_ifkey("WIFI_STA_DEF");
            if (netif == nullptr || esp_netif_get_ip_info(netif, &ip_info) != ESP_OK)
                return 0;
            return ip_info.ip.addr;
        }

        uint32_t get_subnet_broadcast_address() {
            esp_netif_ip_info_t ip_info;
            esp_netif_t *netif = esp_netif_get_handle_from_ifkey("WIFI_STA_DEF");
            
            if (netif == nullptr || esp_netif_get_ip_info(netif, &ip_info) != ESP_OK) {
                return INADDR_BROADCAST; // Fall back to 255.255.255.255
            }

            // Calculation: (IP OR (NOT subnet mask))
            uint32_t ip = ip_info.ip.addr;
            uint32_t mask = ip_info.netmask.addr;
            return (ip | ~mask);
        }

        void send_raw_data(char *data, size_t len) {
            if (this->sock_ < 0) return;

            struct sockaddr_in dest_addr;
            dest_addr.sin_family = AF_INET;
            dest_addr.sin_port = htons(this->port);
            
            // Use the dynamic subnet broadcast address
            dest_addr.sin_addr.s_addr = this->get_subnet_broadcast_address();

            int err = sendto(this->sock_, data, len, 0, (struct sockaddr *)&dest_addr, sizeof(dest_addr));
            
            if (err < 0) {
                ESP_LOGE(TAGS, "Subnet broadcast failed: errno %d", errno);
            } else {
                char ip_str[16];
                esp_ip4addr_ntoa((esp_ip4_addr_t*)&dest_addr.sin_addr.s_addr, ip_str, sizeof(ip_str));
                ESP_LOGD(TAGS, "Sent to %s (%d bytes)", ip_str, len);
            }
        }

        // Build a socket packet from the tags (in list order) and broadcast it
        void send_values(uint8_t socket_id, const std::vector<ab_value> &values) {
            ab_header header;
            header.dir = 1;
            header.typ = socket_id;
            header.from = 1234;
            header.to = 0;
            header.len = ab_getValuesSize(values) + 4;

            // generate dataarray
            char sendbuf[128];
            if (header.len + 14u >= sizeof(sendbuf)) {
                ESP_LOGE(TAGS, "Socket %d is too large: %d bytes of data, maximum is %d", socket_id,
                         header.len - 4, (int)sizeof(sendbuf) - 19);
                return;
            }
            ESP_LOGD(TAGS, "Sending socket %d with %d values", socket_id, (int)values.size());
            ab_setHeader(sendbuf, sizeof(sendbuf), header);
            // set socket data into it
            ab_setValues(sendbuf, sizeof(sendbuf), values);
            // Add checksum
            ab_setUIntVal(sendbuf, sizeof(sendbuf), header.len + 12, ab_calcCRC(sendbuf, header.len + 12));
            // Send out the data
            this->send_raw_data(sendbuf, header.len + 14);
        }
    };

template<typename... Ts> 
class SendDataAction : public esphome::Action<Ts...> { // <-- make sure the esphome:: prefix is present
    public:
        explicit SendDataAction(abus_socket *parent) : parent_(parent) {}

        // Templatable setters (for lambdas)
        void set_socket_id(esphome::TemplatableValue<int, Ts...> v) { socket_id_v_ = v; }
        void set_bits(esphome::TemplatableValue<std::vector<uint8_t>, Ts...> v) { bit_v_ = v; }
        void set_ints(esphome::TemplatableValue<std::vector<int16_t>, Ts...> v) { int_v_ = v; }
        void set_longs(esphome::TemplatableValue<std::vector<int32_t>, Ts...> v) { long_v_ = v; }
        void set_reals(esphome::TemplatableValue<std::vector<float>, Ts...> v) { real_v_ = v; }

        // Static setters (for {1, 2, 3})
        void set_socket_id_static(int v) { socket_id_v_ = v; }
        void set_bits_static(const std::vector<uint8_t> &v) { bit_v_ = v; }
        void set_ints_static(const std::vector<int16_t> &v) { int_v_ = v; }
        void set_longs_static(const std::vector<int32_t> &v) { long_v_ = v; }
        void set_reals_static(const std::vector<float> &v) { real_v_ = v; }

        // Typed tag for the `values` list (constant or lambda), sent in the order they are added
        void add_value(ab_type type, esphome::TemplatableValue<double, Ts...> v) { values_.push_back({type, v}); }

        void play(const Ts &...x) override {
            int s_id = this->socket_id_v_.value(x...);
            std::vector<ab_value> values;

            if (!this->values_.empty()) {
                // `values` list: evaluate every tag in its configured order
                values.reserve(this->values_.size());
                for (const auto &entry : this->values_)
                    values.push_back({entry.first, entry.second.value(x...)});
            } else {
                // bits / ints / longs / reals: fixed order, all bits first, then ints, longs and reals
                for (uint8_t v : this->bit_v_.value(x...)) values.push_back({AB_BIT, (double)v});
                for (int16_t v : this->int_v_.value(x...)) values.push_back({AB_INT, (double)v});
                for (int32_t v : this->long_v_.value(x...)) values.push_back({AB_LONG, (double)v});
                for (float v : this->real_v_.value(x...)) values.push_back({AB_REAL, (double)v});
            }

            this->parent_->send_values((uint8_t)s_id, values);
        }

    protected:
        abus_socket *parent_;
        esphome::TemplatableValue<int, Ts...> socket_id_v_{};
        esphome::TemplatableValue<std::vector<uint8_t>, Ts...> bit_v_{};
        esphome::TemplatableValue<std::vector<int16_t>, Ts...> int_v_{};
        esphome::TemplatableValue<std::vector<int32_t>, Ts...> long_v_{};
        esphome::TemplatableValue<std::vector<float>, Ts...> real_v_{};
        std::vector<std::pair<ab_type, esphome::TemplatableValue<double, Ts...>>> values_;
    };

}; // abus_ns