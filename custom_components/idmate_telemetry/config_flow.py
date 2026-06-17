"""Config + options flow for IDMate (telemetry + vehicle import)."""

from __future__ import annotations

from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_AES_KEY,
    CONF_CHARGING,
    CONF_DEVICE,
    CONF_EXT_TEMP,
    CONF_HEADING,
    CONF_HOST,
    CONF_IMPORT_INTERVAL,
    CONF_IMPORT_TOKEN,
    CONF_IMPORT_URL,
    CONF_INTERVAL,
    CONF_LOCATION,
    CONF_MAX_INTERVAL,
    CONF_MIN_DISTANCE,
    CONF_MIN_HEADING,
    CONF_MODE,
    CONF_ODOMETER,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_POWER,
    CONF_RANGE,
    CONF_SOC,
    CONF_STILL_POINTS,
    CONF_SPEED,
    CONF_TLS,
    CONF_TLS_INSECURE,
    CONF_USERNAME,
    DEFAULT_IMPORT_INTERVAL,
    DEFAULT_INTERVAL,
    DEFAULT_MAX_INTERVAL,
    DEFAULT_MIN_DISTANCE,
    DEFAULT_MIN_HEADING,
    DEFAULT_STILL_POINTS,
    DEFAULT_PORT,
    DEFAULT_TLS,
    DEFAULT_TLS_INSECURE,
    DOMAIN,
    MODE_IMPORT,
    MODE_TELEMETRY,
)

MENU_IMPORT = "import_vehicles"  # menu/step id (avoid HA's reserved 'import' step)

_TEXT = selector.TextSelector()
_PASSWORD = selector.TextSelector(
    selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
)


def _int_field(lo: int, hi: int, unit: str):
    return vol.All(
        selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=lo, max=hi, unit_of_measurement=unit,
                mode=selector.NumberSelectorMode.BOX,
            )
        ),
        vol.Coerce(int),
    )


def _timing_fields(d: dict) -> dict:
    """Adaptive-sender timing/threshold fields (shared by config + options)."""
    return {
        vol.Required(
            CONF_INTERVAL, default=d.get(CONF_INTERVAL, DEFAULT_INTERVAL)
        ): _int_field(2, 3600, "s"),
        vol.Required(
            CONF_MAX_INTERVAL, default=d.get(CONF_MAX_INTERVAL, DEFAULT_MAX_INTERVAL)
        ): _int_field(5, 3600, "s"),
        vol.Required(
            CONF_MIN_DISTANCE, default=d.get(CONF_MIN_DISTANCE, DEFAULT_MIN_DISTANCE)
        ): _int_field(0, 10000, "m"),
        vol.Required(
            CONF_MIN_HEADING, default=d.get(CONF_MIN_HEADING, DEFAULT_MIN_HEADING)
        ): _int_field(0, 180, "°"),
        vol.Required(
            CONF_STILL_POINTS, default=d.get(CONF_STILL_POINTS, DEFAULT_STILL_POINTS)
        ): _int_field(0, 10, ""),
    }


def _entity(domain: str):
    return selector.EntitySelector(selector.EntitySelectorConfig(domain=domain))


def _opt(fields: dict, key: str, sel, defaults: dict, *, required: bool = False):
    marker = vol.Required if required else vol.Optional
    if defaults.get(key) not in (None, ""):
        fields[marker(key, default=defaults[key])] = sel
    else:
        fields[marker(key)] = sel


# ── schemas ──────────────────────────────────────────────────
def _connection_schema(d: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_DEVICE, default=d.get(CONF_DEVICE, "")): _TEXT,
            vol.Required(CONF_HOST, default=d.get(CONF_HOST, "")): _TEXT,
            vol.Required(CONF_PORT, default=d.get(CONF_PORT, DEFAULT_PORT)): vol.All(
                selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1, max=65535, mode=selector.NumberSelectorMode.BOX
                    )
                ),
                vol.Coerce(int),
            ),
            vol.Optional(CONF_USERNAME, default=d.get(CONF_USERNAME, "")): _TEXT,
            vol.Optional(CONF_PASSWORD, default=d.get(CONF_PASSWORD, "")): _PASSWORD,
            vol.Required(CONF_AES_KEY, default=d.get(CONF_AES_KEY, "")): _PASSWORD,
            vol.Required(CONF_TLS, default=d.get(CONF_TLS, DEFAULT_TLS)): bool,
            vol.Required(
                CONF_TLS_INSECURE, default=d.get(CONF_TLS_INSECURE, DEFAULT_TLS_INSECURE)
            ): bool,
            **_timing_fields(d),
        }
    )


def _entities_schema(d: dict[str, Any]) -> vol.Schema:
    fields: dict = {}
    _opt(fields, CONF_SOC, _entity("sensor"), d, required=True)
    _opt(fields, CONF_SPEED, _entity("sensor"), d, required=True)
    _opt(fields, CONF_LOCATION, _entity("device_tracker"), d)
    _opt(fields, CONF_ODOMETER, _entity("sensor"), d)
    _opt(fields, CONF_RANGE, _entity("sensor"), d)
    _opt(fields, CONF_POWER, _entity("sensor"), d)
    _opt(fields, CONF_EXT_TEMP, _entity("sensor"), d)
    _opt(fields, CONF_HEADING, _entity("sensor"), d)
    _opt(fields, CONF_CHARGING, _entity("binary_sensor"), d)
    return vol.Schema(fields)


def _import_schema(d: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_IMPORT_URL, default=d.get(CONF_IMPORT_URL, "")): _TEXT,
            vol.Required(CONF_IMPORT_TOKEN, default=d.get(CONF_IMPORT_TOKEN, "")): _PASSWORD,
            vol.Required(
                CONF_IMPORT_INTERVAL,
                default=d.get(CONF_IMPORT_INTERVAL, DEFAULT_IMPORT_INTERVAL),
            ): _int_field(10, 3600, "s"),
        }
    )


def _validate_aes_key(value: str) -> str | None:
    value = (value or "").strip()
    if len(value) != 64:
        return "aes_key_length"
    try:
        bytes.fromhex(value)
    except ValueError:
        return "aes_key_hex"
    return None


def _normalize_url(raw: str) -> str:
    """Make a forgiving URL: bare IP -> http://IP:3004. Adds scheme + the
    default port so the user only has to type the LAN IP."""
    raw = (raw or "").strip().rstrip("/")
    if not raw:
        return raw
    if "://" not in raw:
        raw = "http://" + raw
    scheme, _, rest = raw.partition("://")
    host = rest.split("/", 1)[0]
    path = rest[len(host):]
    # Default the IDMate port only for plain http (the LAN case); leave https
    # (reverse-proxy/domain on 443) untouched.
    if ":" not in host and scheme == "http":
        host = f"{host}:3004"
    return f"{scheme}://{host}{path}"


async def _validate_import(hass, url: str, token: str) -> str | None:
    """Probe the IDMate export API. Returns an error key, or None on success."""
    url = (url or "").rstrip("/")
    session = async_get_clientsession(hass)
    try:
        async with session.get(
            f"{url}/api/ha/vehicles",
            headers={"Authorization": f"Bearer {token}"},
            timeout=15,
        ) as resp:
            if resp.status in (401, 403):
                return "invalid_auth"
            if resp.status == 503:
                return "not_configured"
            if resp.status >= 400:
                return "cannot_connect"
    except (aiohttp.ClientError, TimeoutError):
        return "cannot_connect"
    return None


# ── config flow ──────────────────────────────────────────────
class IdmateTelemetryConfigFlow(ConfigFlow, domain=DOMAIN):
    """Menu → telemetry (2 steps) or import IDMate vehicles (1 step)."""

    VERSION = 1

    def __init__(self) -> None:
        self._connection: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        return self.async_show_menu(
            step_id="user", menu_options=[MODE_TELEMETRY, MENU_IMPORT]
        )

    # ----- telemetry -----
    async def async_step_telemetry(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            err = _validate_aes_key(user_input.get(CONF_AES_KEY, ""))
            if err:
                errors[CONF_AES_KEY] = err
            else:
                device = user_input[CONF_DEVICE].strip()
                await self.async_set_unique_id(f"{DOMAIN}_tele_{device}")
                self._abort_if_unique_id_configured()
                user_input[CONF_DEVICE] = device
                user_input[CONF_AES_KEY] = user_input[CONF_AES_KEY].strip()
                self._connection = user_input
                return await self.async_step_entities()

        return self.async_show_form(
            step_id="telemetry",
            data_schema=_connection_schema(user_input or {}),
            errors=errors,
        )

    async def async_step_entities(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            data = {CONF_MODE: MODE_TELEMETRY, **self._connection, **user_input}
            return self.async_create_entry(
                title=self._connection[CONF_DEVICE], data=data
            )
        return self.async_show_form(
            step_id="entities", data_schema=_entities_schema({})
        )

    # ----- import IDMate vehicles -----
    async def async_step_import_vehicles(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            url = _normalize_url(user_input.get(CONF_IMPORT_URL, ""))
            user_input[CONF_IMPORT_URL] = url
            err = await _validate_import(
                self.hass, url, user_input.get(CONF_IMPORT_TOKEN, "")
            )
            if err:
                errors["base"] = err
            else:
                await self.async_set_unique_id(f"{DOMAIN}_import_{url}")
                self._abort_if_unique_id_configured()
                data = {CONF_MODE: MODE_IMPORT, **user_input}
                return self.async_create_entry(title=f"Import: {url}", data=data)

        return self.async_show_form(
            step_id=MENU_IMPORT,
            data_schema=_import_schema(user_input or {}),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(entry: ConfigEntry) -> OptionsFlow:
        return IdmateTelemetryOptionsFlow(entry)


# ── options flow ─────────────────────────────────────────────
class IdmateTelemetryOptionsFlow(OptionsFlow):
    """Edit entity mapping (+ interval for telemetry) after setup."""

    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = {**self._entry.data, **self._entry.options}
        if current.get(CONF_MODE) == MODE_IMPORT:
            schema = vol.Schema(
                {
                    vol.Required(
                        CONF_IMPORT_INTERVAL,
                        default=current.get(CONF_IMPORT_INTERVAL, DEFAULT_IMPORT_INTERVAL),
                    ): _int_field(10, 3600, "s")
                }
            )
        else:
            schema = _entities_schema(current).extend(_timing_fields(current))
        return self.async_show_form(step_id="init", data_schema=schema)
