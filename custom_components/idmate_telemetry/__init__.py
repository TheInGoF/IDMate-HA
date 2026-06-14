"""IDMate: push HA vehicle telemetry (MQTT) and charge readings (HTTP) to IDMate."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_interval

from .charge import IdmateChargeTracker
from .const import (
    CONF_INTERVAL,
    CONF_MODE,
    DEFAULT_INTERVAL,
    DOMAIN,
    MODE_CHARGE,
    MODE_IMPORT,
)
from .importer import IdmateImportCoordinator
from .telemetry import IdmateTelemetry

_LOGGER = logging.getLogger(__name__)

IMPORT_PLATFORMS = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.DEVICE_TRACKER,
]


def _merged_config(entry: ConfigEntry) -> dict:
    """Options override data (options flow can re-map entities / interval)."""
    return {**entry.data, **entry.options}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up one config entry — telemetry (MQTT) or charge tracker (HTTP)."""
    cfg = _merged_config(entry)

    if cfg.get(CONF_MODE) == MODE_IMPORT:
        coordinator = IdmateImportCoordinator(hass, entry, cfg)
        await coordinator.async_config_entry_first_refresh()
        hass.data.setdefault(DOMAIN, {})[entry.entry_id] = ("import", coordinator, None)
        await hass.config_entries.async_forward_entry_setups(entry, IMPORT_PLATFORMS)
        entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
        return True

    if cfg.get(CONF_MODE) == MODE_CHARGE:
        tracker = IdmateChargeTracker(hass, entry, cfg)
        await tracker.async_start()
        hass.data.setdefault(DOMAIN, {})[entry.entry_id] = ("charge", tracker, None)
        entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
        return True

    telem = IdmateTelemetry(hass, cfg)
    await hass.async_add_executor_job(telem.start)

    interval = timedelta(seconds=int(cfg.get(CONF_INTERVAL, DEFAULT_INTERVAL)))

    async def _on_interval(_now) -> None:
        # tick() reads states (cheap) and hands the publish to paho's network
        # thread; run it in the executor to keep AES off the event loop.
        await hass.async_add_executor_job(telem.tick)

    unsub = async_track_time_interval(hass, _on_interval, interval)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = ("telemetry", telem, unsub)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Tear down a config entry."""
    domain_data = hass.data.get(DOMAIN, {})
    data = domain_data.get(entry.entry_id)
    if data is None:
        return True
    kind, obj, unsub = data

    if kind == "import":
        unloaded = await hass.config_entries.async_unload_platforms(
            entry, IMPORT_PLATFORMS
        )
        if unloaded:
            domain_data.pop(entry.entry_id, None)
        return unloaded

    domain_data.pop(entry.entry_id, None)
    if unsub is not None:
        unsub()
    if kind == "charge":
        await obj.async_stop()
    else:
        await hass.async_add_executor_job(obj.stop)
    return True


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
