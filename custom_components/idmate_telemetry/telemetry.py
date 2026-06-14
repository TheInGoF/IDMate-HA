"""Build and publish IDMate binary telemetry telegrams over MQTT.

The telegram is byte-identical to the ESP32 firmware (IDTelemetry, protocol
v2) and is decrypted unchanged by the IDMate server. Layout:

    [0x02][IV 16B][ AES-256-CBC( <u32 mask LE><u32 ts LE><fields> ) ]

Fields are packed in ascending bit order; PKCS7 (128-bit) padding.
"""

from __future__ import annotations

import logging
import os
import ssl
import struct
import time

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.padding import PKCS7

from homeassistant.core import HomeAssistant

from .const import PROTO_VERSION

_LOGGER = logging.getLogger(__name__)

# (bit, key, struct_fmt | None=bool, divisor | None) — MUST match the IDMate
# server decoder (_BIN_FIELDS_*) and the firmware (BF_* enum) exactly.
_SCHEMA = [
    (0, "la", "<i", 1_000_000),
    (1, "lo", "<i", 1_000_000),
    (2, "hd", "<H", None),
    (3, "s", "<H", 10),
    (4, "u", "<H", None),
    (5, "i", "<h", None),
    (6, "p", "<h", 10),
    (7, "v", "<H", 10),
    (8, "c", None, None),   # bool: set bit == true
    (9, "dc", None, None),  # bool
    (10, "bt", "<b", None),
    (11, "et", "<b", None),
    (12, "r", "<H", 10),
    (13, "ca", "<H", 10),
    (14, "kw", "<I", 10),
    (15, "pk", None, None),  # bool
    (16, "od", "<I", 10),
    (17, "ls", "<B", None),
    (18, "bd", "<B", None),
    (19, "lp", "<H", None),
]

_MILES_TO_KM = 1.609344


def build_telegram(aes_key: bytes, values: dict, ts: int) -> bytes:
    """Build a v2 telegram. ``values`` maps schema keys to numbers; bool keys
    are sent only when truthy. Out-of-range fields are skipped, not wrapped."""
    mask = 0
    body = b""
    for bit, key, fmt, divisor in _SCHEMA:
        if key not in values or values[key] is None:
            continue
        if fmt is None:
            if values[key]:
                mask |= 1 << bit
            continue
        raw = int(round(values[key] * divisor)) if divisor else int(round(values[key]))
        try:
            packed = struct.pack(fmt, raw)
        except struct.error:
            continue  # value out of range for this field -> omit
        mask |= 1 << bit
        body += packed

    plaintext = struct.pack("<I", mask) + struct.pack("<I", int(ts)) + body

    padder = PKCS7(128).padder()
    padded = padder.update(plaintext) + padder.finalize()

    iv = os.urandom(16)
    encryptor = Cipher(algorithms.AES(aes_key), modes.CBC(iv)).encryptor()
    ciphertext = encryptor.update(padded) + encryptor.finalize()

    return bytes([PROTO_VERSION]) + iv + ciphertext


class IdmateTelemetry:
    """Owns a persistent MQTT connection and publishes telegrams on a timer."""

    def __init__(self, hass: HomeAssistant, cfg: dict) -> None:
        self.hass = hass
        self._cfg = cfg
        self._aes_key = bytes.fromhex(cfg["aes_key"])
        self._topic = f"tele/{cfg['device']}/data"
        self._client = None

    # ── lifecycle ────────────────────────────────────────────
    def start(self) -> None:
        """Create the MQTT client and connect (runs in executor)."""
        import paho.mqtt.client as mqtt

        client = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=f"ha-idmate-{self._cfg['device']}",
        )
        if self._cfg.get("username"):
            client.username_pw_set(self._cfg["username"], self._cfg.get("password", ""))
        if self._cfg.get("tls", True):
            if self._cfg.get("tls_insecure", True):
                client.tls_set(cert_reqs=ssl.CERT_NONE)
                client.tls_insecure_set(True)
            else:
                client.tls_set()
        client.reconnect_delay_set(min_delay=1, max_delay=60)
        client.connect_async(
            self._cfg["host"], int(self._cfg.get("port", 8883)), keepalive=60
        )
        client.loop_start()
        self._client = client
        _LOGGER.info(
            "IDMate Telemetry: MQTT client for '%s' -> %s:%s",
            self._cfg["device"],
            self._cfg["host"],
            self._cfg.get("port", 8883),
        )

    def stop(self) -> None:
        """Disconnect and tear down the MQTT client (runs in executor)."""
        if self._client is not None:
            try:
                self._client.loop_stop()
                self._client.disconnect()
            except Exception:  # noqa: BLE001 - best-effort cleanup
                pass
            self._client = None

    # ── per-tick publish ─────────────────────────────────────
    def tick(self) -> None:
        """Read mapped entities and publish one telegram, if conditions allow."""
        values = self._collect_values()
        if values is None:
            return
        telegram = build_telegram(self._aes_key, values, int(time.time()))
        if self._client is None:
            return
        result = self._client.publish(self._topic, payload=telegram, qos=0)
        _LOGGER.debug(
            "IDMate Telemetry: %d bytes -> %s (rc=%s)",
            len(telegram),
            self._topic,
            getattr(result, "rc", "?"),
        )

    # ── state reading ────────────────────────────────────────
    def _num(self, entity_id: str | None, attr: str | None = None):
        """State (or attribute) of an entity as float, or None if unusable."""
        if not entity_id:
            return None
        st = self.hass.states.get(entity_id)
        if st is None or st.state in (None, "unavailable", "unknown", ""):
            return None
        raw = st.attributes.get(attr) if attr else st.state
        try:
            return float(raw)
        except (TypeError, ValueError):
            return None

    def _unit(self, entity_id: str | None) -> str:
        if not entity_id:
            return ""
        st = self.hass.states.get(entity_id)
        if st is None:
            return ""
        return str(st.attributes.get("unit_of_measurement") or "").strip()

    def _collect_values(self) -> dict | None:
        cfg = self._cfg
        soc = self._num(cfg.get("soc_entity"))
        if soc is None or soc < 0:
            return None  # no valid SoC -> car asleep, send nothing

        speed = self._num(cfg.get("speed_entity")) or 0.0
        speed_unit = self._unit(cfg.get("speed_entity")).lower()
        if speed_unit == "mph":
            speed *= _MILES_TO_KM

        charging_st = self.hass.states.get(cfg.get("charging_entity") or "")
        charging = bool(charging_st and charging_st.state == "on")

        if speed <= 0 and not charging:
            return None  # parked and not charging -> let the car sleep

        values: dict = {
            "s": soc,
            "v": speed,
            "pk": 1 if speed <= 0 else 0,
            "c": 1 if charging else 0,
            # dc omitted -> bit clear -> "no DC fast charging"
        }

        lat = self._num(cfg.get("location_entity"), attr="latitude")
        lon = self._num(cfg.get("location_entity"), attr="longitude")
        if lat is not None and lon is not None and (lat != 0 or lon != 0):
            values["la"] = lat
            values["lo"] = lon

        odo = self._num(cfg.get("odometer_entity"))
        if odo is not None and odo >= 0:
            values["od"] = self._to_km(odo, self._unit(cfg.get("odometer_entity")))

        rng = self._num(cfg.get("range_entity"))
        if rng is not None and rng >= 0:
            values["r"] = self._to_km(rng, self._unit(cfg.get("range_entity")))

        power = self._num(cfg.get("power_entity"))
        if power is not None and power != 0:
            values["p"] = self._to_kw(power, self._unit(cfg.get("power_entity")))

        return values

    @staticmethod
    def _to_km(value: float, unit: str) -> float:
        u = unit.lower()
        if u == "m":
            return value / 1000.0
        if u == "mi":
            return value * _MILES_TO_KM
        return value  # assume km

    @staticmethod
    def _to_kw(value: float, unit: str) -> float:
        return value / 1000.0 if unit.lower() == "w" else value  # assume kW
