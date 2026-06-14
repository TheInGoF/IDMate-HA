"""Config + options flow for IDMate Telemetry."""

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
    CONF_CHARGING,
    CONF_DEVICE,
    CONF_HOST,
    CONF_INTERVAL,
    CONF_LOCATION,
    CONF_ODOMETER,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_POWER,
    CONF_RANGE,
    CONF_SOC,
    CONF_SPEED,
    CONF_TLS,
    CONF_TLS_INSECURE,
    CONF_USERNAME,
    DEFAULT_INTERVAL,
    DEFAULT_PORT,
    DEFAULT_TLS,
    DEFAULT_TLS_INSECURE,
    DOMAIN,
)

_TEXT = selector.TextSelector()
_PASSWORD = selector.TextSelector(
    selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
)


def _connection_schema(defaults: dict[str, Any]) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_DEVICE, default=defaults.get(CONF_DEVICE, "")): _TEXT,
            vol.Required(CONF_HOST, default=defaults.get(CONF_HOST, "")): _TEXT,
            vol.Required(CONF_PORT, default=defaults.get(CONF_PORT, DEFAULT_PORT)): vol.All(
                selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=1, max=65535, mode=selector.NumberSelectorMode.BOX
                    )
                ),
                vol.Coerce(int),
            ),
            vol.Required(CONF_USERNAME, default=defaults.get(CONF_USERNAME, "")): _TEXT,
            vol.Required(CONF_PASSWORD, default=defaults.get(CONF_PASSWORD, "")): _PASSWORD,
            vol.Required(CONF_AES_KEY, default=defaults.get(CONF_AES_KEY, "")): _PASSWORD,
            vol.Required(CONF_TLS, default=defaults.get(CONF_TLS, DEFAULT_TLS)): bool,
            vol.Required(
                CONF_TLS_INSECURE,
                default=defaults.get(CONF_TLS_INSECURE, DEFAULT_TLS_INSECURE),
            ): bool,
            vol.Required(
                CONF_INTERVAL, default=defaults.get(CONF_INTERVAL, DEFAULT_INTERVAL)
            ): vol.All(
                selector.NumberSelector(
                    selector.NumberSelectorConfig(
                        min=5, max=3600, unit_of_measurement="s",
                        mode=selector.NumberSelectorMode.BOX,
                    )
                ),
                vol.Coerce(int),
            ),
        }
    )


def _entities_schema(defaults: dict[str, Any]) -> vol.Schema:
    def sensor(optional_key: str, *, required: bool = False, domain: str = "sensor"):
        sel = selector.EntitySelector(
            selector.EntitySelectorConfig(domain=domain)
        )
        marker = vol.Required if required else vol.Optional
        if defaults.get(optional_key):
            return marker(optional_key, default=defaults[optional_key]), sel
        return marker(optional_key), sel

    fields: dict = {}
    for key, req, dom in (
        (CONF_SOC, True, "sensor"),
        (CONF_SPEED, True, "sensor"),
        (CONF_LOCATION, False, "device_tracker"),
        (CONF_ODOMETER, False, "sensor"),
        (CONF_RANGE, False, "sensor"),
        (CONF_POWER, False, "sensor"),
        (CONF_CHARGING, False, "binary_sensor"),
    ):
        marker, sel = sensor(key, required=req, domain=dom)
        fields[marker] = sel
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


class IdmateTelemetryConfigFlow(ConfigFlow, domain=DOMAIN):
    """Two-step config flow: connection, then entity mapping."""

    VERSION = 1

    def __init__(self) -> None:
        self._connection: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            err = _validate_aes_key(user_input.get(CONF_AES_KEY, ""))
            if err:
                errors[CONF_AES_KEY] = err
            else:
                device = user_input[CONF_DEVICE].strip()
                await self.async_set_unique_id(f"{DOMAIN}_{device}")
                self._abort_if_unique_id_configured()
                user_input[CONF_DEVICE] = device
                user_input[CONF_AES_KEY] = user_input[CONF_AES_KEY].strip()
                self._connection = user_input
                return await self.async_step_entities()

        return self.async_show_form(
            step_id="user",
            data_schema=_connection_schema(user_input or {}),
            errors=errors,
        )

    async def async_step_entities(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            data = {**self._connection, **user_input}
            return self.async_create_entry(
                title=self._connection[CONF_DEVICE], data=data
            )

        return self.async_show_form(
            step_id="entities", data_schema=_entities_schema({})
        )

    @staticmethod
    @callback
    def async_get_options_flow(entry: ConfigEntry) -> OptionsFlow:
        return IdmateTelemetryOptionsFlow(entry)


class IdmateTelemetryOptionsFlow(OptionsFlow):
    """Edit interval + entity mapping after setup."""

    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        current = {**self._entry.data, **self._entry.options}
        schema = _entities_schema(current).extend(
            {
                vol.Required(
                    CONF_INTERVAL,
                    default=current.get(CONF_INTERVAL, DEFAULT_INTERVAL),
                ): vol.All(
                    selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=5, max=3600, unit_of_measurement="s",
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                    vol.Coerce(int),
                ),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
