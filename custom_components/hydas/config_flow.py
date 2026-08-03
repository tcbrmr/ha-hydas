"""Config flow for HyDAS API."""

from __future__ import annotations

import hashlib
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import SelectSelector, SelectSelectorConfig

from .api import HyDASClient, HyDASConnectionError, HyDASResponseError
from .const import (
    CONF_BASE_URL,
    CONF_SCAN_INTERVAL,
    CONF_STATION_IDS,
    DEFAULT_BASE_URL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MIN_SCAN_INTERVAL,
)
from .helpers import station_display_name


def _connection_schema(defaults: dict[str, Any]) -> vol.Schema:
    """Return the connection step schema."""
    return vol.Schema(
        {
            vol.Required(
                CONF_BASE_URL,
                default=defaults.get(CONF_BASE_URL, DEFAULT_BASE_URL),
            ): str,
            vol.Required(
                CONF_SCAN_INTERVAL,
                default=defaults.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            ): vol.All(vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL)),
        }
    )


def _station_label(station: dict[str, Any]) -> str:
    """Build a helpful, searchable label for a station."""
    state = station.get("state")
    number = station.get("number")
    location = " · ".join(str(value) for value in (state, number) if value)
    label = station_display_name(station)
    return f"{label} ({location})" if location else label


def _stations_schema(
    stations: list[dict[str, Any]], selected: list[str] | None = None
) -> vol.Schema:
    """Return a searchable multi-select containing all discovered stations."""
    options = [
        {"value": station["id"], "label": _station_label(station)}
        for station in sorted(
            stations,
            key=lambda item: (
                str(item.get("waterBodyName", "")).casefold(),
                str(item.get("name", "")).casefold(),
                str(item.get("number", "")).casefold(),
            ),
        )
    ]
    key = vol.Required(CONF_STATION_IDS)
    if selected:
        key = vol.Required(CONF_STATION_IDS, default=selected)
    return vol.Schema(
        {
            key: SelectSelector(
                SelectSelectorConfig(options=options, multiple=True)
            )
        }
    )


async def _load_stations(
    hass: HomeAssistant, user_input: dict[str, Any]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Normalize the connection settings and retrieve available stations."""
    data = dict(user_input)
    data[CONF_BASE_URL] = user_input[CONF_BASE_URL].strip().rstrip("/")
    if not data[CONF_BASE_URL].startswith(("http://", "https://")):
        raise ValueError
    client = HyDASClient(async_get_clientsession(hass), data[CONF_BASE_URL])
    stations = await client.async_get_stations()
    if not stations:
        raise HyDASResponseError("The API does not provide any stations")
    if any(not isinstance(station.get("id"), str) for station in stations):
        raise HyDASResponseError("A station is missing its string ID")
    return data, stations


class HyDASConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HyDAS."""

    VERSION = 1

    def __init__(self) -> None:
        self._pending_data: dict[str, Any] = {}
        self._stations: list[dict[str, Any]] = []

    async def async_step_user(self, user_input=None):
        """Collect and validate the API connection."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                self._pending_data, self._stations = await _load_stations(
                    self.hass, user_input
                )
            except HyDASConnectionError:
                errors["base"] = "cannot_connect"
            except (HyDASResponseError, ValueError):
                errors["base"] = "invalid_response"
            else:
                return await self.async_step_stations()
        return self.async_show_form(
            step_id="user",
            data_schema=_connection_schema(user_input or {}),
            errors=errors,
        )

    async def async_step_stations(self, user_input=None):
        """Let the user search and select one or more stations."""
        errors: dict[str, str] = {}
        if user_input is not None:
            selected = user_input.get(CONF_STATION_IDS, [])
            known_ids = {station["id"] for station in self._stations}
            if not selected:
                errors[CONF_STATION_IDS] = "station_required"
            elif not set(selected).issubset(known_ids):
                errors[CONF_STATION_IDS] = "invalid_station"
            else:
                data = {**self._pending_data, CONF_STATION_IDS: selected}
                fingerprint = (
                    f"{data[CONF_BASE_URL]}|{','.join(sorted(selected))}"
                )
                await self.async_set_unique_id(
                    hashlib.sha256(fingerprint.encode()).hexdigest()
                )
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=data[CONF_BASE_URL], data=data
                )
        return self.async_show_form(
            step_id="stations",
            data_schema=_stations_schema(self._stations),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return HyDASOptionsFlow()


class HyDASOptionsFlow(config_entries.OptionsFlow):
    """Allow changing URL, stations and polling interval."""

    def __init__(self) -> None:
        self._pending_data: dict[str, Any] = {}
        self._stations: list[dict[str, Any]] = []

    async def async_step_init(self, user_input=None):
        """Collect and validate updated connection settings."""
        errors: dict[str, str] = {}
        current = {**self.config_entry.data, **self.config_entry.options}
        if user_input is not None:
            try:
                self._pending_data, self._stations = await _load_stations(
                    self.hass, user_input
                )
            except HyDASConnectionError:
                errors["base"] = "cannot_connect"
            except (HyDASResponseError, ValueError):
                errors["base"] = "invalid_response"
            else:
                return await self.async_step_stations()
        return self.async_show_form(
            step_id="init",
            data_schema=_connection_schema(current),
            errors=errors,
        )

    async def async_step_stations(self, user_input=None):
        """Select stations for an existing config entry."""
        errors: dict[str, str] = {}
        current = {**self.config_entry.data, **self.config_entry.options}
        selected_default = [
            station_id
            for station_id in current.get(CONF_STATION_IDS, [])
            if any(station["id"] == station_id for station in self._stations)
        ]
        if user_input is not None:
            selected = user_input.get(CONF_STATION_IDS, [])
            known_ids = {station["id"] for station in self._stations}
            if not selected:
                errors[CONF_STATION_IDS] = "station_required"
            elif not set(selected).issubset(known_ids):
                errors[CONF_STATION_IDS] = "invalid_station"
            else:
                return self.async_create_entry(
                    data={**self._pending_data, CONF_STATION_IDS: selected}
                )
        return self.async_show_form(
            step_id="stations",
            data_schema=_stations_schema(self._stations, selected_default),
            errors=errors,
        )
