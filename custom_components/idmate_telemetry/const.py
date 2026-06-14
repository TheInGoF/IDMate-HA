"""Constants for the IDMate Telemetry integration."""

DOMAIN = "idmate_telemetry"

# Entry mode — one integration, several kinds of config entry.
CONF_MODE = "mode"
MODE_TELEMETRY = "telemetry"
MODE_CHARGE = "charge"
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

# ── Telemetry: entity-mapping config keys ────────────────────
CONF_SOC = "soc_entity"
CONF_SPEED = "speed_entity"
CONF_LOCATION = "location_entity"
CONF_ODOMETER = "odometer_entity"
CONF_RANGE = "range_entity"
CONF_POWER = "power_entity"
CONF_CHARGING = "charging_entity"

# ── Charge tracker config keys ───────────────────────────────
CONF_NAME = "name"
CONF_URL = "url"
CONF_TOKEN = "token"
CONF_METER = "meter_entity"
CONF_VEHICLE_ENTITY = "vehicle_entity"
CONF_VEHICLE_PLATE = "vehicle_plate"
CONF_PRICE = "price_entity"
CONF_BASE_FEE = "base_fee_entity"
CONF_CHARGE_ODOMETER = "charge_odometer_entity"
CONF_CHARGE_SOC = "charge_soc_entity"

# ── Import (IDMate vehicles -> Home Assistant) config keys ───
CONF_IMPORT_URL = "import_url"
CONF_IMPORT_TOKEN = "import_token"
CONF_IMPORT_INTERVAL = "import_interval"

# ── Defaults ─────────────────────────────────────────────────
DEFAULT_IMPORT_INTERVAL = 30  # poll interval for imported vehicles (s)
DEFAULT_PORT = 8883
DEFAULT_INTERVAL = 10        # evaluation tick / throttle floor (s)
DEFAULT_MAX_INTERVAL = 60    # heartbeat while active (s)
DEFAULT_MIN_DISTANCE = 100   # distance trigger (m) — mirrors the firmware
DEFAULT_MIN_HEADING = 8      # bearing-change trigger (deg) — curve approximation
DEFAULT_TLS = True
DEFAULT_TLS_INSECURE = True

# Binary telegram protocol version (v2: kw widened to u32).
# Must stay in sync with the IDMate server decoder and the ESP32 firmware.
PROTO_VERSION = 0x02
