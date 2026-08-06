"""Tests for the HyDAS update coordinator."""

from unittest.mock import AsyncMock

import pytest
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.hydas.api import HealthStatus, HyDASConnectionError
from custom_components.hydas.coordinator import HyDASCoordinator


async def test_coordinator_updates_measurements_and_health(hass):
    client = AsyncMock()
    client.async_get_measurements.return_value = {("s", "p"): object()}
    client.async_get_health.return_value = HealthStatus("healthy", None, "2026-01-01T00:00:00Z", 10)
    coordinator = HyDASCoordinator(hass, client, ["s"], 60)

    result = await coordinator._async_update_data()

    assert ("s", "p") in result
    assert coordinator.health_supported is True
    assert coordinator.health_available is True


async def test_optional_health_failure_does_not_fail_update(hass):
    client = AsyncMock()
    client.async_get_measurements.return_value = {}
    client.async_get_health.side_effect = HyDASConnectionError("offline")
    coordinator = HyDASCoordinator(hass, client, [], 60)

    assert await coordinator._async_update_data() == {}
    assert coordinator.health_available is False


async def test_measurement_failure_becomes_update_failed(hass):
    client = AsyncMock()
    client.async_get_measurements.side_effect = HyDASConnectionError("offline")
    coordinator = HyDASCoordinator(hass, client, [], 60)

    with pytest.raises(UpdateFailed, match="Error communicating"):
        await coordinator._async_update_data()
