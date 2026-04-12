# ABUS Socket ESPHome Component

Dies ist eine benutzerdefinierte [ESPHome](https://esphome.io/)-Komponente zur Kommunikation mit Cybro-3 Controllern von Cybrotech/Robotina über UDP-Sockets. Die Komponente ermöglicht das Senden und Empfangen von spezifischen, strukturierten Datenpaketen (Bits, Integer, Longs, Reals) per Broadcast im lokalen Netzwerk.

> 🚀 **Schnellstart**: Eine vollständige, einsatzbereite Konfiguration finden Sie in der [`example-esp32.yaml`](example-esp32.yaml) Datei.

## Funktionen

* **UDP-Kommunikation**: Lauscht auf Port 8442 und sendet UDP-Subnetz-Broadcasts (bzw. Fallback auf `255.255.255.255`).
* **Strukturierte Daten**: Unterstützt das Senden und Konfigurieren von Empfangspuffern für `bits` (8-bit), `ints` (16-bit), `longs` (32-bit) und `reals` (Float).
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

Füge den `abus_socket` Block zu deiner YAML-Datei hinzu, um die Komponente zu aktivieren und das Empfangs-Schema festzulegen:

```yaml
abus_socket:
  id: my_abus_socket
  # Optional: Konfiguration für den Empfang von bestimmten Datentypen
  socket_receive:
    socket_id: 1
    num_bit: 8
    num_int: 2
    num_long: 1
    num_real: 1
```

> 📋 **Vollständiges Beispiel**: Eine umfassende Konfiguration mit Sensoren, Schaltern und Automatisierungen finden Sie in [`example-esp32.yaml`](example-esp32.yaml).

### Konfigurationsvariablen:
* **id** (*Optional*, ID): Die ID für diese Komponente. Wird benötigt, um aus Automatisierungen (Actions) darauf zuzugreifen.
* **socket_receive** (*Optional*):
  * **socket_id** (*Erforderlich*, int, templatable): Die zu lauschende Socket-ID.
  * **num_bit** (*Optional*, int): Erwartete Anzahl der Bits/Bytes (Standard: 0).
  * **num_int** (*Optional*, int): Erwartete Anzahl der 16-Bit Integer (Standard: 0).
  * **num_long** (*Optional*, int): Erwartete Anzahl der 32-Bit Integer (Standard: 0).
  * **num_real** (*Optional*, int): Erwartete Anzahl der Floats (Standard: 0).

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

## Abhängigkeiten

Damit diese Komponente kompilieren kann, werden die Hilfsfunktionen `ab_checkValidPacket`, `ab_getHeader` etc. benötigt. Diese müssen über die Header-Datei `abus_helper.h` zur Verfügung gestellt werden.

## Beispieldatei

Eine vollständige Beispielkonfiguration finden Sie in [`example-esp32.yaml`](example-esp32.yaml). Diese zeigt:

* Grundkonfiguration für ESP32 
* WiFi-Setup mit manueller IP und Fallback-Hotspot
* Integration mit Home Assistant über API
* ABUS Socket Konfiguration mit allen Datentypen
* Template-Sensoren für empfangene Daten
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
   ota_password: "sicheres-passwort"
   ```
3. Kompilieren und flashen: 
   ```bash
   esphome compile example-esp32.yaml
   esphome upload example-esp32.yaml
   ```

Die Beispieldatei verwendet Socket-ID 1 und zeigt alle verfügbaren Funktionen der Komponente.

## Repository

Dieses Projekt ist auf GitHub verfügbar: [https://github.com/killer0071234/abus-esphome-lib](https://github.com/killer0071234/abus-esphome-lib)

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