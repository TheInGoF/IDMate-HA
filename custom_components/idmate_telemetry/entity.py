"""Shared base entity for imported IDMate vehicles."""

from __future__ import annotations

from homeassistant.helpers.device_info import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .importer import IdmateImportCoordinator


class IdmateVehicleEntity(CoordinatorEntity[IdmateImportCoordinator]):
    """Base for all entities of one imported vehicle."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: IdmateImportCoordinator,
        entry_id: str,
        device: str,
        vehicle: dict,
    ) -> None:
        super().__init__(coordinator)
        self._device = device
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"{entry_id}_{device}")},
            name=vehicle.get("name") or device,
            model=vehicle.get("model") or None,
            manufacturer="IDMate",
            serial_number=device,
        )

    @property
    def _vehicle(self) -> dict:
        return (self.coordinator.data or {}).get(self._device) or {}

    @property
    def _state(self) -> dict:
        return self._vehicle.get("state") or {}

    @property
    def available(self) -> bool:
        return super().available and self._device in (self.coordinator.data or {})
