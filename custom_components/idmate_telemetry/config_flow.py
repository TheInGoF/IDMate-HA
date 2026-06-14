"""Config + options flow for IDMate (telemetry + charge tracker)."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_AES_KEY,
    CONF_BASE_FEE,
    CONF_CHARGE_ODOMETER,
    CONF_CHARGE_SOC,
    CONF_CHARGING,
    CONF_DEVICE,
    CONF_HOST,
    CONF_INTERVAL,
    CONF_LOCATION,
    CONF_MAX_INTERVAL,
    CONF_METER,
    CONF_MIN_DISTANCE,
    CONF_MIN_HEADING,
    CONF_MODE,
    CONF_NAME,
    CONF_ODOMETER,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_POWER,
    CONF_PRICE,
    CONF_RANGE,
    CONF_SOC,
    CONF_SPEED,
    CONF_TLS,
    CONF_TLS_INSECURE,
    CONF_TOKEN,
    CONF_URL,
    CONF_USERNAME,
    CONF_VEHICLE_ENTITY,
    CONF_VEHICLE_PLATE,
    DEFAULT_INTERVAL,
    DEFAULT_MAX_INTERVAL,
    DEFAULT_MIN_DISTANCE,
    DEFAULT_MIN_HEADING,
    DEFAULT_PORT,
    DEFAULT_TLS,
    DEFAULT_TLS_INSECURE,
    DOMAIN,
    MODE_CHARGE,
    MODE_TELEMETRY,
)

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
            vol.Required(CONF_USERNAME, default=d.get(CONF_USERNAME, "")): _TEXT,
            vol.Required(CONF_PASSWORD, default=d.get(CONF_PASSWORD, "")): _PASSWORD,
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
    _opt(fields, CONF_CHARGING, _entity("binary_sensor"), d)
    return vol.Schema(fields)


def _charge_schema(d: dict[str, Any]) -> vol.Schema:
    fields: dict = {
        vol.Required(CONF_NAME, default=d.get(CONF_NAME, "")): _TEXT,
        vol.Required(CONF_URL, default=d.get(CONF_URL, "")): _TEXT,
        vol.Required(CONF_TOKEN, default=d.get(CONF_TOKEN, "")): _PASSWORD,
    }
    _opt(fields, CONF_METER, _entity("sensor"), d, required=True)
    _opt(fields, CONF_VEHICLE_ENTITY, _entity("sensor"), d)
    fields[
        vol.Optional(CONF_VEHICLE_PLATE, default=d.get(CONF_VEHICLE_PLATE, ""))
    ] = _TEXT
    _opt(fields, CONF_PRICE, _entity("sensor"), d)
    _opt(fields, CONF_BASE_FEE, _entity("sensor"), d)
    _opt(fields, CONF_CHARGE_ODOMETER, _entity("sensor"), d)
    _opt(fields, CONF_CHARGE_SOC, _entity("sensor"), d)
    return vol.Schema(fields)


def _validate_aes_key(value: str) -> str | None:
    value = (value or "").strip()
    if len(value) != 64:
        return "aes_key_length"
    try:
        bytes.fromhex(value)
    except ValueError:
        return "aes_key_hex"
    return None


# ── config flow ──────────────────────────────────────────────
class IdmateTelemetryConfigFlow(ConfigFlow, domain=DOMAIN):
    """Menu → telemetry (2 steps) or charge tracker (1 step)."""

    VERSION = 1

    def __init__(self) -> None:
        self._connection: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        return self.async_show_menu(
            step_id="user", menu_options=[MODE_TELEMETRY, MODE_CHARGE]
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

    # ----- charge tracker -----
    async def async_step_charge(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            name = user_input[CONF_NAME].strip()
            await self.async_set_unique_id(f"{DOMAIN}_charge_{name}")
            self._abort_if_unique_id_configured()
            data = {CONF_MODE: MODE_CHARGE, **user_input}
            return self.async_create_entry(title=f"Charge: {name}", data=data)
        return self.async_show_form(step_id="charge", data_schema=_charge_schema({}))

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
        if current.get(CONF_MODE) == MODE_CHARGE:
            schema = _charge_schema(current)
        else:
            schema = _entities_schema(current).extend(_timing_fields(current))
        return self.async_show_form(step_id="init", data_schema=schema)
