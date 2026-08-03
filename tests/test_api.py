"""Tests for the HyDAS API client."""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from aiohttp import ClientConnectionError

from custom_components.hydas.api import (
    HyDASClient,
    HyDASConnectionError,
    HyDASResponseError,
)


class FakeResponse:
    """Small asynchronous aiohttp response replacement."""

    def __init__(self, payload: Any = None, status: int = 200, error: Exception | None = None):
        self.payload = payload
        self.status = status
        self.error = error

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return None

    def raise_for_status(self):
        if self.error:
            raise self.error

    async def json(self, **kwargs):
        if isinstance(self.payload, Exception):
            raise self.payload
        return self.payload


class FakeSession:
    """Record requests and return queued responses."""

    def __init__(self, *responses: FakeResponse):
        self.responses = list(responses)
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def get(self, url: str, **kwargs):
        self.calls.append((url, kwargs))
        return self.responses.pop(0)


@pytest.mark.asyncio
async def test_get_stations_normalizes_url_and_passes_ids():
    session = FakeSession(FakeResponse({"data": [{"id": "a"}]}))
    client = HyDASClient(session, "https://example.test/api/")

    assert await client.async_get_stations(["a", "b"]) == [{"id": "a"}]
    assert session.calls[0][0] == "https://example.test/api/stations"
    assert session.calls[0][1]["params"] == {"ids": "a,b"}
    assert session.calls[0][1]["headers"] == {"Accept": "application/json"}


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", [[], {}, {"data": {}}, None])
async def test_get_data_rejects_invalid_envelopes(payload):
    client = HyDASClient(FakeSession(FakeResponse(payload)), "https://example.test")

    with pytest.raises(HyDASResponseError, match="data list"):
        await client.async_get_stations()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "error",
    [ClientConnectionError("offline"), asyncio.TimeoutError()],
)
async def test_get_data_maps_connection_errors(error):
    client = HyDASClient(
        FakeSession(FakeResponse({"data": []}, error=error)), "https://example.test"
    )

    with pytest.raises(HyDASConnectionError):
        await client.async_get_stations()


@pytest.mark.asyncio
async def test_get_data_maps_invalid_json():
    client = HyDASClient(FakeSession(FakeResponse(ValueError())), "https://example.test")

    with pytest.raises(HyDASResponseError, match="valid JSON"):
        await client.async_get_stations()


@pytest.mark.asyncio
async def test_latest_value_selects_newest_and_quotes_path():
    session = FakeSession(
        FakeResponse(
            {
                "data": [
                    {"timestamp": "2026-01-01T10:00:00+00:00", "value": 1.0},
                    {"timestamp": "2026-01-01T11:00:00+00:00", "value": 2.0},
                    {"value": 99},
                ]
            }
        )
    )
    client = HyDASClient(session, "https://example.test")

    assert await client.async_get_latest_value("station/a", "water level") == (
        2.0,
        "2026-01-01T11:00:00+00:00",
    )
    assert session.calls[0][0].endswith("/stations/station%2Fa/parameters/water%20level/values")


@pytest.mark.asyncio
async def test_latest_value_handles_empty_data():
    client = HyDASClient(FakeSession(FakeResponse({"data": []})), "https://example.test")

    assert await client.async_get_latest_value("a", "b") == (None, None)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("item", "message"),
    [
        ({"timestamp": "not-a-date", "value": 1}, "timestamp"),
        ({"timestamp": "2026-01-01T00:00:00+00:00", "value": "high"}, "numeric"),
    ],
)
async def test_latest_value_rejects_invalid_measurements(item, message):
    client = HyDASClient(FakeSession(FakeResponse({"data": [item]})), "https://example.test")

    with pytest.raises(HyDASResponseError, match=message):
        await client.async_get_latest_value("a", "b")


@pytest.mark.asyncio
async def test_health_accepts_valid_payload():
    client = HyDASClient(
        FakeSession(
            FakeResponse(
                {
                    "status": "degraded",
                    "message": "maintenance",
                    "timestamp": "2026-01-01T00:00:00+00:00",
                    "uptime": 42,
                }
            )
        ),
        "https://example.test",
    )

    health = await client.async_get_health()
    assert health is not None
    assert health.status == "degraded"
    assert health.uptime == 42


@pytest.mark.asyncio
async def test_health_404_is_optional():
    client = HyDASClient(FakeSession(FakeResponse(status=404)), "https://example.test")

    assert await client.async_get_health() is None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        [],
        {"status": "unknown", "timestamp": "2026-01-01T00:00:00Z", "uptime": 1},
        {"status": "healthy", "timestamp": "invalid", "uptime": 1},
        {"status": "healthy", "timestamp": "2026-01-01T00:00:00Z", "uptime": True},
        {
            "status": "healthy",
            "timestamp": "2026-01-01T00:00:00Z",
            "uptime": 1,
            "message": 2,
        },
    ],
)
async def test_health_rejects_invalid_payload(payload):
    client = HyDASClient(FakeSession(FakeResponse(payload)), "https://example.test")

    with pytest.raises(HyDASResponseError):
        await client.async_get_health()


@pytest.mark.asyncio
async def test_validate_reports_unknown_stations():
    client = HyDASClient(
        FakeSession(FakeResponse({"data": [{"id": "known"}]})), "https://example.test"
    )

    with pytest.raises(HyDASResponseError, match="missing"):
        await client.async_validate(["known", "missing"])


@pytest.mark.asyncio
async def test_measurement_discovery_builds_stable_keys():
    client = HyDASClient(
        FakeSession(
            FakeResponse({"data": [{"id": "s1", "name": "Station"}]}),
            FakeResponse({"data": [{"id": "p1", "name": "Level"}]}),
            FakeResponse({"data": [{"timestamp": "2026-01-01T00:00:00Z", "value": 3.5}]}),
        ),
        "https://example.test",
    )

    measurements = await client.async_get_measurements()

    assert list(measurements) == [("s1", "p1")]
    assert measurements[("s1", "p1")].value == 3.5
