"""Constants for the IDMate Telemetry integration."""

DOMAIN = "idmate_telemetry"

# ── Connection config keys ───────────────────────────────────
CONF_HOST = "host"
CONF_PORT = "port"
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_AES_KEY = "aes_key"
CONF_TLS = "tls"
CONF_TLS_INSECURE = "tls_insecure"
CONF_DEVICE = "device"
CONF_INTERVAL = "interval"

# ── Entity-mapping config keys ───────────────────────────────
CONF_SOC = "soc_entity"
CONF_SPEED = "speed_entity"
CONF_LOCATION = "location_entity"
CONF_ODOMETER = "odometer_entity"
CONF_RANGE = "range_entity"
CONF_POWER = "power_entity"
CONF_CHARGING = "charging_entity"

# ── Defaults ─────────────────────────────────────────────────
DEFAULT_PORT = 8883
DEFAULT_INTERVAL = 60
DEFAULT_TLS = True
DEFAULT_TLS_INSECURE = True

# Binary telegram protocol version (v2: kw widened to u32).
# Must stay in sync with the IDMate server decoder and the ESP32 firmware.
PROTO_VERSION = 0x02
