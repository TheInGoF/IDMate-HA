"""Binary sensors (charging / DC / parked) for imported IDMate vehicles."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import IdmateVehicleEntity

BINARY_SENSORS: tuple[BinarySensorEntityDescription, ...] = (
    BinarySensorEntityDescription(
        key="charging", name="Charging",
        device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
    ),
    BinarySensorEntityDescription(
        key="dc_charging", name="DC fast charging", icon="mdi:ev-station",
    ),
    BinarySensorEntityDescription(
        key="parked", name="Parked", icon="mdi:car-brake-parking",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id][1]
    entities: list[IdmateBinarySensor] = []
    for device, vehicle in (coordinator.data or {}).items():
        for desc in BINARY_SENSORS:
            entities.append(IdmateBinarySensor(coordinator, entry.entry_id, device, vehicle, desc))
    async_add_entities(entities)


class IdmateBinarySensor(IdmateVehicleEntity, BinarySensorEntity):
    """A boolean flag of an imported vehicle (1/true = on)."""

    def __init__(self, coordinator, entry_id, device, vehicle, description):
        super().__init__(coordinator, entry_id, device, vehicle)
        self.entity_description = description
        self._attr_unique_id = f"{entry_id}_{device}_{description.key}"

    @property
    def is_on(self) -> bool:
        return self._state.get(self.entity_description.key) in (1, True, "1", "on", "true")
