"""The HyDAS API integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import HyDASClient
from .const import (
    CONF_BASE_URL,
    CONF_SCAN_INTERVAL,
    CONF_STATION_IDS,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
)
from .coordinator import HyDASCoordinator

PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up HyDAS from a config entry."""
    config = {**entry.data, **entry.options}
    client = HyDASClient(async_get_clientsession(hass), config[CONF_BASE_URL])
    coordinator = HyDASCoordinator(
        hass,
        client,
        config.get(CONF_STATION_IDS, []),
        config.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
    )
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a HyDAS config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)
