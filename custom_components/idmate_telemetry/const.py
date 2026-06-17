"""Constants for the IDMate Telemetry integration."""

DOMAIN = "idmate_telemetry"

# Entry mode — one integration, several kinds of config entry.
CONF_MODE = "mode"
MODE_TELEMETRY = "telemetry"
MODE_IMPORT = "import"

# ── Telemetry: connection config keys ────────────────────────
CONF_HOST = "host"
CONF_PORT = "port"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_AES_KEY = "aes_key"
CONF_TLS = "tls"
CONF_TLS_INSECURE = "tls_insecure"
CONF_DEVICE = "device"
CONF_INTERVAL = "interval"  # evaluation tick / minimum interval between sends (s)
CONF_MAX_INTERVAL = "max_interval"  # heartbeat: send at least this often while active (s)
CONF_MIN_DISTANCE = "min_distance"  # send when moved at least this far (m)
CONF_MIN_HEADING = "min_heading"  # send when bearing changed at least this much (deg)
CONF_STILL_POINTS = "still_points"  # standstill points (v=0) to send after stopping

# ── Telemetry: entity-mapping config keys ────────────────────
CONF_SOC = "soc_entity"
CONF_SPEED = "speed_entity"
CONF_LOCATION = "location_entity"
CONF_ODOMETER = "odometer_entity"
CONF_RANGE = "range_entity"
CONF_POWER = "power_entity"
CONF_EXT_TEMP = "ext_temp_entity"
CONF_HEADING = "heading_entity"

# ── Import (IDMate vehicles -> Home Assistant) config keys ───
CONF_IMPORT_URL = "import_url"
CONF_IMPORT_TOKEN = "import_token"
CONF_IMPORT_INTERVAL = "import_interval"

# ── Defaults ─────────────────────────────────────────────────
DEFAULT_IMPORT_INTERVAL = 30  # poll interval for imported vehicles (s)
# IDMate's MQTT model = plain broker + AES-encrypted payload (the ESP32 stick
# connects to port 1883 with no user/pass; security is the AES key). Defaults
# mirror that: plain, anonymous. TLS/auth stay available for hardened brokers.
DEFAULT_PORT = 1883
DEFAULT_INTERVAL = 10        # evaluation tick / throttle floor (s)
DEFAULT_MAX_INTERVAL = 60    # heartbeat while active (s)
DEFAULT_MIN_DISTANCE = 100   # distance trigger (m) — mirrors the firmware
DEFAULT_MIN_HEADING = 8      # bearing-change trigger (deg) — curve approximation
DEFAULT_STILL_POINTS = 3     # standstill points (v=0) sent after stopping, then silence
DEFAULT_TLS = False
DEFAULT_TLS_INSECURE = True

# Binary telegram protocol version (v2: kw widened to u32).
# Must stay in sync with the IDMate server decoder and the ESP32 firmware.
PROTO_VERSION = 0x02
