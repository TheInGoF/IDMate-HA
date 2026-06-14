"""Sensors for imported IDMate vehicles."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfLength,
    UnitOfPower,
    UnitOfSpeed,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .entity import IdmateVehicleEntity

_M = SensorStateClass.MEASUREMENT

SENSORS: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(key="soc", name="State of charge", native_unit_of_measurement=PERCENTAGE, device_class=SensorDeviceClass.BATTERY, state_class=_M),
    SensorEntityDescription(key="speed", name="Speed", native_unit_of_measurement=UnitOfSpeed.KILOMETERS_PER_HOUR, device_class=SensorDeviceClass.SPEED, state_class=_M),
    SensorEntityDescription(key="power", name="Power", native_unit_of_measurement=UnitOfPower.KILO_WATT, device_class=SensorDeviceClass.POWER, state_class=_M),
    SensorEntityDescription(key="range_km", name="Range", native_unit_of_measurement=UnitOfLength.KILOMETERS, device_class=SensorDeviceClass.DISTANCE, state_class=_M),
    SensorEntityDescription(key="odometer", name="Odometer", native_unit_of_measurement=UnitOfLength.KILOMETERS, device_class=SensorDeviceClass.DISTANCE, state_class=SensorStateClass.TOTAL_INCREASING),
    SensorEntityDescription(key="voltage", name="Voltage", native_unit_of_measurement=UnitOfElectricPotential.VOLT, device_class=SensorDeviceClass.VOLTAGE, state_class=_M),
    SensorEntityDescription(key="current", name="Current", native_unit_of_measurement=UnitOfElectricCurrent.AMPERE, device_class=SensorDeviceClass.CURRENT, state_class=_M),
    SensorEntityDescription(key="bat_temp", name="Battery temperature", native_unit_of_measurement=UnitOfTemperature.CELSIUS, device_class=SensorDeviceClass.TEMPERATURE, state_class=_M),
    SensorEntityDescription(key="ext_temp", name="Outside temperature", native_unit_of_measurement=UnitOfTemperature.CELSIUS, device_class=SensorDeviceClass.TEMPERATURE, state_class=_M),
    SensorEntityDescription(key="esp_battery", name="Logger battery", native_unit_of_measurement=PERCENTAGE, device_class=SensorDeviceClass.BATTERY, state_class=_M),
    SensorEntityDescription(key="lte_signal", name="LTE signal", native_unit_of_measurement=PERCENTAGE, state_class=_M, icon="mdi:signal"),
    SensorEntityDescription(key="operator", name="Mobile operator", icon="mdi:sim"),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id][1]
    entities: list[IdmateSensor] = []
    for device, vehicle in (coordinator.data or {}).items():
        for desc in SENSORS:
            entities.append(IdmateSensor(coordinator, entry.entry_id, device, vehicle, desc))
    async_add_entities(entities)


class IdmateSensor(IdmateVehicleEntity, SensorEntity):
    """A single field of an imported vehicle."""

    def __init__(self, coordinator, entry_id, device, vehicle, description):
        super().__init__(coordinator, entry_id, device, vehicle)
        self.entity_description = description
        self._attr_unique_id = f"{entry_id}_{device}_{description.key}"

    @property
    def native_value(self):
        return self._state.get(self.entity_description.key)

    @property
    def available(self) -> bool:
        return super().available and self.entity_description.key in self._state
