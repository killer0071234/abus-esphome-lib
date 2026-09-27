#pragma once
#include "esphome/core/component.h" // Component base class
#include "esphome/core/log.h"
#include "esphome/components/network/util.h"

#include "esphome/core/automation.h"
#include <vector>

#include "esphome.h"
#include "lwip/err.h"
#include "lwip/sockets.h"
#include "lwip/sys.h"
#include <lwip/netdb.h>
#include "abus_helper.h"
#include "esp_netif.h"

static const char *const TAGS = "abus";

namespace abus_ns {

    class abus_socket : public esphome::Component {
        protected:
            uint16_t port = 8442;
            int sock_ = -1;
            ab_socket_config sock_cnf_rec;  // Socket config for receiving a socket
            ab_socket send_storage_;
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

            // 3. Regular receive code
            if (sock_ >= 0) {
                char rx_buffer[128];
                struct sockaddr_storage source_addr;
                socklen_t socklen = sizeof(source_addr);
                int len = recvfrom(sock_, rx_buffer, sizeof(rx_buffer), 0, (struct sockaddr *)&source_addr, &socklen);
                if (len > 0) {
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

        void set_socket_receive_config(uint8_t id, uint8_t num_bit, uint8_t num_int, uint8_t num_long, uint8_t num_real){
            this->sock_cnf_rec.socket_id = id;
            this->sock_cnf_rec.bitcount = num_bit;
            this->sock_cnf_rec.intcount = num_int;
            this->sock_cnf_rec.longcount = num_long;
            this->sock_cnf_rec.realcount = num_real;
        }


        void process_packet(char* recbuf, size_t len) {
            if (ab_checkValidPacket(recbuf, len))
            {
                ab_header header = ab_getHeader(recbuf, len);
                // we got a socket message
                if (header.dir == 1u && header.typ > 0u)
                {
                    //ESP_LOGD(TAGS, "<SOCK: ID: %3d: ", header.typ);

                    ab_socket sock = ab_getSocket(recbuf, len, header, this->sock_cnf_rec);
                    // TODO: here we need the code to parse the received data
                }
            }
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

        // Setter for the action (called by SendDataAction)
        void set_send_data(int id, const std::vector<uint8_t> &bits, 
                        const std::vector<int16_t> &ints, 
                        const std::vector<int32_t> &longs, 
                        const std::vector<float> &reals) {
            
            send_storage_.config.socket_id = (uint8_t)id;
            send_storage_.sender = 1234;
            send_storage_.bitdata = bits;
            send_storage_.intdata = ints;
            send_storage_.longdata = longs;
            send_storage_.realdata = reals;
            send_storage_.socket_valid = true;

        }

        void play_send() {
            if (!send_storage_.socket_valid) return;
            // generate the header
            ab_header header;
            header.dir = 1;
            header.typ = send_storage_.config.socket_id;
            header.from = send_storage_.sender;
            header.to = 0;
            ESP_LOGD(TAGS, "socket.bitdata.size()=%d", send_storage_.bitdata.size());
            ESP_LOGD(TAGS, "socket.intdata.size()=%d", send_storage_.intdata.size());
            ESP_LOGD(TAGS, "socket.longdata.size()=%d", send_storage_.longdata.size());
            ESP_LOGD(TAGS, "socket.realdata.size()=%d", send_storage_.realdata.size());
            header.len = send_storage_.bitdata.size() + send_storage_.intdata.size() * 2 + send_storage_.longdata.size() * 4 + send_storage_.realdata.size() * 4 + 4;

            // generate dataarray
            char sendbuf[128];
            ab_setHeader(sendbuf, sizeof(sendbuf), header);
            // set socket data into it
            ab_setSocket(sendbuf, sizeof(sendbuf), send_storage_);
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
        void play(const Ts &...x) override {
            // 1. Extract all values from the templates
            int s_id = this->socket_id_v_.value(x...);
            auto bits = this->bit_v_.value(x...);
            auto ints = this->int_v_.value(x...);
            auto longs = this->long_v_.value(x...);
            auto reals = this->real_v_.value(x...);

            // 2. Write them into the component's central ab_socket storage
            this->parent_->set_send_data(s_id, bits, ints, longs, reals);

            // 3. Trigger the send
            this->parent_->play_send();
        }

    protected:
        abus_socket *parent_;
        esphome::TemplatableValue<int, Ts...> socket_id_v_{};
        esphome::TemplatableValue<std::vector<uint8_t>, Ts...> bit_v_{};
        esphome::TemplatableValue<std::vector<int16_t>, Ts...> int_v_{};
        esphome::TemplatableValue<std::vector<int32_t>, Ts...> long_v_{};
        esphome::TemplatableValue<std::vector<float>, Ts...> real_v_{};
    };

}; // abus_ns