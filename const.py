"""Constants for the GoodWe Inverter AA55 over RS485 integration."""
from datetime import timedelta

from homeassistant.const import Platform

DEFAULT_NAME = "Goodwe inverter"
DOMAIN = "goodwe_aa55"

PLATFORMS = [Platform.SENSOR]

SCAN_INTERVAL = timedelta(seconds=10)

KEY_INVERTER = "inverter"
KEY_COORDINATOR = "coordinator"
KEY_DEVICE_INFO = "device_info"
