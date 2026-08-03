"""Client and spatial matching helpers for official LHP flood alerts."""

from __future__ import annotations

import asyncio
import math
import re
from dataclasses import dataclass
from typing import Any

from aiohttp import ClientError, ClientSession, ClientTimeout

LHP_API_URL = "https://api.hochwasserzentralen.de/public/v1/data/alerts"
LHP_SOURCE_URL = "https://www.hochwasserzentralen.de"
RIVER_ALERT_MAX_DISTANCE_KM = 1.0


class LHPError(Exception):
    """Raised when LHP flood-alert data cannot be retrieved or parsed."""


@dataclass(frozen=True, slots=True)
class FloodAlert:
    """One official regional or river-section flood alert."""

    id: str
    geometry_type: str
    coordinates: Any
    area_description: str | None
    area_type: str | None
    headline: str
    link: str | None
    lhp_class: int
    class_name: str | None
    identifier: str | None
    sender_name: str | None
    sent: str | None
    onset: str | None
    expires: str | None
    severity: str | None
    certainty: str | None
    description: str | None
    instruction: str | None


@dataclass(frozen=True, slots=True)
class FloodAlertData:
    """LHP response metadata and normalized active alerts."""

    updated: str
    source: str
    licence: str | None
    alerts: tuple[FloodAlert, ...]


def _text(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None


def _normalize_alert(item: Any) -> FloodAlert | None:
    """Normalize an LHP alert with optional CAP details."""
    if not isinstance(item, dict):
        return None
    properties = item.get("properties")
    properties = properties if isinstance(properties, dict) else item
    geometry = item.get("geometry")
    if not isinstance(geometry, dict):
        return None
    geometry_type = geometry.get("type")
    coordinates = geometry.get("coordinates")
    if geometry_type not in {"Polygon", "MultiPolygon", "LineString"} or not isinstance(
        coordinates, list
    ):
        return None
    station_id = item.get("id")
    headline = properties.get("alertHeadline")
    raw_class = properties.get("lhpClass")
    try:
        lhp_class = int(raw_class)
    except (TypeError, ValueError):
        return None
    if (
        not isinstance(station_id, str)
        or not isinstance(headline, str)
        or lhp_class not in {1, 2, 4, 5, 6}
    ):
        return None

    cap = properties.get("cap")
    cap = cap if isinstance(cap, dict) else {}
    info = cap.get("info")
    info = info if isinstance(info, dict) else {}
    return FloodAlert(
        id=station_id,
        geometry_type=geometry_type,
        coordinates=coordinates,
        area_description=_text(properties.get("areaDesc")),
        area_type=_text(properties.get("areaType")),
        headline=_text(info.get("headline")) or headline,
        link=_text(properties.get("alertLink")) or _text(info.get("web")),
        lhp_class=lhp_class,
        class_name=_text(properties.get("lhpClassName")),
        identifier=_text(cap.get("identifier")),
        sender_name=_text(info.get("sendername")),
        sent=_text(cap.get("sent")),
        onset=_text(info.get("onset")),
        expires=_text(info.get("expires")),
        severity=_text(info.get("severity")),
        certainty=_text(info.get("certainty")),
        description=_text(info.get("description")),
        instruction=_text(info.get("instruction")),
    )


def _point_in_ring(lon: float, lat: float, ring: list[Any]) -> bool:
    """Return whether a longitude/latitude point is inside a linear ring."""
    inside = False
    previous = ring[-1] if ring else None
    for current in ring:
        if (
            not isinstance(previous, list)
            or not isinstance(current, list)
            or len(previous) < 2
            or len(current) < 2
        ):
            previous = current
            continue
        x1, y1 = previous[:2]
        x2, y2 = current[:2]
        if not all(isinstance(value, (int, float)) for value in (x1, y1, x2, y2)):
            previous = current
            continue
        if (y1 > lat) != (y2 > lat) and lon < (x2 - x1) * (lat - y1) / (y2 - y1) + x1:
            inside = not inside
        previous = current
    return inside


def _point_in_polygon(lon: float, lat: float, polygon: list[Any]) -> bool:
    """Return whether a point is inside a GeoJSON polygon, respecting holes."""
    if not polygon or not isinstance(polygon[0], list):
        return False
    return _point_in_ring(lon, lat, polygon[0]) and not any(
        _point_in_ring(lon, lat, ring) for ring in polygon[1:] if isinstance(ring, list)
    )


def _distance_to_line_km(lon: float, lat: float, line: list[Any]) -> float:
    """Approximate the shortest point-to-LineString distance in kilometres."""
    scale_x = 111.32 * math.cos(math.radians(lat))
    scale_y = 110.57
    shortest = math.inf
    for start, end in zip(line, line[1:]):
        if (
            not isinstance(start, list)
            or not isinstance(end, list)
            or len(start) < 2
            or len(end) < 2
            or not all(isinstance(value, (int, float)) for value in (*start[:2], *end[:2]))
        ):
            continue
        ax, ay = (start[0] - lon) * scale_x, (start[1] - lat) * scale_y
        bx, by = (end[0] - lon) * scale_x, (end[1] - lat) * scale_y
        dx, dy = bx - ax, by - ay
        factor = max(0.0, min(1.0, -(ax * dx + ay * dy) / (dx * dx + dy * dy))) if dx or dy else 0
        shortest = min(shortest, math.hypot(ax + factor * dx, ay + factor * dy))
    return shortest


def _normalized_words(value: str) -> set[str]:
    return set(re.findall(r"[a-zäöüß]{3,}", value.casefold()))


def alert_applies_to_station(alert: FloodAlert, station: dict[str, Any]) -> bool:
    """Return whether an alert geometry safely applies to a HyDAS station."""
    coordinates = station.get("coordinates")
    if not isinstance(coordinates, dict):
        return False
    lat = coordinates.get("lat")
    lon = coordinates.get("lon")
    if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
        return False

    if alert.geometry_type == "Polygon":
        return _point_in_polygon(float(lon), float(lat), alert.coordinates)
    if alert.geometry_type == "MultiPolygon":
        return any(
            _point_in_polygon(float(lon), float(lat), polygon)
            for polygon in alert.coordinates
            if isinstance(polygon, list)
        )

    water = station.get("waterBodyName")
    if not isinstance(water, str):
        return False
    alert_text = " ".join(
        value for value in (alert.area_description, alert.headline, alert.description) if value
    )
    if not (_normalized_words(water) & _normalized_words(alert_text)):
        return False
    return (
        _distance_to_line_km(float(lon), float(lat), alert.coordinates)
        <= RIVER_ALERT_MAX_DISTANCE_KM
    )


class LHPClient:
    """Retrieve and ETag-cache official active LHP alerts."""

    def __init__(self, session: ClientSession) -> None:
        self._session = session
        self._etag: str | None = None
        self._cache_key: tuple[str, ...] | None = None
        self._cached_data: FloodAlertData | None = None

    async def async_get_alerts(self, states: set[str]) -> FloodAlertData:
        """Return active official flood alerts with CAP details."""
        state_codes = tuple(sorted(state.removeprefix("DE-") for state in states))
        headers = {"Accept": "application/json", "Accept-Language": "de"}
        if self._etag and self._cache_key == state_codes:
            headers["If-None-Match"] = self._etag
        params = {"cap": "true"}
        if state_codes:
            params["states"] = ",".join(state_codes)
        try:
            async with self._session.get(
                LHP_API_URL,
                params=params,
                headers=headers,
                timeout=ClientTimeout(total=30),
            ) as response:
                if response.status == 304 and self._cached_data is not None:
                    return self._cached_data
                response.raise_for_status()
                payload = await response.json(content_type=None)
                etag = response.headers.get("ETag")
        except (ClientError, asyncio.TimeoutError) as err:
            raise LHPError(str(err)) from err
        except (ValueError, TypeError) as err:
            raise LHPError("The LHP API did not return valid JSON") from err

        if not isinstance(payload, dict) or payload.get("status") != "success":
            raise LHPError("The LHP response is not successful")
        raw_alerts = payload.get("data", payload.get("features"))
        updated = payload.get("updated", payload.get("update"))
        if not isinstance(raw_alerts, list) or not isinstance(updated, str):
            raise LHPError("The LHP response is missing alerts or update time")
        data = FloodAlertData(
            updated=updated,
            source=(
                payload.get("source") if isinstance(payload.get("source"), str) else LHP_SOURCE_URL
            ),
            licence=(payload.get("licence") if isinstance(payload.get("licence"), str) else None),
            alerts=tuple(
                alert for item in raw_alerts if (alert := _normalize_alert(item)) is not None
            ),
        )
        self._etag = etag
        self._cache_key = state_codes
        self._cached_data = data
        return data
