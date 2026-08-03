"""Tests for the HyDAS config flow."""

from unittest.mock import AsyncMock, patch

from homeassistant import config_entries, data_entry_flow

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
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], user_input={CONF_STATION_IDS: ["unknown"]}
        )

    assert result["type"] is data_entry_flow.FlowResultType.FORM
    assert result["errors"] == {CONF_STATION_IDS: "invalid_station"}
