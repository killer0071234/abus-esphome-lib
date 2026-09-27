# ABUS Socket ESPHome Component

🇬🇧 **English** | 🇩🇪 [Deutsch](README.de.md)

This is a custom [ESPHome](https://esphome.io/) component for communicating with Cybro-3 controllers from Cybrotech/Robotina over UDP sockets. The component lets you send and receive specific, structured data packets (bits, integers, longs, reals) via broadcast on the local network.

> 🚀 **Quick start**: A complete, ready-to-use configuration is available in [`example-esp32.yaml`](example-esp32.yaml).

## Features

* **UDP communication**: Listens on port 8442 and sends UDP subnet broadcasts (falling back to `255.255.255.255`).
* **Structured data**: Supports sending and configuring receive buffers for `bits` (8-bit), `ints` (16-bit), `longs` (32-bit) and `reals` (float). When sending, the data types can be in any order.
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

Add the `abus_socket` block to your YAML file to enable the component and define which sockets it receives:

```yaml
abus_socket:
  id: my_abus_socket
  # Optional: sockets to receive, one entry per socket
  socket_receive:
    # Free order of data types
    - socket_id: 2
      layout: [bit, real, bit, int, int, long, int]
    # Fixed order: all bits, then ints, longs and reals
    - socket_id: 1
      num_bit: 8
      num_int: 2
      num_long: 1
      num_real: 1
```

> 📋 **Full example**: A comprehensive configuration with sensors, switches and automations is available in [`example-esp32.yaml`](example-esp32.yaml).

### Configuration variables:
* **id** (*Optional*, ID): The ID of this component. Required to access it from automations (actions).
* **socket_receive** (*Optional*, list): Sockets to receive. A single entry without a list is accepted as well. Every `socket_id` may appear only once.
  * **socket_id** (*Required*, int 1–255): The socket ID to listen for.
  * **layout** (*Optional*, list of `bit`, `int`, `long`, `real`): The data types in the order they are sent by the counterpart.
  * **num_bit** / **num_int** / **num_long** / **num_real** (*Optional*, int): Instead of `layout`: the number of bits, 16-bit integers, 32-bit integers and floats, in this fixed order. Cannot be combined with `layout`.

Packets whose data length does not match the layout are ignored and a warning is logged. The device ignores its own broadcasts. A socket can contain at most 110 bytes of data (bit = 1, int = 2, long and real = 4 bytes).

## Sensors

Every received value can be published to its own sensor. `index` is the position of the value in the socket, starting at 0. With `num_*` the index counts through all bits first, then the ints, longs and reals.

```yaml
sensor:
  - platform: abus_socket
    name: "ABUS Temperature"
    socket_id: 2
    index: 1          # the real in [bit, real, bit, ...]
    unit_of_measurement: "°C"

binary_sensor:
  - platform: abus_socket
    name: "ABUS Alarm"
    socket_id: 2
    index: 0          # the first bit
```

* **socket_id** (*Required*, int): A socket configured under `socket_receive`.
* **index** (*Required*, int): Position of the value in the socket. `sensor` accepts `int`, `long` and `real` values, `binary_sensor` accepts `bit` values; the configuration check reports a wrong index or type.
* **abus_socket_id** (*Optional*, ID): The `abus_socket` component, only needed if there is more than one.
* All other options of [sensor](https://esphome.io/components/sensor/) or [binary sensor](https://esphome.io/components/binary_sensor/), such as `name`, `unit_of_measurement` or `filters`.

A sensor is updated every time its socket is received.

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

With `bits`, `ints`, `longs` and `reals` the values are always sent in a fixed order: all bits first, then all ints, longs and reals.

#### Free order of data types (`values`)

If the counterpart expects the data types in a different order, use `values` instead. Every entry has exactly one type (`bit`, `int`, `long` or `real`), and the values are sent exactly in the order of the list. Each value can be a constant or its own lambda:

```yaml
on_...:
  then:
    - abus_socket.send_data:
        id: my_abus_socket
        socket_id: 2
        values:            # layout: [bit, real, bit, int, int, long, int]
          - bit: true
          - real: !lambda return id(my_temperature).state;
          - bit: 0
          - int: 123
          - int: -456
          - long: 123456
          - int: !lambda return millis() / 1000;
```

* **values** (*Optional*, list): Typed values in send order. Cannot be combined with `bits`, `ints`, `longs` or `reals`.
  * **bit** (bool or `0`/`1`, templatable): 1 byte.
  * **int** (int16, templatable): 2 bytes. Lambda results are rounded and limited to −32768…32767.
  * **long** (int32, templatable): 4 bytes. Lambda results are rounded and limited to the int32 range.
  * **real** (float, templatable): 4 bytes. `NaN` is sent as `0.0`.

A socket can carry at most 109 bytes of data; larger sockets are not sent and an error is logged.

## Dependencies

This component ships all required dependencies in the bundled header file [`abus_helper.h`](components/abus_socket/abus_helper.h), which provides the following key functions:

* **Packet validation and parsing**: `ab_checkValidPacket`, `ab_getHeader`, `ab_getSocket`, `ab_getValues`
* **Packet creation**: `ab_setHeader`, `ab_setSocket`, `ab_setValues`, `ab_calcCRC`
* **Data type handling**: `ab_getBoolVal`, `ab_getIntVal`, `ab_getLongVal`, `ab_getRealVal`
* **Socket structures**: `ab_header`, `ab_socket_config`, `ab_socket`, `ab_value`

No additional external dependencies are required — everything needed for Cybro-3 communication is already included.

> ⚠️ **Important**: This component currently supports only the ESP-IDF framework. The Arduino framework is not supported at this time.

## Example file

A complete example configuration is available in [`example-esp32.yaml`](example-esp32.yaml). It demonstrates:

* Basic configuration for ESP32
* WiFi setup with a static IP and fallback hotspot
* Home Assistant integration via the API
* ABUS socket configuration with all data types
* Sensors and binary sensors for received data
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
