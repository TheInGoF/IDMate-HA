# IDMate Telemetry — Home Assistant Integration

Bridge Home Assistant to [IDMate](https://github.com/TheInGoF/IDMate). The
integration offers three kinds of config entry (pick from a menu when adding it),
and you can add as many as you like:

1. **Vehicle telemetry (MQTT)** — sends live vehicle data as **AES-256-CBC
   encrypted MQTT telegrams**, byte-identical to the ESP32 firmware
   ([IDTelemetry](https://github.com/TheInGoF)). Your data arrives at the IDMate
   server "from outside" over an authenticated, TLS-encrypted MQTT connection,
   exactly like any other vehicle. The IDMate server needs **no changes**.
2. **Charge tracker (HTTP)** — posts 15-minute energy-meter readings to the
   IDMate webhook (`/api/charge/reading`); IDMate builds charge sessions and
   costs automatically.
3. **Import IDMate vehicles (HTTP)** — the reverse direction: pulls the latest
   state of vehicles you exposed in IDMate (e.g. the CAN/ESP32 loggers) and
   creates HA devices with sensors and a location tracker.

Use this when you already have a vehicle in Home Assistant (Tesla via TeslaMate,
the official Tesla integration, a Volkswagen/ID. integration, etc.) and want to
feed it into IDMate without writing directly to InfluxDB or maintaining
hand-written automations — or to bring IDMate's own logged vehicles back into HA.

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

When you add the integration, a menu lets you choose **Vehicle telemetry** or
**Charge tracker**. Add as many entries as you like (one per vehicle / per
meter).

### Vehicle telemetry (MQTT)

Connection:

- **Device name** — the IDMate vehicle id (e.g. `id7`). Publishes to `tele/<device>/data`.
- **Broker host / port** — your Mosquitto (default `8883`).
- **Username / password** — the MQTT user for this vehicle.
- **AES key** — the same 64-char hex key as the IDMate server's `MQTT_AES_KEY`.
- **TLS / accept self-signed** — enable both for a self-signed broker cert.
- **Send interval** — default 60 s.

Entity mapping (SoC + speed required, rest optional):

- State of charge (%), speed, location (`device_tracker`), odometer, remaining
  range, power, charging (`binary_sensor`).
- Units for range / power / odometer are auto-detected from
  `unit_of_measurement` (`m`/`km`/`mi`, `W`/`kW`, `mph`).

**Adaptive sending (GPS state machine).** Instead of a dumb fixed timer the
integration mirrors the ESP32 firmware: it *evaluates* every `interval` seconds
(the throttle floor — it never sends faster than this) and only emits a telegram
when a trigger fires:

- **Distance** — moved ≥ `min_distance` (default 100 m): dense points in town,
  sparse on the motorway.
- **Heading** — bearing (computed from GPS) changed ≥ `min_heading` (default 8°):
  captures curves. The computed bearing is also sent as the `hd` field.
- **Heartbeat** — at least every `max_interval` (default 60 s) while active.
- **State change** — charging started/stopped: sent immediately.

This sends nothing while parked-and-not-charging (the car may sleep), keeps the
rate bounded by `interval`, and produces a much finer track than fixed-interval
sampling without flooding InfluxDB. Tune all four thresholds in the config /
options. Boolean fields (charging / parked / DC) follow the firmware convention:
a set bit means *true*; *false* simply omits the field.

### Charge tracker (HTTP)

- **Name** — unique label for this meter (e.g. `wallbox`).
- **IDMate base URL** — e.g. `http://192.168.1.5:3004`.
- **Webhook token** — the server's `CHARGE_WEBHOOK_TOKEN` (sent as `Bearer`).
- **Energy meter** — a continuous kWh sensor (the wallbox / meter total). Required.
- **Vehicle** — either an entity that holds the plate, or a fixed fallback plate.
- **Price / base fee** — optional €/kWh entities (e.g. a Tibber/EPEX template
  sensor). Forwarded verbatim as `tibber_price` / `tibber_grundgebuehr`.
- **Odometer / SoC** — optional.

Every wall-clock quarter hour (`:00/:15/:30/:45`) the integration reads the
meter, computes the consumption since the last tick and POSTs it. Readings with
`kwh <= 0` or an empty/`free` vehicle are skipped by the server. No
`input_number` helper or quarter-hour-reset sensor is needed — the integration
keeps that state itself.

**No consumption is ever lost across restarts.** The last meter value is
persisted on every tick and *restored* (not re-anchored) on startup, so if Home
Assistant is down across a tick the next tick simply reports the larger
difference (e.g. a 30-minute window). With a monotonic all-time meter, the diff
is always exactly the real consumption since the last successful reading. If the
meter is still `unavailable` at a tick (entity not loaded yet after a restart),
that tick is skipped without touching the anchor, so the next one catches up. A
decreasing meter (counter reset) is skipped. The anchor is set to the current
meter only on the very first run, to avoid billing the lifetime total as one
window.

### Import IDMate vehicles (HTTP)

Brings vehicles that live in IDMate (e.g. the CAN/ESP32 loggers) **into** Home
Assistant.

First, in **IDMate → Admin → Home Assistant**: generate a read token and tick
the vehicles you want to expose. Leave anything that originates in HA unticked —
there is no loopback. Then add this integration:

- **IDMate base URL** — e.g. `http://192.168.1.5:3004`.
- **Read token** — the token shown on that IDMate admin page.
- **Poll interval** — default 30 s.

For each exposed vehicle the integration creates a **device** with sensors (state
of charge, speed, power, range, odometer, voltage, current, temperatures, logger
battery, LTE signal, mobile operator), **binary sensors** (charging, DC fast
charging, parked) and a **`device_tracker`** for the map. Values follow the
IDMate server's latest known state (refreshed every poll). New vehicles exposed
later in IDMate appear after reloading the entry.

## Requirements

- Home Assistant 2024.1+.
- An IDMate server with its MQTT bridge enabled and a vehicle with the matching
  `device` id.
- `paho-mqtt` and `cryptography` ship with Home Assistant — no extra installs.

## License

[AGPL-3.0](LICENSE), matching the IDMate project.
