"""Data coordinator for HyDAS."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import HealthStatus, HyDASClient, HyDASError, Measurement
from .flood import FloodAlert, FloodAlertData, LHPClient, LHPError, alert_applies_to_station

_LOGGER = logging.getLogger(__name__)


class HyDASCoordinator(DataUpdateCoordinator[dict[tuple[str, str], Measurement]]):
    """Coordinate discovery and value updates for one HyDAS API."""

    def __init__(
        self,
        hass,
        client: HyDASClient,
        flood_client: LHPClient,
        station_ids: list[str],
        interval: int,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="HyDAS API",
            update_interval=timedelta(seconds=interval),
        )
        self.client = client
        self.flood_client = flood_client
        self.station_ids = station_ids
        self.health: HealthStatus | None = None
        self.health_supported: bool | None = None
        self.health_available = False
        self.flood_alert_data: FloodAlertData | None = None
        self.flood_alerts: dict[str, tuple[FloodAlert, ...]] = {}
        self.flood_available = False

    async def _async_update_data(self) -> dict[tuple[str, str], Measurement]:
        try:
            measurements = await self.client.async_get_measurements(self.station_ids or None)
        except HyDASError as err:
            raise UpdateFailed(f"Error communicating with HyDAS API: {err}") from err

        try:
            health = await self.client.async_get_health()
        except HyDASError as err:
            self.health_available = False
            _LOGGER.warning("Error requesting optional HyDAS health endpoint: %s", err)
        else:
            self.health_supported = health is not None
            self.health_available = health is not None
            if health is not None:
                self.health = health

        hydas_stations = {
            str(measurement.station["id"]): measurement.station
            for measurement in measurements.values()
        }
        if not hydas_stations:
            self.flood_alerts = {}
            self.flood_available = False
            return measurements
        states = {
            state
            for station in hydas_stations.values()
            if isinstance((state := station.get("state")), str)
        }
        try:
            flood_data = await self.flood_client.async_get_alerts(states)
        except LHPError as err:
            self.flood_available = False
            _LOGGER.warning("Error requesting optional LHP flood alerts: %s", err)
        else:
            self.flood_alert_data = flood_data
            self.flood_available = True
            self.flood_alerts = {
                station_id: matches
                for station_id, station in hydas_stations.items()
                if (
                    matches := tuple(
                        alert
                        for alert in flood_data.alerts
                        if alert_applies_to_station(alert, station)
                    )
                )
            }
        return measurements
