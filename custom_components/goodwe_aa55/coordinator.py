# This file should contain code which fetches data from the inverter (extend DataUpdateCoordinator)
"""Update coordinator for Goodwe."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import SCAN_INTERVAL
from .exceptions import InverterError, RequestFailedException
from .inverter import Inverter, InverterStatus

_LOGGER = logging.getLogger(__name__)


class GoodweAA55UpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Gather data for the energy device."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        inverter: Inverter,
    ) -> None:
        """Initialize update coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=entry.title,
            update_interval=SCAN_INTERVAL,
        )
        self.inverter: Inverter = inverter
        self._last_data: dict[str, Any] = {}

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from the inverter."""
        try:
            if self.data:
                self._last_data = self.data
            return await self.inverter.get_running_info()
        except RequestFailedException:
            # UDP communication with inverter is by definition unreliable.
            # It is rather normal in many environments to fail to receive
            # proper response in usual time, so we intentionally ignore isolated
            # failures and report problem with availability only after
            # consecutive streak of 3 of failed requests.
            if self.inverter.consecutive_com_failures < 3:
                _LOGGER.debug(
                    "No response received (streak of %d)",
                    self.inverter.consecutive_com_failures,
                )
                # return last known data
                return self._last_data
            # Inverter does not respond anymore (e.g. it went to sleep mode)
            _LOGGER.debug(
                "Inverter not responding (streak of %d)",
                self.inverter.consecutive_com_failures,
            )

            return {
                "work_mode": InverterStatus(-1).name,
                "pac": 0,
                "e_today": self._last_data.get("e_today"),
                "e_total": self._last_data.get("e_total"),
                "l1_voltage": None,
                "l1_frequency": None,
                "temperature": None,
                "running_hours": self._last_data.get("running_hours"),
            }

        except InverterError as ex:
            raise UpdateFailed(ex) from ex

    def sensor_value(self, sensor: str) -> Any:
        """Answer current (or last known) value of the sensor."""
        val = self.data.get(sensor)
        return val if val is not None else self._last_data.get(sensor)

    def total_sensor_value(self, sensor: str) -> Any:
        """Answer current value of the 'total' (never 0) sensor."""
        val = self.data.get(sensor)
        return val if val else self._last_data.get(sensor)

    def reset_sensor(self, sensor: str) -> None:
        """Reset sensor value to 0.

        Intended for "daily" cumulative sensors (e.g. PV energy produced today),
        which should be explicitly reset to 0 at midnight if inverter is suspended.
        """
        self._last_data[sensor] = 0
        self.data[sensor] = 0
