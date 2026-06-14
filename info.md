# IDMate Telemetry

Bridge Home Assistant to [IDMate](https://github.com/TheInGoF/IDMate). Three
kinds of config entry (chosen from a menu):

- **Vehicle telemetry (MQTT)** — live vehicle data as AES-256-CBC encrypted MQTT
  telegrams, byte-identical to the ESP32 firmware. Arrives at IDMate "from
  outside" over TLS + auth; the server needs no changes. Adaptive sending
  (distance / heading / heartbeat) like the firmware's GPS state machine.
- **Charge tracker (HTTP)** — quarter-hourly energy-meter readings posted to
  `/api/charge/reading`; IDMate builds charge sessions and costs automatically.
  Restart-safe: no consumption is lost across Home Assistant restarts.
- **Import IDMate vehicles (HTTP)** — pulls vehicles you exposed in IDMate into
  HA as devices with sensors and a location tracker.

Add as many entries as you like. Everything is configured in the UI; no secrets
live in this repository.
