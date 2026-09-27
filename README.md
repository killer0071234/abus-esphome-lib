# ABUS Socket ESPHome Component

🇬🇧 **English** | 🇩🇪 [Deutsch](README.de.md)

This is a custom [ESPHome](https://esphome.io/) component for communicating with Cybro-3 controllers from Cybrotech/Robotina over UDP sockets. The component lets you send and receive specific, structured data packets (bits, integers, longs, reals) via broadcast on the local network.

> 🚀 **Quick start**: A complete, ready-to-use configuration is available in [`example-esp32.yaml`](example-esp32.yaml).

## Features

* **UDP communication**: Listens on port 8442 and sends UDP subnet broadcasts (falling back to `255.255.255.255`).
* **Structured data**: Supports sending and configuring receive buffers for `bits` (8-bit), `ints` (16-bit), `longs` (32-bit) and `reals` (float).
* **Automatic header generation**: Automatically sends a correct `ab_header`, including length calculation and CRC checksum.
* **ESPHome actions**: Provides the `abus_socket.send_data` action for automations, including template support (lambdas).

## Installation

### GitHub repository (recommended)

Add the GitHub repository as `external_components` in your ESPHome configuration (YAML):

```yaml
external_components:
  - source:
      type: git
      url: https://github.com/killer0071234/abus-esphome-lib
      ref: main # or a specific tag such as v1.0.0
```

### Local installation (development)

Alternatively, you can use the local directory:

```yaml
external_components:
  - source:
      type: local
      path: components # path to the folder containing the 'abus_socket' folder
```

> 💡 **Tip**: For a complete step-by-step setup, see [`example-esp32.yaml`](example-esp32.yaml).

## Configuration

Add the `abus_socket` block to your YAML file to enable the component and define the receive schema:

```yaml
abus_socket:
  id: my_abus_socket
  # Optional: configuration for receiving specific data types
  socket_receive:
    socket_id: 1
    num_bit: 8
    num_int: 2
    num_long: 1
    num_real: 1
```

> 📋 **Full example**: A comprehensive configuration with sensors, switches and automations is available in [`example-esp32.yaml`](example-esp32.yaml).

### Configuration variables:
* **id** (*Optional*, ID): The ID of this component. Required to access it from automations (actions).
* **socket_receive** (*Optional*):
  * **socket_id** (*Required*, int, templatable): The socket ID to listen on.
  * **num_bit** (*Optional*, int): Expected number of bits/bytes (default: 0).
  * **num_int** (*Optional*, int): Expected number of 16-bit integers (default: 0).
  * **num_long** (*Optional*, int): Expected number of 32-bit integers (default: 0).
  * **num_real** (*Optional*, int): Expected number of floats (default: 0).

## Actions

### `abus_socket.send_data`

This action sends data packets to the network via UDP broadcast. All data fields (`bits`, `ints`, `longs`, `reals`) are optional and can be omitted if not needed. C++ lambdas (templates) are supported as well.

```yaml
on_...:
  then:
    - abus_socket.send_data:
        id: my_abus_socket
        socket_id: 2
        bits: [1, 0, 1]
        ints: [256, 1024]
        longs: [100000]
        reals: [23.5, 42.0]
```

#### Action parameters:
* **id** (*Required*, ID): The ID of the `abus_socket` component as set in the configuration.
* **socket_id** (*Required*, int, templatable): The target socket ID (`typ` in the header).
* **bits** (*Optional*, list[uint8], templatable): List of 8-bit values.
* **ints** (*Optional*, list[int16], templatable): List of 16-bit integer values.
* **longs** (*Optional*, list[int32], templatable): List of 32-bit integer values.
* **reals** (*Optional*, list[float], templatable): List of float values.

## Dependencies

This component ships all required dependencies in the bundled header file [`abus_helper.h`](components/abus_socket/abus_helper.h), which provides the following key functions:

* **Packet validation and parsing**: `ab_checkValidPacket`, `ab_getHeader`, `ab_getSocket`
* **Packet creation**: `ab_setHeader`, `ab_setSocket`, `ab_calcCRC`
* **Data type handling**: `ab_getBoolVal`, `ab_getIntVal`, `ab_getLongVal`, `ab_getRealVal`
* **Socket structures**: `ab_header`, `ab_socket_config`, `ab_socket`

No additional external dependencies are required — everything needed for Cybro-3 communication is already included.

> ⚠️ **Important**: This component currently supports only the ESP-IDF framework. The Arduino framework is not supported at this time.

## Example file

A complete example configuration is available in [`example-esp32.yaml`](example-esp32.yaml). It demonstrates:

* Basic configuration for ESP32
* WiFi setup with a static IP and fallback hotspot
* Home Assistant integration via the API
* ABUS socket configuration with all data types
* Template sensors for received data
* Switches and buttons for sending data
* Automated cyclic transmission
* Time-based actions

### Quick start with the example file:

1. Copy `example-esp32.yaml` and `secrets.yaml` into your ESPHome directory
2. Fill in `secrets.yaml` with your WiFi credentials:
   ```yaml
   wifi_ssid: "Your-WiFi-Name"
   wifi_password: "Your-WiFi-Password"
   api_encryption_key: "32-character-base64-key"
   ota_password: "secure-password"
   ```
3. Compile and flash:
   ```bash
   esphome compile example-esp32.yaml
   esphome upload example-esp32.yaml
   ```

The example file uses socket ID 1 and demonstrates all available features of the component.

## Repository

This project is available on GitHub: [https://github.com/killer0071234/abus-esphome-lib](https://github.com/killer0071234/abus-esphome-lib)

**Source**: This ESPHome component is based on the original ESP_ABUS library: [https://github.com/killer0071234/esp_abus](https://github.com/killer0071234/esp_abus)

## Versioning

It is recommended to use specific tags or releases instead of the `main` branch:

```yaml
external_components:
  - source:
      type: git
      url: https://github.com/killer0071234/abus-esphome-lib
      ref: v1.0.0  # use specific releases for stable installations
```

## Support and issues

If you run into problems or have suggestions for improvement:

1. **Issues**: Open a [GitHub issue](https://github.com/killer0071234/abus-esphome-lib/issues)
2. **Discussions**: Use [GitHub Discussions](https://github.com/killer0071234/abus-esphome-lib/discussions) for questions and discussions

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a pull request

## License

This project is licensed under the [MIT License](LICENSE) — see the LICENSE file for details.
