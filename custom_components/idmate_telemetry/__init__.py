"""IDMate Telemetry: push HA vehicle data to IDMate as encrypted MQTT telegrams."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_interval

from .const import CONF_INTERVAL, DEFAULT_INTERVAL, DOMAIN
from .telemetry import IdmateTelemetry

_LOGGER = logging.getLogger(__name__)


def _merged_config(entry: ConfigEntry) -> dict:
    """Options override data (options flow can re-map entities / interval)."""
    return {**entry.data, **entry.options}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up one IDMate Telemetry config entry (one vehicle)."""
    cfg = _merged_config(entry)
    telem = IdmateTelemetry(hass, cfg)
    await hass.async_add_executor_job(telem.start)

    interval = timedelta(seconds=int(cfg.get(CONF_INTERVAL, DEFAULT_INTERVAL)))

    async def _on_interval(_now) -> None:
        # tick() reads states (cheap) and hands the publish to paho's network
        # thread; run it in the executor to keep AES off the event loop.
        await hass.async_add_executor_job(telem.tick)

    unsub = async_track_time_interval(hass, _on_interval, interval)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = (telem, unsub)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Tear down a config entry."""
    data = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    if data is not None:
        telem, unsub = data
        unsub()
        await hass.async_add_executor_job(telem.stop)
    return True


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
