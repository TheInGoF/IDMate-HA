"""Constants for the IDMate Telemetry integration."""

DOMAIN = "idmate_telemetry"

# Entry mode — one integration, two kinds of config entry.
CONF_MODE = "mode"
MODE_TELEMETRY = "telemetry"
MODE_CHARGE = "charge"

# ── Telemetry: connection config keys ────────────────────────
CONF_HOST = "host"
CONF_PORT = "port"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_AES_KEY = "aes_key"
CONF_TLS = "tls"
CONF_TLS_INSECURE = "tls_insecure"
CONF_DEVICE = "device"
CONF_INTERVAL = "interval"

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

# ── Defaults ─────────────────────────────────────────────────
DEFAULT_PORT = 8883
DEFAULT_INTERVAL = 60
DEFAULT_TLS = True
DEFAULT_TLS_INSECURE = True

# Binary telegram protocol version (v2: kw widened to u32).
# Must stay in sync with the IDMate server decoder and the ESP32 firmware.
PROTO_VERSION = 0x02
