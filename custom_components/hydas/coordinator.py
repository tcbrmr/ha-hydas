"""Data coordinator for HyDAS."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import HealthStatus, HyDASClient, HyDASError, Measurement

_LOGGER = logging.getLogger(__name__)


class HyDASCoordinator(DataUpdateCoordinator[dict[tuple[str, str], Measurement]]):
    """Coordinate discovery and value updates for one HyDAS API."""

    def __init__(self, hass, client: HyDASClient, station_ids: list[str], interval: int) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="HyDAS API",
            update_interval=timedelta(seconds=interval),
        )
        self.client = client
        self.station_ids = station_ids
        self.health: HealthStatus | None = None
        self.health_supported: bool | None = None
        self.health_available = False

    async def _async_update_data(self) -> dict[tuple[str, str], Measurement]:
        try:
            measurements = await self.client.async_get_measurements(
                self.station_ids or None
            )
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
        return measurements
