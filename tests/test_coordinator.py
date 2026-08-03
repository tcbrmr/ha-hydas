"""Tests for the HyDAS update coordinator."""

from unittest.mock import AsyncMock

import pytest
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.hydas.api import HealthStatus, HyDASConnectionError, Measurement
from custom_components.hydas.coordinator import HyDASCoordinator
from custom_components.hydas.flood import FloodAlert, FloodAlertData, LHPError


def _alert():
    return FloodAlert(
        "NW_rhein",
        "Polygon",
        [[[6.7, 51.1], [6.9, 51.1], [6.9, 51.3], [6.7, 51.3], [6.7, 51.1]]],
        "Rhein bei Düsseldorf",
        "Region",
        "Hochwasserwarnung",
        "https://example.test/warning",
        4,
        "Hochwasser",
        "LHP.NW.rhein",
        "Hochwasserzentrale",
        None,
        None,
        None,
        None,
        None,
        None,
        None,
    )


def _flood_client():
    client = AsyncMock()
    client.async_get_alerts.return_value = FloodAlertData(
        "2026-01-01T00:00:00+01:00",
        "https://www.hochwasserzentralen.de",
        "https://creativecommons.org/licenses/by/4.0/deed.de",
        (_alert(),),
    )
    return client


async def test_coordinator_updates_measurements_and_health(hass):
    client = AsyncMock()
    measurement = Measurement(
        {
            "id": "s",
            "state": "DE-NW",
            "coordinates": {"lat": 51.2255, "lon": 6.7699},
        },
        {"id": "p"},
        1.0,
        None,
    )
    client.async_get_measurements.return_value = {("s", "p"): measurement}
    client.async_get_health.return_value = HealthStatus("healthy", None, "2026-01-01T00:00:00Z", 10)
    flood_client = _flood_client()
    coordinator = HyDASCoordinator(hass, client, flood_client, ["s"], 60)

    result = await coordinator._async_update_data()

    assert ("s", "p") in result
    assert coordinator.health_supported is True
    assert coordinator.health_available is True
    assert coordinator.flood_available is True
    assert coordinator.flood_alerts["s"] == (_alert(),)
    flood_client.async_get_alerts.assert_awaited_once_with({"DE-NW"})


async def test_optional_health_failure_does_not_fail_update(hass):
    client = AsyncMock()
    client.async_get_measurements.return_value = {}
    client.async_get_health.side_effect = HyDASConnectionError("offline")
    coordinator = HyDASCoordinator(hass, client, _flood_client(), [], 60)

    assert await coordinator._async_update_data() == {}
    assert coordinator.health_available is False


async def test_measurement_failure_becomes_update_failed(hass):
    client = AsyncMock()
    client.async_get_measurements.side_effect = HyDASConnectionError("offline")
    coordinator = HyDASCoordinator(hass, client, _flood_client(), [], 60)

    with pytest.raises(UpdateFailed, match="Error communicating"):
        await coordinator._async_update_data()


async def test_optional_flood_failure_does_not_fail_update(hass):
    client = AsyncMock()
    measurement = Measurement({"id": "s", "state": "DE-NW"}, {"id": "p"}, 1.0, None)
    client.async_get_measurements.return_value = {("s", "p"): measurement}
    client.async_get_health.return_value = None
    flood_client = AsyncMock()
    flood_client.async_get_alerts.side_effect = LHPError("offline")
    coordinator = HyDASCoordinator(hass, client, flood_client, [], 60)

    assert await coordinator._async_update_data() == {("s", "p"): measurement}
    assert coordinator.flood_available is False
