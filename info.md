# IDMate Telemetry

Bridge Home Assistant to [IDMate](https://github.com/TheInGoF/IDMate). Two kinds
of config entry (chosen from a menu):

- **Vehicle telemetry (MQTT)** — live vehicle data as AES-256-CBC encrypted MQTT
  telegrams, byte-identical to the ESP32 firmware. Arrives at IDMate "from
  outside" over TLS + auth; the server needs no changes.
- **Charge tracker (HTTP)** — quarter-hourly energy-meter readings posted to
  `/api/charge/reading`; IDMate builds charge sessions and costs automatically.
  Restart-safe: no consumption is lost across Home Assistant restarts.

Add as many entries as you like — one per vehicle and one (or more) per meter.
Everything is configured in the UI; no secrets live in this repository.
