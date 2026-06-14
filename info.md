# IDMate Telemetry

Bridge Home Assistant to [IDMate](https://github.com/TheInGoF/IDMate). Two kinds
of config entry (chosen from a menu):

- **Vehicle telemetry (MQTT)** — live vehicle data as AES-256-CBC encrypted MQTT
  telegrams, byte-identical to the ESP32 firmware. HA publishes to the internal
  LAN broker (plain, anonymous); the AES key is the security. Adaptive sending
  (distance / heading / heartbeat) like the firmware's GPS state machine.
- **Import IDMate vehicles (HTTP)** — pulls vehicles you exposed in IDMate into
  HA as devices with sensors and a location tracker.

Add as many entries as you like. Everything is configured in the UI; no secrets
live in this repository. (Charge tracking lives in a Home Assistant automation
posting to IDMate's `/api/charge/reading`, not in this integration.)
