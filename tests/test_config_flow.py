"""Tests for the HyDAS config flow."""

from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries, data_entry_flow

from custom_components.hydas.config_flow import _stations_schema
from custom_components.hydas.const import (
    CONF_BASE_URL,
    CONF_SCAN_INTERVAL,
    CONF_STATION_IDS,
    DOMAIN,
)

CONNECTION = {
    CONF_BASE_URL: "https://example.test/api/",
    CONF_SCAN_INTERVAL: 300,
}
STATIONS = [
    {"id": "b", "name": "Beta", "waterBodyName": "Rhine"},
    {"id": "a", "name": "Alpha", "waterBodyName": "Elbe"},
]


def test_station_schema_has_no_default_selection():
    schema = _stations_schema(STATIONS)

    assert schema({})[CONF_STATION_IDS] == []


def test_station_schema_preserves_existing_selection():
    schema = _stations_schema(STATIONS, ["a"])

    assert schema({})[CONF_STATION_IDS] == ["a"]


async def test_config_flow_creates_entry(hass):
    with patch(
        "custom_components.hydas.config_flow.HyDASClient.async_get_stations",
        AsyncMock(return_value=STATIONS),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        assert result["type"] is data_entry_flow.FlowResultType.FORM

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input=CONNECTION
        )
        assert result["step_id"] == "stations"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={CONF_STATION_IDS: ["a"]}
        )

    assert result["type"] is data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result["data"] == {
        CONF_BASE_URL: "https://example.test/api",
        CONF_SCAN_INTERVAL: 300,
        CONF_STATION_IDS: ["a"],
    }


async def test_config_flow_rejects_bad_url(hass):
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": config_entries.SOURCE_USER},
        data=None,
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={CONF_BASE_URL: "example.test", CONF_SCAN_INTERVAL: 300},
    )

    assert result["errors"] == {"base": "invalid_response"}


async def test_config_flow_requires_known_station(hass):
    with patch(
        "custom_components.hydas.config_flow.HyDASClient.async_get_stations",
        AsyncMock(return_value=STATIONS),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": config_entries.SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input=CONNECTION
        )
        with pytest.raises(data_entry_flow.InvalidData) as exc_info:
            await hass.config_entries.flow.async_configure(
                result["flow_id"], user_input={CONF_STATION_IDS: ["unknown"]}
            )

    assert exc_info.value.path == [CONF_STATION_IDS]
