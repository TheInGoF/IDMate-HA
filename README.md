# IDMate Telemetry — Home Assistant Integration

Bridge Home Assistant to [IDMate](https://github.com/TheInGoF/IDMate). The
integration offers two kinds of config entry (pick from a menu when adding it),
and you can add as many as you like:

1. **Vehicle telemetry (MQTT)** — sends live vehicle data as **AES-256-CBC
   encrypted MQTT telegrams**, byte-identical to the ESP32 firmware
   ([IDTelemetry](https://github.com/TheInGoF)). HA publishes to the IDMate
   broker on the **LAN** — plain (port 1883), anonymous, exactly like the
   sticks; the AES key is the security. The broker stays internal (no external
   exposure) and the IDMate server needs **no changes**.
2. **Import IDMate vehicles (HTTP)** — the reverse direction: pulls the latest
   state of vehicles you exposed in IDMate (e.g. the CAN/ESP32 loggers) and
   creates HA devices with sensors and a location tracker.

Use this when you already have a vehicle in Home Assistant (Tesla via TeslaMate,
the official Tesla integration, a Volkswagen/ID. integration, etc.) and want to
feed it into IDMate — or to bring IDMate's own logged vehicles back into HA.

> **Charge tracking** is intentionally **not** part of this integration — it is
> too setup-specific (which vehicle is charging, tariff/price logic). Use a Home
> Assistant automation that POSTs to IDMate's `/api/charge/reading` webhook
> instead; see `homeassistant/idmate_charge_tracker.yaml` in the IDMate repo.

## Why MQTT instead of a direct InfluxDB write?

- **No InfluxDB token in Home Assistant.** HA only talks to the broker on the LAN.
- **App-layer encryption is the security.** Each telegram is AES-256-CBC
  encrypted with a key the broker never sees — so the broker needs neither TLS
  nor authentication, just like the ESP32 sticks. The broker stays internal.
- **Same path as the hardware loggers.** One ingestion path on the server side.

## Security model

The repository contains **no secrets**. Broker IP and the AES key are entered in
the Home Assistant UI and stored encrypted in HA's `.storage`. Security comes
from the per-telegram **AES** layer — the broker is plain/anonymous and not
exposed externally, exactly as the firmware uses it. A public repo is therefore
the correct and secure choice (and lets HACS install it without a GitHub token).

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
- **Broker LAN IP** — your Mosquitto on the LAN, plain port `1883` (default).
- **AES key** — the same 64-char hex key as the IDMate server's `MQTT_AES_KEY`. This is the security.
- **Username / password / TLS** — leave empty / off (IDMate's broker is plain and anonymous). Only set them for a hardened TLS broker.
- **Send interval** — default 60 s.

In short: **broker IP + AES key** is all you normally enter.

Entity mapping (SoC + speed required, rest optional):

- State of charge (%), speed, location (`device_tracker`), odometer, remaining
  range, power, outside temperature. Each field has an inline hint explaining it.
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
- **Heartbeat** — at least every `max_interval` (default 60 s) while moving.

When the car stops it sends `still_points` standstill points (default 3, `v=0`)
to mark the real parking spot, then goes silent until it moves again. This keeps
the rate bounded by `interval` and produces a much finer track than fixed-interval
sampling without flooding InfluxDB. Charge tracking is handled separately by a
Home Assistant automation, so there is no charging entity here.

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
of charge, speed, power, range, odometer, heading, voltage, current, battery &
outside temperature, logger battery, LTE signal, mobile operator) and a
**`device_tracker`** for the map. Values follow the IDMate server's latest known
state (refreshed every poll). A sensor is unavailable while its vehicle doesn't
report that field. New vehicles exposed later in IDMate appear after reloading
the entry.

## Requirements

- Home Assistant 2024.1+.
- An IDMate server with its MQTT bridge enabled and a vehicle with the matching
  `device` id.
- `paho-mqtt` and `cryptography` ship with Home Assistant — no extra installs.

## License

[AGPL-3.0](LICENSE), matching the IDMate project.
