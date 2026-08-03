"""Shared presentation helpers for HyDAS data."""

from __future__ import annotations

from typing import Any


def station_display_name(station: dict[str, Any]) -> str:
    """Return a station name suited to its standardized station type."""
    name = str(station.get("name") or station.get("id") or "HyDAS station")
    station_type = station.get("type")

    water_body = station.get("waterBodyName")
    if station_type == "surfaceWater" or (station_type is None and water_body):
        return f"{water_body} - {name}" if water_body else name

    if station_type == "groundwater":
        aquifer = station.get("aquifer")
        aquifer_name = aquifer.get("name") if isinstance(aquifer, dict) else None
        return f"{aquifer_name} - {name}" if aquifer_name else name

    # MeteorologicalStation defines no additional naming field. Unknown future
    # station types also safely fall back to the standardized BaseStation name.
    return name


def parameter_icon(parameter: dict[str, Any]) -> str | None:
    """Return an MDI icon for a standardized observed property."""
    observed_property = parameter.get("observedProperty")
    parameter_id = str(parameter.get("id", "")).casefold()

    icons = {
        "water-level-rel": "mdi:waves",
        "water-level-abs": "mdi:waves",
        "groundwater-level-rel": "mdi:water-well",
        "groundwater-level-abs": "mdi:water-well",
        "discharge": "mdi:waves-arrow-right",
        "flow-rate": "mdi:waves-arrow-right",
        "spring-discharge": "mdi:waves-arrow-right",
        "water-temperature": "mdi:thermometer-water",
        "groundwater-temperature": "mdi:thermometer-water",
        "air-temperature": "mdi:thermometer",
        "wind-speed": "mdi:weather-windy",
    }
    if observed_property in icons:
        return icons[observed_property]

    # PEGELONLINE currently uses the short parameter IDs W and Q and does not
    # expose observedProperty in its HyDAS parameter response.
    if parameter_id == "w":
        return "mdi:waves"
    if parameter_id == "q":
        return "mdi:waves-arrow-right"
    return None
