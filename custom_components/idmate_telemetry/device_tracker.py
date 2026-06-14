"""Location tracker for imported IDMate vehicles."""

from __future__ import annotations

from homeassistant.components.device_tracker import SourceType, TrackerEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import IdmateVehicleEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id][1]
    entities = [
        IdmateTracker(coordinator, entry.entry_id, device, vehicle)
        for device, vehicle in (coordinator.data or {}).items()
    ]
    async_add_entities(entities)


class IdmateTracker(IdmateVehicleEntity, TrackerEntity):
    """GPS position of an imported vehicle (named after the vehicle)."""

    _attr_name = None  # has_entity_name + None -> uses the device (vehicle) name

    def __init__(self, coordinator, entry_id, device, vehicle):
        super().__init__(coordinator, entry_id, device, vehicle)
        self._attr_unique_id = f"{entry_id}_{device}_location"

    @property
    def source_type(self) -> SourceType:
        return SourceType.GPS

    @property
    def latitude(self):
        return self._state.get("lat")

    @property
    def longitude(self):
        return self._state.get("lon")

    @property
    def location_accuracy(self) -> int:
        return 10

    @property
    def available(self) -> bool:
        return super().available and "lat" in self._state and "lon" in self._state
