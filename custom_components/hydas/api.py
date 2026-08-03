"""Async client for APIs implementing the HydroDaten API standard."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib.parse import quote

from aiohttp import ClientError, ClientSession, ClientTimeout


class HyDASError(Exception):
    """Base exception for HyDAS client errors."""


class HyDASConnectionError(HyDASError):
    """Raised when the API cannot be reached."""


class HyDASResponseError(HyDASError):
    """Raised when the API response has an unexpected shape."""


@dataclass(frozen=True, slots=True)
class Measurement:
    """Latest value and metadata for one station parameter."""

    station: dict[str, Any]
    parameter: dict[str, Any]
    value: float | int | None
    timestamp: str | None

    @property
    def key(self) -> tuple[str, str]:
        """Return the stable station/parameter key."""
        return str(self.station["id"]), str(self.parameter["id"])


@dataclass(frozen=True, slots=True)
class HealthStatus:
    """Health information reported by the optional /health endpoint."""

    status: str
    message: str | None
    timestamp: str
    uptime: int


class HyDASClient:
    """Small client for the standardized HyDAS endpoints."""

    def __init__(self, session: ClientSession, base_url: str) -> None:
        self._session = session
        self.base_url = base_url.rstrip("/")
        # A full API can expose many station/parameter combinations. Keep the
        # service and Home Assistant responsive while polling them.
        self._request_limit = asyncio.Semaphore(10)

    async def _get_data(
        self, path: str, params: dict[str, str] | None = None
    ) -> list[dict[str, Any]]:
        try:
            async with self._request_limit:
                async with self._session.get(
                    f"{self.base_url}/{path.lstrip('/')}",
                    params=params,
                    timeout=ClientTimeout(total=30),
                    headers={"Accept": "application/json"},
                ) as response:
                    response.raise_for_status()
                    payload = await response.json(content_type=None)
        except (ClientError, asyncio.TimeoutError) as err:
            raise HyDASConnectionError(str(err)) from err
        except (ValueError, TypeError) as err:
            raise HyDASResponseError("The API did not return valid JSON") from err

        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, list):
            raise HyDASResponseError("The response does not contain a data list")
        return data

    async def async_get_stations(
        self, station_ids: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """Return stations, optionally restricted to IDs."""
        params = {"ids": ",".join(station_ids)} if station_ids else None
        return await self._get_data("stations", params)

    async def async_get_health(self) -> HealthStatus | None:
        """Return API health information, or None when unsupported."""
        try:
            async with self._request_limit:
                async with self._session.get(
                    f"{self.base_url}/health",
                    timeout=ClientTimeout(total=30),
                    headers={"Accept": "application/json"},
                ) as response:
                    if response.status == 404:
                        return None
                    response.raise_for_status()
                    payload = await response.json(content_type=None)
        except (ClientError, asyncio.TimeoutError) as err:
            raise HyDASConnectionError(str(err)) from err
        except (ValueError, TypeError) as err:
            raise HyDASResponseError("The health endpoint did not return valid JSON") from err

        if not isinstance(payload, dict):
            raise HyDASResponseError("The health response is not an object")
        status = payload.get("status")
        message = payload.get("message")
        timestamp = payload.get("timestamp")
        uptime = payload.get("uptime")
        if status not in {"healthy", "degraded", "unhealthy"}:
            raise HyDASResponseError("The health response contains an invalid status")
        if not isinstance(timestamp, str):
            raise HyDASResponseError("The health response is missing its timestamp")
        try:
            datetime.fromisoformat(timestamp)
        except ValueError as err:
            raise HyDASResponseError("The health timestamp is not ISO-8601") from err
        if not isinstance(uptime, int) or isinstance(uptime, bool) or uptime < 0:
            raise HyDASResponseError("The health response contains an invalid uptime")
        if message is not None and not isinstance(message, str):
            raise HyDASResponseError("The health message is not a string")
        return HealthStatus(status, message, timestamp, uptime)

    async def async_get_parameters(self, station_id: str) -> list[dict[str, Any]]:
        """Return parameters offered by a station."""
        station = quote(station_id, safe="")
        return await self._get_data(f"stations/{station}/parameters")

    async def async_get_latest_value(
        self, station_id: str, parameter_id: str
    ) -> tuple[float | int | None, str | None]:
        """Return the most recent value reported by a parameter."""
        station = quote(station_id, safe="")
        parameter = quote(parameter_id, safe="")
        values = await self._get_data(
            f"stations/{station}/parameters/{parameter}/values"
        )
        valid = [item for item in values if isinstance(item.get("timestamp"), str)]
        if not valid:
            return None, None
        try:
            latest = max(
                valid, key=lambda item: datetime.fromisoformat(item["timestamp"])
            )
        except ValueError as err:
            raise HyDASResponseError("A measurement timestamp is not ISO-8601") from err
        value = latest.get("value")
        if value is not None and not isinstance(value, (int, float)):
            raise HyDASResponseError("A measurement value is not numeric or null")
        return value, latest["timestamp"]

    async def async_validate(self, station_ids: list[str] | None = None) -> None:
        """Validate connectivity and configured station IDs."""
        stations = await self.async_get_stations(station_ids)
        if any(not isinstance(item.get("id"), str) for item in stations):
            raise HyDASResponseError("A station is missing its string ID")
        if station_ids:
            found = {str(station.get("id")) for station in stations}
            missing = set(station_ids) - found
            if missing:
                raise HyDASResponseError(
                    f"Unknown station IDs: {', '.join(sorted(missing))}"
                )

    async def async_get_measurements(
        self, station_ids: list[str] | None = None
    ) -> dict[tuple[str, str], Measurement]:
        """Discover stations/parameters and fetch their latest values."""
        stations = await self.async_get_stations(station_ids)

        async def load_station(station: dict[str, Any]) -> list[Measurement]:
            if not isinstance(station.get("id"), str):
                raise HyDASResponseError("A station is missing its string ID")
            station_id = station["id"]
            parameters = await self.async_get_parameters(station_id)

            async def load_parameter(parameter: dict[str, Any]) -> Measurement:
                if not isinstance(parameter.get("id"), str):
                    raise HyDASResponseError("A parameter is missing its string ID")
                value, timestamp = await self.async_get_latest_value(
                    station_id, parameter["id"]
                )
                return Measurement(station, parameter, value, timestamp)

            return await asyncio.gather(*(load_parameter(item) for item in parameters))

        station_results = await asyncio.gather(*(load_station(item) for item in stations))
        return {measurement.key: measurement for group in station_results for measurement in group}
