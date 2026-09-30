# ABUS Socket ESPHome Component

🇬🇧 [English](README.md) | 🇩🇪 **Deutsch**

Dies ist eine benutzerdefinierte [ESPHome](https://esphome.io/)-Komponente zur Kommunikation mit Cybro-3 Controllern von Cybrotech/Robotina über UDP-Sockets. Die Komponente ermöglicht das Senden und Empfangen von spezifischen, strukturierten Datenpaketen (Bits, Integer, Longs, Reals) per Broadcast im lokalen Netzwerk.

> 🚀 **Schnellstart**: Eine vollständige, einsatzbereite Konfiguration finden Sie in der [`example-esp32.yaml`](example-esp32.yaml) Datei.

## Funktionen

* **UDP-Kommunikation**: Lauscht auf Port 8442 und sendet UDP-Subnetz-Broadcasts (bzw. Fallback auf `255.255.255.255`).
* **Strukturierte Daten**: Unterstützt das Senden und Konfigurieren von Empfangspuffern für `bits` (8-bit), `ints` (16-bit), `longs` (32-bit) und `reals` (Float).
* **Automatische Header-Generierung**: Sendet automatisch korrekte `ab_header` inklusive Längenberechnung und CRC-Prüfsumme.
* **Sockets empfangen**: Wertet eingehende Sockets mit der konfigurierten `socket_id` und Struktur aus und übergibt sie an `on_receive`-Automatisierungen. Eigene Broadcasts des Geräts werden ignoriert.
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
    - socket_id: 1
      num_bit: 8
      num_int: 2
      num_long: 1
      num_real: 1
      # Optional: wird für jeden gültig empfangenen Socket ausgeführt (x ist der empfangene Socket)
      on_receive:
        - lambda: |-
            id(my_bit).publish_state(x.bitdata[0]);
            id(my_int).publish_state(x.intdata[0]);
            id(my_long).publish_state(x.longdata[0]);
            id(my_real).publish_state(x.realdata[0]);
    - socket_id: 2
      num_real: 3
```

> 📋 **Vollständiges Beispiel**: Eine umfassende Konfiguration mit Sensoren, Schaltern und Automatisierungen finden Sie in [`example-esp32.yaml`](example-esp32.yaml).

### Konfigurationsvariablen:
* **id** (*Optional*, ID): Die ID für diese Komponente. Wird benötigt, um aus Automatisierungen (Actions) darauf zuzugreifen.
* **socket_receive** (*Optional*, Liste): Die zu empfangenden Sockets, ein Eintrag pro Socket-ID:
  * **socket_id** (*Erforderlich*, int, 1–255): Die zu lauschende Socket-ID. Jede ID darf nur einmal konfiguriert werden.
  * **num_bit** (*Optional*, int, 0–100): Erwartete Anzahl der Bits/Bytes (Standard: 0).
  * **num_int** (*Optional*, int, 0–100): Erwartete Anzahl der 16-Bit Integer (Standard: 0).
  * **num_long** (*Optional*, int, 0–100): Erwartete Anzahl der 32-Bit Integer (Standard: 0).
  * **num_real** (*Optional*, int, 0–100): Erwartete Anzahl der Floats (Standard: 0).
  * **on_receive** (*Optional*, [Automation](https://esphome.io/automations/)): Aktionen, die ausgeführt werden, wenn ein Socket mit dieser `socket_id` und genau der konfigurierten Anzahl an Werten empfangen wird. In Lambdas ist `x` der empfangene `ab_socket` mit den Feldern `bitdata`, `intdata`, `longdata`, `realdata` (Vektoren in den konfigurierten Größen) und `sender` (ABUS-Adresse des Absenders). Pakete mit abweichender Länge werden als Fehler geloggt und verworfen.

> ℹ️ **Reihenfolge der Werte**: Die Werte eines Sockets werden immer in derselben Reihenfolge übertragen: zuerst alle Bits, dann alle Ints, dann alle Longs, dann alle Reals. Das gilt auch dann, wenn die Datentypen in der Socket-Definition in der SPS gemischt angelegt sind. `x.intdata[0]` ist also immer der erste Int des Sockets, egal an welcher Stelle er in der SPS steht.

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

Diese Komponente enthält alle benötigten Abhängigkeiten in der mitgelieferten Header-Datei [`abus_helper.h`](components/abus_socket/abus_helper.h). Diese stellt folgende wichtige Funktionen bereit:

* **Paket-Validierung und -Parsing**: `ab_checkValidPacket`, `ab_getHeader`, `ab_getSocket`
* **Paket-Erstellung**: `ab_setHeader`, `ab_setSocket`, `ab_calcCRC`
* **Datentyp-Manipulation**: `ab_getBoolVal`, `ab_getIntVal`, `ab_getLongVal`, `ab_getRealVal`
* **Socket-Strukturen**: `ab_header`, `ab_socket_config`, `ab_socket`

Es sind keine zusätzlichen externen Abhängigkeiten erforderlich - alles was für die Cybro-3 Kommunikation benötigt wird, ist bereits enthalten.

> ⚠️ **Wichtiger Hinweis**: Diese Komponente unterstützt aktuell nur das ESP-IDF Framework. Arduino Framework wird derzeit nicht unterstützt.

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