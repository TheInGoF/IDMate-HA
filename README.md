# IDMate Telemetry — Home Assistant Integration

Send vehicle telemetry from Home Assistant to [IDMate](https://github.com/TheInGoF/IDMate)
as **AES-256-CBC encrypted MQTT telegrams** — byte-identical to the ESP32
firmware ([IDTelemetry](https://github.com/TheInGoF)). Your data arrives at the
IDMate server "from outside" over an authenticated, TLS-encrypted MQTT
connection, exactly like any other vehicle. The IDMate server needs **no
changes**.

Use this when you already have a vehicle in Home Assistant (Tesla via TeslaMate,
the official Tesla integration, a Volkswagen/ID. integration, etc.) and want to
feed it into IDMate without writing directly to InfluxDB.

## Why MQTT instead of a direct InfluxDB write?

- **No InfluxDB token in Home Assistant.** HA only talks to the MQTT broker,
  authenticated per vehicle.
- **End-to-end app-layer encryption.** Each telegram is AES-256-CBC encrypted
  with a key the broker never sees — so even an untrusted broker can't read or
  forge your data.
- **Same path as the hardware loggers.** One ingestion path on the server side.

## Security model

The repository contains **no secrets**. Broker host, username, password and the
AES key are entered in the Home Assistant UI and stored encrypted in HA's
`.storage`. Security comes from TLS + MQTT auth + the per-telegram AES layer —
not from keeping the source private. A public repo is therefore the correct and
secure choice (and lets HACS install it without a GitHub token).

## Installation (HACS)

1. HACS → ⋮ → **Custom repositories**.
2. Add `https://github.com/TheInGoF/IDMate-HA`, category **Integration**.
3. Install **IDMate Telemetry**, then restart Home Assistant.
4. Settings → Devices & Services → **Add Integration** → *IDMate Telemetry*.

### Manual installation

Copy `custom_components/idmate_telemetry/` into your HA `config/custom_components/`
and restart.

## Configuration

Set up via the UI (one config entry per vehicle):

**Connection**
- **Device name** — the IDMate vehicle id (e.g. `sirius`). Publishes to `tele/<device>/data`.
- **Broker host / port** — your Mosquitto (default `8883`).
- **Username / password** — the MQTT user for this vehicle.
- **AES key** — the same 64-char hex key as the IDMate server's `MQTT_AES_KEY`.
- **TLS / accept self-signed** — enable both for a self-signed broker cert.
- **Send interval** — default 60 s.

**Entity mapping** (SoC + speed required, rest optional)
- State of charge (%), speed, location (`device_tracker`), odometer, remaining
  range, power, charging (`binary_sensor`).
- Units for range / power / odometer are auto-detected from
  `unit_of_measurement` (`m`/`km`/`mi`, `W`/`kW`, `mph`).

## Behaviour

- A telegram is sent every interval **only while driving or charging** (valid
  SoC and (speed > 0 or charging)). Parked-and-not-charging sends nothing, so
  the car is allowed to sleep.
- Boolean fields (charging / parked / DC) follow the firmware convention: a set
  bit means *true*; *false* simply omits the field.

## Requirements

- Home Assistant 2024.1+.
- An IDMate server with its MQTT bridge enabled and a vehicle with the matching
  `device` id.
- `paho-mqtt` and `cryptography` ship with Home Assistant — no extra installs.

## License

[AGPL-3.0](LICENSE), matching the IDMate project.
