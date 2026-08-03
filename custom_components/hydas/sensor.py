"""Sensor platform for HyDAS."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from urllib.parse import urlparse

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import Measurement
from .const import DOMAIN
from .coordinator import HyDASCoordinator
from .helpers import parameter_icon, station_display_name


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up all discovered sensors and add newly discovered ones later."""
    coordinator: HyDASCoordinator = hass.data[DOMAIN][entry.entry_id]
    known: set[tuple[str, str]] = set()
    status_stations_added: set[str] = set()
    health_added = False

    @callback
    def add_new_entities() -> None:
        nonlocal health_added
        new_keys = set(coordinator.data) - known
        entities: list[SensorEntity] = [
            HyDASSensor(coordinator, entry, key) for key in sorted(new_keys)
        ]
        known.update(new_keys)
        stations_with_status = {
            str(measurement.station["id"])
            for measurement in coordinator.data.values()
            if isinstance(measurement.station.get("status"), dict)
            and str(measurement.station["id"]) not in status_stations_added
        }
        for station_id in sorted(stations_with_status):
            status_stations_added.add(station_id)
            entities.extend(
                (
                    HyDASStationStatusSensor(coordinator, entry, station_id),
                    HyDASStationStatusSinceSensor(coordinator, entry, station_id),
                    HyDASStationStatusExpectedEndSensor(coordinator, entry, station_id),
                )
            )
        if coordinator.health_supported and not health_added:
            health_added = True
            entities.extend(
                (
                    HyDASHealthStatusSensor(coordinator, entry),
                    HyDASHealthUptimeSensor(coordinator, entry),
                    HyDASHealthTimestampSensor(coordinator, entry),
                )
            )
        if entities:
            async_add_entities(entities)

    add_new_entities()
    entry.async_on_unload(coordinator.async_add_listener(add_new_entities))


class HyDASSensor(CoordinatorEntity[HyDASCoordinator], SensorEntity):
    """Representation of one HyDAS station parameter."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: HyDASCoordinator,
        entry: ConfigEntry,
        key: tuple[str, str],
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._key = key
        self._attr_unique_id = f"{entry.entry_id}_{key[0]}_{key[1]}"

    @property
    def measurement(self) -> Measurement | None:
        return self.coordinator.data.get(self._key)

    @property
    def name(self) -> str:
        measurement = self.measurement
        return (
            str(measurement.parameter.get("name") or self._key[1]) if measurement else self._key[1]
        )

    @property
    def native_value(self) -> float | int | None:
        return self.measurement.value if self.measurement else None

    @property
    def native_unit_of_measurement(self) -> str | None:
        return self.measurement.parameter.get("unitDisplay") if self.measurement else None

    @property
    def icon(self) -> str | None:
        """Return an icon matching the standardized observed property."""
        return parameter_icon(self.measurement.parameter) if self.measurement else None

    @property
    def available(self) -> bool:
        return super().available and self.measurement is not None

    @property
    def device_info(self) -> DeviceInfo:
        measurement = self.measurement
        station: dict[str, Any] = measurement.station if measurement else {}
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self._entry.entry_id}_{self._key[0]}")},
            name=station_display_name(station),
            manufacturer=station.get("operator"),
            configuration_url=station.get("url"),
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        measurement = self.measurement
        if not measurement:
            return {}
        parameter = measurement.parameter
        station = measurement.station
        attributes: dict[str, Any] = {
            "station_id": self._key[0],
            "parameter_id": self._key[1],
            "water_body": station.get("waterBodyName"),
            "procedure": parameter.get("procedure"),
            "measurement_interval": parameter.get("interval"),
            "status": (parameter.get("status") or {}).get("condition"),
            "status_message": (parameter.get("status") or {}).get("message"),
        }
        if measurement.timestamp:
            try:
                attributes["measurement_timestamp"] = datetime.fromisoformat(measurement.timestamp)
            except ValueError:
                attributes["measurement_timestamp"] = measurement.timestamp
        return {key: value for key, value in attributes.items() if value is not None}


class HyDASHealthSensorBase(CoordinatorEntity[HyDASCoordinator], SensorEntity):
    """Base class for API-level health sensors."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: HyDASCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry

    @property
    def available(self) -> bool:
        return (
            super().available
            and self.coordinator.health_available
            and self.coordinator.health is not None
        )

    @property
    def device_info(self) -> DeviceInfo:
        hostname = urlparse(self.coordinator.client.base_url).hostname
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self._entry.entry_id}_api")},
            name=f"HyDAS API - {hostname or self._entry.title}",
            configuration_url=self.coordinator.client.base_url,
        )


class HyDASHealthStatusSensor(HyDASHealthSensorBase):
    """Overall health status of a HyDAS API."""

    _attr_translation_key = "health_status"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["healthy", "degraded", "unhealthy"]
    _attr_icon = "mdi:heart-pulse"

    def __init__(self, coordinator: HyDASCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_health_status"

    @property
    def native_value(self) -> str | None:
        return self.coordinator.health.status if self.coordinator.health else None

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        health = self.coordinator.health
        return {"message": health.message} if health and health.message else {}


class HyDASHealthUptimeSensor(HyDASHealthSensorBase):
    """Uptime reported by a HyDAS API."""

    _attr_translation_key = "health_uptime"
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_icon = "mdi:timer-outline"

    def __init__(self, coordinator: HyDASCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_health_uptime"

    @property
    def native_value(self) -> int | None:
        return self.coordinator.health.uptime if self.coordinator.health else None


class HyDASHealthTimestampSensor(HyDASHealthSensorBase):
    """Timestamp of the latest API health check."""

    _attr_translation_key = "health_timestamp"
    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_icon = "mdi:clock-check-outline"

    def __init__(self, coordinator: HyDASCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_unique_id = f"{entry.entry_id}_health_timestamp"

    @property
    def native_value(self) -> datetime | None:
        health = self.coordinator.health
        return datetime.fromisoformat(health.timestamp) if health else None


class HyDASStationStatusSensorBase(CoordinatorEntity[HyDASCoordinator], SensorEntity):
    """Base class for station-level operational status sensors."""

    _attr_has_entity_name = True
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: HyDASCoordinator, entry: ConfigEntry, station_id: str) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._station_id = station_id

    @property
    def station(self) -> dict[str, Any] | None:
        """Return current station metadata from any of its measurements."""
        return next(
            (
                measurement.station
                for measurement in self.coordinator.data.values()
                if str(measurement.station.get("id")) == self._station_id
            ),
            None,
        )

    @property
    def station_status(self) -> dict[str, Any] | None:
        station = self.station
        status = station.get("status") if station else None
        return status if isinstance(status, dict) else None

    @property
    def available(self) -> bool:
        return super().available and self.station_status is not None

    @property
    def device_info(self) -> DeviceInfo:
        station = self.station or {"id": self._station_id}
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self._entry.entry_id}_{self._station_id}")},
            name=station_display_name(station),
            manufacturer=station.get("operator"),
            configuration_url=station.get("url"),
        )


class HyDASStationStatusSensor(HyDASStationStatusSensorBase):
    """Operational condition of one station."""

    _attr_translation_key = "station_status"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = [
        "operational",
        "impaired",
        "decommissioned",
        "unavailable",
        "degraded",
        "sensor-malfunction",
        "communication-failure",
        "power-outage",
        "maintenance",
        "construction",
        "calibration",
        "data-quality",
        "environmental",
        "offline",
        "other",
    ]

    def __init__(self, coordinator: HyDASCoordinator, entry: ConfigEntry, station_id: str) -> None:
        super().__init__(coordinator, entry, station_id)
        self._attr_unique_id = f"{entry.entry_id}_{station_id}_station_status"

    @property
    def native_value(self) -> str | None:
        status = self.station_status
        condition = status.get("condition") if status else None
        return condition if isinstance(condition, str) else None

    @property
    def icon(self) -> str:
        return (
            "mdi:check-circle-outline"
            if self.native_value == "operational"
            else "mdi:alert-circle-outline"
        )

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        status = self.station_status or {}
        return {
            key: value
            for key, value in {
                "message": status.get("message"),
                "contact": status.get("contact"),
            }.items()
            if isinstance(value, str) and value
        }


class HyDASStationStatusTimestampSensor(HyDASStationStatusSensorBase):
    """Base class for optional station status timestamps."""

    _attr_device_class = SensorDeviceClass.TIMESTAMP
    _attr_entity_registry_enabled_default = False
    status_key: str

    @property
    def native_value(self) -> datetime | None:
        value = (self.station_status or {}).get(self.status_key)
        if not isinstance(value, str):
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None


class HyDASStationStatusSinceSensor(HyDASStationStatusTimestampSensor):
    """Timestamp since the current station condition applies."""

    _attr_translation_key = "station_status_since"
    _attr_icon = "mdi:clock-start"
    status_key = "since"

    def __init__(self, coordinator: HyDASCoordinator, entry: ConfigEntry, station_id: str) -> None:
        super().__init__(coordinator, entry, station_id)
        self._attr_unique_id = f"{entry.entry_id}_{station_id}_station_status_since"


class HyDASStationStatusExpectedEndSensor(HyDASStationStatusTimestampSensor):
    """Expected end of the current station condition."""

    _attr_translation_key = "station_status_expected_end"
    _attr_icon = "mdi:clock-end"
    status_key = "expectedEnd"

    def __init__(self, coordinator: HyDASCoordinator, entry: ConfigEntry, station_id: str) -> None:
        super().__init__(coordinator, entry, station_id)
        self._attr_unique_id = f"{entry.entry_id}_{station_id}_station_status_expected_end"
