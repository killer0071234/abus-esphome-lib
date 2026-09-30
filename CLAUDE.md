# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

An ESPHome external component (`abus_socket`) that talks to Cybrotech/Robotina Cybro-2/Cybro-3 PLCs over their "A-bus" UDP protocol. It broadcasts and receives "sockets" (fixed-layout data packets of bits, int16, int32, floats) on UDP port 8442. Users consume it via `external_components` pointing at this repo; `example-esp32.yaml` is the reference configuration.

Only the ESP-IDF framework is supported (the code uses `lwip` sockets and `esp_netif` directly). Arduino is not.

## Layout

- [components/abus_socket/__init__.py](components/abus_socket/__init__.py): ESPHome codegen. Config schema (`socket_receive` list with `socket_id` 1–255, `num_bit/int/long/real` 0–100, `on_receive` automation), unique-`socket_id` validation, `to_code`, and registration of the `abus_socket.send_data` action.
- [components/abus_socket/abus_socket_component.h](components/abus_socket/abus_socket_component.h): all C++ runtime code, header-only, in namespace `abus_ns`:
  - `abus_socket` (the `Component`): lazily creates, binds and tears down the non-blocking UDP socket in `loop()` according to network state; receives packets, drops its own broadcasts, and dispatches them through `process_packet`; sends to the subnet broadcast address (falls back to 255.255.255.255).
  - `ReceiveTrigger`: one per `on_receive` block, filtered by `socket_id`; `x` is a `const ab_socket &`.
  - `SendDataAction<Ts...>`: templatable `socket_id`/`bits`/`ints`/`longs`/`reals`; writes into the parent's `send_storage_` and then calls `play_send()`.
- [components/abus_socket/abus_helper.h](components/abus_socket/abus_helper.h): protocol library (global namespace, `ab_` prefix): packet structs (`ab_header`, `ab_socket_config`, `ab_socket`), CRC, little-endian get/set helpers, `ab_checkValidPacket`, `ab_getHeader`/`ab_setHeader`, and `ab_getSocket`/`ab_setSocket`.

## Wire format (as implemented)

```
[0..1]  0xAA 0x55
[2..3]  len (uint16 LE) = payload bytes + 4
[4..7]  from (uint32 LE, sender A-bus address)
[8..11] to   (uint32 LE)
[12]    dir  (1 = socket message)
[13]    typ  (socket id; 0 = not a socket)
[14..]  payload: all bits (1 B each), then all ints (2 B), then longs (4 B), then reals (4 B float)
[len+10..len+11] ts_id (uint16)
[len+12..len+13] CRC (uint16 LE over bytes 0..len+11)
```

Total packet size is `len + 14`. Values always arrive grouped by type in the order bits → ints → longs → reals, regardless of how they are declared in the PLC. A received socket is only accepted when `len` matches the configured counts exactly; mismatches are logged as errors and dropped.

## Things to know before changing code

- Everything in the two headers is defined (not just declared) in headers, including non-`inline` functions and global unions (`ab_real`, `ab_int`, ...). This works only because a single translation unit includes them. Adding another `.cpp` that includes `abus_helper.h` will cause duplicate-symbol link errors unless you mark them `inline`.
- Receive and send buffers are both fixed at 128 bytes (`rx_buffer` in `loop()`, `sendbuf` in `play_send()`). The receive payload is limited to 110 bytes; the current sender is safely limited to 109 bytes because `ab_setHeader` uses a strict `>` size check. The YAML schema allows up to 100 of each type, which can exceed those limits. `ab_setSocket` does not bounds-check bits.
- `loop()` reads at most one datagram per iteration.
- The outgoing sender address is the `nad` option (`nad_`), defaulting to the last 3 bytes of the MAC in `setup()`; `to` is always 0 (broadcast).
- Log tags: the component uses `TAGS = "abus"`; the helper uses `TAG = "abus_helper"`.
- A `socket_receive` entry with `on_receive` adds a callback; `process_packet` returns early when no `socket_receive` is configured.
- When you add YAML options, keep the Python schema, the C++ setters, `to_code` and both READMEs in sync.

## Building / testing

There are no unit tests or CI builds. Verification means compiling an ESPHome config with the ESPHome CLI, which the devcontainer (`esphome/esphome` image) provides:

```bash
esphome config example-esp32.yaml    # validate the configuration schema only
esphome compile example-esp32.yaml   # run code generation and a full ESP-IDF build
```

`example-esp32.yaml` pulls the component from **GitHub `main`**, not from the working tree. To test local changes, temporarily switch its `external_components` source to `type: local` with `path: components` (and don't commit that change). It also needs a `secrets.yaml` (git-ignored) with `wifi_ssid`, `wifi_password` and `api_encryption_key`. Build output goes to `.esphome/` (git-ignored).

## Docs and repo conventions

- Documentation exists in two languages: [README.md](README.md) (English) and [README.de.md](README.de.md) (German). Update both together. Code comments and log messages are in English.
- GitHub Actions label PRs by changed paths (`.github/labeler.yml`: `component`, `example`, `documentation`, `devcontainer`, `ci`) and by title or branch via Release Drafter (`bug`, `enhancement`, `breaking-change`). Release Drafter creates `v$RESOLVED_VERSION` drafts, with `enhancement` → minor, `breaking-change` → major, and `bug`/`documentation`/`dependencies` → patch.
