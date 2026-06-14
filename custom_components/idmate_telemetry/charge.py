"""Charge-session tracker: post 15-minute meter readings to IDMate.

Replicates the Home Assistant "quarter-hourly charge reading" automation
inside the integration. On every wall-clock quarter hour it reads a (monotonic)
energy meter, computes the consumption since the last tick and POSTs it to the
IDMate webhook (``/api/charge/reading``). The IDMate server aggregates the
readings into sessions itself (gap > 60 min = new session).

The last meter value is persisted via HA's Store, so a restart does not emit
phantom consumption.
"""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    CONF_BASE_FEE,
    CONF_CHARGE_ODOMETER,
    CONF_CHARGE_SOC,
    CONF_METER,
    CONF_PRICE,
    CONF_TOKEN,
    CONF_URL,
    CONF_VEHICLE_ENTITY,
    CONF_VEHICLE_PLATE,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)
_UNUSABLE = (None, "unavailable", "unknown", "")


class IdmateChargeTracker:
    """Posts quarter-hourly charge readings to the IDMate webhook."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, cfg: dict) -> None:
        self.hass = hass
        self._cfg = cfg
        self._store: Store = Store(hass, 1, f"{DOMAIN}_charge_{entry.entry_id}")
        self._last_meter: float | None = None
        self._unsub = None

    async def async_start(self) -> None:
        stored = await self._store.async_load()
        if stored and stored.get("last_meter") is not None:
            # Restore the anchor instead of re-anchoring: if HA was down across
            # one or more ticks, the next tick reports the full difference since
            # this value (e.g. a 30-min window). Nothing is lost — a monotonic
            # meter makes the diff exactly the real consumption.
            self._last_meter = float(stored["last_meter"])
        else:
            # First run only: anchor to the current meter so we never bill the
            # whole lifetime total as one window.
            self._last_meter = self._num(self._cfg.get(CONF_METER))
            await self._save()

        self._unsub = async_track_time_change(
            self.hass, self._on_quarter, minute=[0, 15, 30, 45], second=0
        )
        _LOGGER.info(
            "IDMate charge tracker active (meter=%s, anchor=%s)",
            self._cfg.get(CONF_METER),
            self._last_meter,
        )

    async def async_stop(self) -> None:
        if self._unsub is not None:
            self._unsub()
            self._unsub = None

    async def _save(self) -> None:
        await self._store.async_save({"last_meter": self._last_meter})

    # ── tick ─────────────────────────────────────────────────
    async def _on_quarter(self, now) -> None:
        meter = self._num(self._cfg.get(CONF_METER))
        if meter is None:
            return

        last = self._last_meter
        self._last_meter = meter
        await self._save()

        if last is None:
            return
        kwh = round(meter - last, 3)
        if kwh <= 0:
            return  # no consumption (or meter reset) -> nothing to report

        vehicle = self._vehicle()
        payload = {
            "vehicle": vehicle,
            "kwh": kwh,
            "meter_start": round(last, 3),
            "meter_end": round(meter, 3),
            "timestamp": dt_util.utcnow().strftime("%Y-%m-%dT%H:%M:%S"),
        }
        price = self._num(self._cfg.get(CONF_PRICE))
        if price is not None:
            payload["tibber_price"] = round(price, 4)
        base = self._num(self._cfg.get(CONF_BASE_FEE))
        if base is not None:
            payload["tibber_grundgebuehr"] = round(base, 4)
        odo = self._num(self._cfg.get(CONF_CHARGE_ODOMETER))
        if odo is not None:
            payload["odometer"] = odo
        soc = self._num(self._cfg.get(CONF_CHARGE_SOC))
        if soc is not None:
            payload["soc"] = soc

        await self._post(payload)

    async def _post(self, payload: dict) -> None:
        session = async_get_clientsession(self.hass)
        url = self._cfg[CONF_URL].rstrip("/") + "/api/charge/reading"
        headers = {
            "Authorization": f"Bearer {self._cfg.get(CONF_TOKEN, '')}",
            "Content-Type": "application/json",
        }
        try:
            async with session.post(
                url, json=payload, headers=headers, timeout=30
            ) as resp:
                if resp.status >= 400:
                    body = await resp.text()
                    _LOGGER.warning(
                        "IDMate charge reading failed (%s): %s", resp.status, body[:200]
                    )
                else:
                    _LOGGER.debug(
                        "IDMate charge reading sent: %.3f kWh, vehicle=%s",
                        payload["kwh"],
                        payload["vehicle"],
                    )
        except Exception as exc:  # noqa: BLE001 - network best-effort
            _LOGGER.warning("IDMate charge reading POST error: %s", exc)

    # ── helpers ──────────────────────────────────────────────
    def _vehicle(self) -> str:
        ent = self._cfg.get(CONF_VEHICLE_ENTITY)
        if ent:
            st = self.hass.states.get(ent)
            if st is not None and st.state not in _UNUSABLE:
                return str(st.state).strip()
        return str(self._cfg.get(CONF_VEHICLE_PLATE, "") or "").strip()

    def _num(self, entity_id: str | None):
        if not entity_id:
            return None
        st = self.hass.states.get(entity_id)
        if st is None or st.state in _UNUSABLE:
            return None
        try:
            return float(st.state)
        except (TypeError, ValueError):
            return None
