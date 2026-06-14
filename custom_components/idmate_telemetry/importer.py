"""Poll the IDMate server for selected vehicles and expose them in HA.

This is the reverse direction of the telemetry/charge modes: instead of pushing
data to IDMate, it pulls the latest state of the vehicles the IDMate admin has
exposed (GET /api/ha/vehicles, Bearer token) and feeds it to sensor /
binary_sensor / device_tracker entities via a DataUpdateCoordinator.
"""

from __future__ import annotations

from datetime import timedelta
import logging

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_IMPORT_INTERVAL,
    CONF_IMPORT_TOKEN,
    CONF_IMPORT_URL,
    DEFAULT_IMPORT_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


class IdmateImportCoordinator(DataUpdateCoordinator):
    """Fetches {device: vehicle} from the IDMate export API."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, cfg: dict) -> None:
        interval = int(cfg.get(CONF_IMPORT_INTERVAL, DEFAULT_IMPORT_INTERVAL))
        super().__init__(
            hass,
            _LOGGER,
            name="IDMate import",
            update_interval=timedelta(seconds=interval),
        )
        self._url = str(cfg[CONF_IMPORT_URL]).rstrip("/")
        self._token = cfg.get(CONF_IMPORT_TOKEN, "")

    async def _async_update_data(self) -> dict:
        session = async_get_clientsession(self.hass)
        url = f"{self._url}/api/ha/vehicles"
        headers = {"Authorization": f"Bearer {self._token}"}
        try:
            async with session.get(url, headers=headers, timeout=30) as resp:
                if resp.status in (401, 403):
                    raise ConfigEntryAuthFailed("IDMate rejected the token")
                if resp.status == 503:
                    raise UpdateFailed("IDMate HA export is not configured")
                resp.raise_for_status()
                data = await resp.json()
        except ConfigEntryAuthFailed:
            raise
        except (aiohttp.ClientError, TimeoutError) as exc:
            raise UpdateFailed(f"IDMate not reachable: {exc}") from exc

        vehicles = data.get("vehicles", []) if isinstance(data, dict) else []
        return {v["device"]: v for v in vehicles if v.get("device")}
