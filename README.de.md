# ABUS Socket ESPHome Component

🇬🇧 [English](README.md) | 🇩🇪 **Deutsch**

Dies ist eine benutzerdefinierte [ESPHome](https://esphome.io/)-Komponente zur Kommunikation mit Cybro-3 Controllern von Cybrotech/Robotina über UDP-Sockets. Die Komponente ermöglicht das Senden und Empfangen von spezifischen, strukturierten Datenpaketen (Bits, Integer, Longs, Reals) per Broadcast im lokalen Netzwerk.

> 🚀 **Schnellstart**: Eine vollständige, einsatzbereite Konfiguration finden Sie in der [`example-esp32.yaml`](example-esp32.yaml) Datei.

## Funktionen

* **UDP-Kommunikation**: Lauscht auf Port 8442 und sendet UDP-Subnetz-Broadcasts (bzw. Fallback auf `255.255.255.255`).
* **Strukturierte Daten**: Unterstützt das Senden und Konfigurieren von Empfangspuffern für `bits` (8-bit), `ints` (16-bit), `longs` (32-bit) und `reals` (Float). Beim Senden können die Datentypen in beliebiger Reihenfolge stehen.
* **Automatische Header-Generierung**: Sendet automatisch korrekte `ab_header` inklusive Längenberechnung und CRC-Prüfsumme.
* **ESPHome Actions**: Stellt die Aktion `abus_socket.send_data` für Automatisierungen bereit, inklusive Template-Unterstützung (Lambdas).

## Installation

### GitHub Repository (empfohlen)

Füge das GitHub-Repository als `external_components` in deiner ESPHome-Konfiguration (YAML) hinzu:

```yaml
external_components:
  - source:
      type: git
      url: https://github.com/killer0071234/abus-esphome-lib
      ref: main # oder ein spezifisches Tag wie v1.0.0
```

### Lokale Installation (Entwicklung)

Alternativ kannst du das lokale Verzeichnis verwenden:

```yaml
external_components:
  - source:
      type: local
      path: components # Pfad zum Ordner, der den 'abus_socket' Ordner enthält
```

> 💡 **Tipp**: Für eine komplette Installationsanleitung mit allen Schritten siehe die [`example-esp32.yaml`](example-esp32.yaml).

## Konfiguration

Füge den `abus_socket` Block zu deiner YAML-Datei hinzu, um die Komponente zu aktivieren und festzulegen, welche Sockets empfangen werden:

```yaml
abus_socket:
  id: my_abus_socket
  # Optional: zu empfangende Sockets, ein Eintrag pro Socket
  socket_receive:
    # Freie Reihenfolge der Datentypen
    - socket_id: 2
      layout: [bit, real, bit, int, int, long, int]
    # Feste Reihenfolge: zuerst alle Bits, dann Ints, Longs und Reals
    - socket_id: 1
      num_bit: 8
      num_int: 2
      num_long: 1
      num_real: 1
```

> 📋 **Vollständiges Beispiel**: Eine umfassende Konfiguration mit Sensoren, Schaltern und Automatisierungen finden Sie in [`example-esp32.yaml`](example-esp32.yaml).

### Konfigurationsvariablen:
* **id** (*Optional*, ID): Die ID für diese Komponente. Wird benötigt, um aus Automatisierungen (Actions) darauf zuzugreifen.
* **socket_receive** (*Optional*, Liste): Zu empfangende Sockets. Ein einzelner Eintrag ohne Liste wird ebenfalls akzeptiert. Jede `socket_id` darf nur einmal vorkommen.
  * **socket_id** (*Erforderlich*, int 1–255): Die Socket-ID, auf die gelauscht wird.
  * **layout** (*Optional*, Liste aus `bit`, `int`, `long`, `real`): Die Datentypen in der Reihenfolge, in der die Gegenstelle sie sendet.
  * **num_bit** / **num_int** / **num_long** / **num_real** (*Optional*, int): Statt `layout`: die Anzahl der Bits, 16-Bit Integer, 32-Bit Integer und Floats, in dieser festen Reihenfolge. Kann nicht mit `layout` kombiniert werden.

Pakete, deren Datenlänge nicht zum Layout passt, werden ignoriert und eine Warnung wird geloggt. Eigene Broadcasts des Geräts werden ignoriert. Empfangene Sockets können höchstens 110 Bytes Daten enthalten (bit = 1, int = 2, long und real = 4 Bytes); gesendete Sockets höchstens 109 Bytes.

## Sensoren

Jeder empfangene Wert kann auf einem eigenen Sensor veröffentlicht werden. `index` ist die Position des Werts im Socket, beginnend bei 0. Bei `num_*` zählt der Index zuerst durch alle Bits, dann durch die Ints, Longs und Reals.

```yaml
sensor:
  - platform: abus_socket
    name: "ABUS Temperatur"
    socket_id: 2
    index: 1          # der Real-Wert in [bit, real, bit, ...]
    unit_of_measurement: "°C"

binary_sensor:
  - platform: abus_socket
    name: "ABUS Alarm"
    socket_id: 2
    index: 0          # das erste Bit
```

* **socket_id** (*Erforderlich*, int): Ein unter `socket_receive` konfigurierter Socket.
* **index** (*Erforderlich*, int): Position des Werts im Socket. `sensor` akzeptiert `int`-, `long`- und `real`-Werte, `binary_sensor` akzeptiert `bit`-Werte; die Konfigurationsprüfung meldet einen falschen Index oder Typ.
* **abus_socket_id** (*Optional*, ID): Die `abus_socket` Komponente, nur nötig, wenn es mehrere gibt.
* Alle weiteren Optionen von [Sensor](https://esphome.io/components/sensor/) bzw. [Binary Sensor](https://esphome.io/components/binary_sensor/), z. B. `name`, `unit_of_measurement` oder `filters`.

Ein Sensor wird jedes Mal aktualisiert, wenn sein Socket empfangen wird.

## Actions

### `abus_socket.send_data`

Diese Aktion sendet Datenpakete per UDP Broadcast an das Netzwerk. Alle Datenfelder (`bits`, `ints`, `longs`, `reals`) sind optional und können weggelassen werden, wenn sie nicht benötigt werden. Es werden auch C++-Lambdas (Templates) unterstützt.

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

#### Parameter der Action:
* **id** (*Erforderlich*, ID): Die in der Konfiguration vergebene ID der `abus_socket` Komponente.
* **socket_id** (*Erforderlich*, int, templatable): Die Ziel-Socket-ID (`typ` im Header).
* **bits** (*Optional*, list[uint8], templatable): Liste von 8-Bit Werten.
* **ints** (*Optional*, list[int16], templatable): Liste von 16-Bit Integer Werten.
* **longs** (*Optional*, list[int32], templatable): Liste von 32-Bit Integer Werten.
* **reals** (*Optional*, list[float], templatable): Liste von Float Werten.

Mit `bits`, `ints`, `longs` und `reals` werden die Werte immer in einer festen Reihenfolge gesendet: zuerst alle Bits, dann alle Ints, Longs und Reals.

#### Freie Reihenfolge der Datentypen (`values`)

Erwartet die Gegenstelle die Datentypen in einer anderen Reihenfolge, verwenden Sie stattdessen `values`. Jeder Eintrag hat genau einen Typ (`bit`, `int`, `long` oder `real`), und die Werte werden genau in der Reihenfolge der Liste gesendet. Jeder Wert kann eine Konstante oder ein eigenes Lambda sein:

```yaml
on_...:
  then:
    - abus_socket.send_data:
        id: my_abus_socket
        socket_id: 2
        values:            # Layout: [bit, real, bit, int, int, long, int]
          - bit: true
          - real: !lambda return id(my_temperature).state;
          - bit: 0
          - int: 123
          - int: -456
          - long: 123456
          - int: !lambda return millis() / 1000;
```

* **values** (*Optional*, list): Typisierte Werte in Sende-Reihenfolge. Kann nicht mit `bits`, `ints`, `longs` oder `reals` kombiniert werden.
  * **bit** (bool oder `0`/`1`, templatable): 1 Byte.
  * **int** (int16, templatable): 2 Bytes. Lambda-Ergebnisse werden gerundet und auf −32768…32767 begrenzt.
  * **long** (int32, templatable): 4 Bytes. Lambda-Ergebnisse werden gerundet und auf den int32-Bereich begrenzt.
  * **real** (float, templatable): 4 Bytes. `NaN` wird als `0.0` gesendet.

Ein Socket kann höchstens 109 Bytes Daten enthalten; größere Sockets werden nicht gesendet und ein Fehler wird geloggt.

## Abhängigkeiten

Diese Komponente enthält alle benötigten Abhängigkeiten in der mitgelieferten Header-Datei [`abus_helper.h`](components/abus_socket/abus_helper.h). Diese stellt folgende wichtige Funktionen bereit:

* **Paket-Validierung und -Parsing**: `ab_checkValidPacket`, `ab_getHeader`, `ab_getSocket`, `ab_getValues`
* **Paket-Erstellung**: `ab_setHeader`, `ab_setSocket`, `ab_setValues`, `ab_calcCRC`
* **Datentyp-Manipulation**: `ab_getBoolVal`, `ab_getIntVal`, `ab_getLongVal`, `ab_getRealVal`
* **Socket-Strukturen**: `ab_header`, `ab_socket_config`, `ab_socket`, `ab_value`

Es sind keine zusätzlichen externen Abhängigkeiten erforderlich - alles was für die Cybro-3 Kommunikation benötigt wird, ist bereits enthalten.

> ⚠️ **Wichtiger Hinweis**: Diese Komponente unterstützt aktuell nur das ESP-IDF Framework. Arduino Framework wird derzeit nicht unterstützt.

## Beispieldatei

Eine vollständige Beispielkonfiguration finden Sie in [`example-esp32.yaml`](example-esp32.yaml). Diese zeigt:

* Grundkonfiguration für ESP32 
* WiFi-Setup mit manueller IP und Fallback-Hotspot
* Integration mit Home Assistant über API
* ABUS Socket Konfiguration mit allen Datentypen
* Sensoren und Binärsensoren für empfangene Daten
* Schalter und Buttons für das Senden von Daten
* Automatisierte zyklische Übertragung
* Zeitbasierte Aktionen

### Schnellstart mit der Beispieldatei:

1. Kopieren Sie `example-esp32.yaml` und `secrets.yaml` in Ihr ESPHome-Verzeichnis
2. Passen Sie die `secrets.yaml` mit Ihren WiFi-Zugangsdaten an:
   ```yaml
   wifi_ssid: "Ihr-WiFi-Name"
   wifi_password: "Ihr-WiFi-Passwort"
   api_encryption_key: "32-Zeichen-Base64-Schlüssel"
   ```
3. Kompilieren und flashen: 
   ```bash
   esphome compile example-esp32.yaml
   esphome upload example-esp32.yaml
   ```

Die Beispieldatei verwendet Socket-ID 1 und zeigt alle verfügbaren Funktionen der Komponente.

## Repository

Dieses Projekt ist auf GitHub verfügbar: [https://github.com/killer0071234/abus-esphome-lib](https://github.com/killer0071234/abus-esphome-lib)

**Quelle**: Diese ESPHome-Komponente basiert auf der ursprünglichen ESP_ABUS Library: [https://github.com/killer0071234/esp_abus](https://github.com/killer0071234/esp_abus)

## Versioning

Es wird empfohlen, spezifische Tags oder Releases zu verwenden anstatt den `main` Branch:

```yaml
external_components:
  - source:
      type: git
      url: https://github.com/killer0071234/abus-esphome-lib
      ref: v1.0.0  # Verwende spezifische Releases für stabile Installationen
```

## Support und Issues

Falls du Probleme findest oder Verbesserungsvorschläge hast:

1. **Issues**: Erstelle ein [GitHub Issue](https://github.com/killer0071234/abus-esphome-lib/issues)
2. **Diskussionen**: Verwende [GitHub Discussions](https://github.com/killer0071234/abus-esphome-lib/discussions) für Fragen und Diskussionen

## Mitwirkende

Beiträge sind willkommen! Bitte:

1. Forke das Repository
2. Erstelle einen Feature-Branch (`git checkout -b feature/AmazingFeature`)
3. Commit deine Änderungen (`git commit -m 'Add some AmazingFeature'`)
4. Push zum Branch (`git push origin feature/AmazingFeature`)
5. Öffne eine Pull Request

## Lizenz

Dieses Projekt steht unter der [MIT Lizenz](LICENSE) - siehe die LICENSE-Datei für Details.