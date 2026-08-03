"""Constants for the HyDAS integration."""

from datetime import timedelta

DOMAIN = "hydas"
PLATFORMS = ["sensor"]

CONF_BASE_URL = "base_url"
CONF_STATION_IDS = "station_ids"
CONF_SCAN_INTERVAL = "scan_interval"

DEFAULT_BASE_URL = "https://pegelonline.wsv.de/api/v1"
DEFAULT_SCAN_INTERVAL = 300
MIN_SCAN_INTERVAL = 60

DEFAULT_UPDATE_INTERVAL = timedelta(seconds=DEFAULT_SCAN_INTERVAL)
