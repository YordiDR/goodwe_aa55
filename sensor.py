# This file actually gets the data (device integration extending sensor entity)
"""Support for GoodWe inverter over AA55 RS485 converted to UDP."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_point_in_time
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity
import homeassistant.util.dt as dt_util

from .const import DOMAIN, KEY_COORDINATOR, KEY_DEVICE_INFO, KEY_INVERTER
from .coordinator import GoodweAA55UpdateCoordinator
from .inverter import Inverter

_LOGGER = logging.getLogger(__name__)

# Sensors that are reset to 0 at midnight.
# The inverter is only powered by the solar panels and not mains power, so it goes dead when the sun goes down.
# The "_day" sensors are reset to 0 when the inverter wakes up in the morning when the sun comes up and power to the inverter is restored.
# This makes sure daily values are reset at midnight instead of at sunrise.
# When the inverter has a battery connected, HomeAssistant will not reset the values but let the inverter reset them by looking at the unavailable state of the inverter.
DAILY_RESET = ["e_today"]

_ICONS: dict[str, str] = {
    "work_mode": "mdi:solar-power",
    "pac": "mdi:solar-power",
    "e_today": "mdi:solar-power",
    "e_total": "mdi:solar-power",
    "running_hours": "mdi:clock",
    "temperature": "mdi:temperature-celsius",
    "l1_voltage": "mdi:power-plug-outline",
    "l1_frequency": "mdi:power-plug-outline",
}


@dataclass(frozen=True)
class GoodweAA55SensorEntityDescription(SensorEntityDescription):
    """Class describing Goodwe sensor entities."""

    value: Callable[[GoodweAA55UpdateCoordinator, str], Any] = (
        lambda coordinator, sensor: coordinator.sensor_value(sensor)
    )
    available: Callable[[GoodweAA55UpdateCoordinator], bool] = (
        lambda coordinator: coordinator.last_update_success
    )


_NAMES: dict[str, str] = {
    "work_mode": "Work mode",
    "pac": "Feeding power",
    "e_today": "Energy today",
    "e_total": "Energy total",
    "running_hours": "Running hours",
    "temperature": "Temperature",
    "l1_voltage": "Phase 1 voltage",
    "l1_frequency": "Phase 1 frequency",
}

_DESCRIPTIONS: dict[str, GoodweAA55SensorEntityDescription] = {
    "work_mode": GoodweAA55SensorEntityDescription(key="text"),
    "pac": GoodweAA55SensorEntityDescription(
        key="W",
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfPower.WATT,
    ),
    "e_today": GoodweAA55SensorEntityDescription(
        key="kWh",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        value=lambda coordinator, sensor: coordinator.total_sensor_value(sensor),
        available=lambda coordinator: coordinator.data is not None,
    ),
    "e_total": GoodweAA55SensorEntityDescription(
        key="kWh",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        value=lambda coordinator, sensor: coordinator.total_sensor_value(sensor),
        available=lambda coordinator: coordinator.data is not None,
    ),
    "running_hours": GoodweAA55SensorEntityDescription(
        key="h",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTime.HOURS,
        suggested_display_precision=0,
    ),
    "temperature": GoodweAA55SensorEntityDescription(
        key="C",
        device_class=SensorDeviceClass.TEMPERATURE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfTemperature.CELSIUS,
    ),
    "l1_voltage": GoodweAA55SensorEntityDescription(
        key="V",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT,
    ),
    "l1_frequency": GoodweAA55SensorEntityDescription(
        key="Hz",
        device_class=SensorDeviceClass.FREQUENCY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
    ),
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the GoodWe inverter from a config entry."""
    inverter = hass.data[DOMAIN][config_entry.entry_id][KEY_INVERTER]
    coordinator = hass.data[DOMAIN][config_entry.entry_id][KEY_COORDINATOR]
    device_info = hass.data[DOMAIN][config_entry.entry_id][KEY_DEVICE_INFO]

    # Individual inverter sensors entities
    entities: list[InverterSensor] = [
        InverterSensor(coordinator, device_info, inverter, "work_mode"),
        InverterSensor(coordinator, device_info, inverter, "pac"),
        InverterSensor(coordinator, device_info, inverter, "e_today"),
        InverterSensor(coordinator, device_info, inverter, "e_total"),
        InverterSensor(coordinator, device_info, inverter, "running_hours"),
        InverterSensor(coordinator, device_info, inverter, "temperature"),
        InverterSensor(coordinator, device_info, inverter, "l1_voltage"),
        InverterSensor(coordinator, device_info, inverter, "l1_frequency"),
    ]
    async_add_entities(entities)


class InverterSensor(CoordinatorEntity[GoodweAA55UpdateCoordinator], SensorEntity):
    """Entity representing individual inverter sensor."""

    entity_description: GoodweAA55SensorEntityDescription

    def __init__(
        self,
        coordinator: GoodweAA55UpdateCoordinator,
        device_info: DeviceInfo,
        inverter: Inverter,
        sensorName: str,
    ) -> None:
        """Initialize an inverter sensor."""
        super().__init__(coordinator)
        self._attr_name = _NAMES[sensorName]
        self._attr_unique_id = f"{DOMAIN}-{sensorName}-{inverter.serial_number}"
        self._attr_device_info = device_info
        self.entity_description = _DESCRIPTIONS[sensorName]
        self._attr_icon = _ICONS[sensorName]
        self._sensorName = sensorName
        self._stop_reset: Callable[[], None] | None = None

    @property
    def native_value(self) -> StateType | date | datetime | Decimal:
        """Return the value reported by the sensor."""
        return self.entity_description.value(self.coordinator, self._sensorName)

    @property
    def available(self) -> bool:
        """Return if entity is available.

        We delegate the behavior to entity description lambda, since
        some sensors (like energy produced today) should report themselves
        as available even when the (non-battery) pv inverter is off-line during night
        and most of the sensors are actually unavailable.
        """
        return self.entity_description.available(self.coordinator)

    @callback
    def async_reset(self, now):
        """Reset the value back to 0 at midnight.

        Some sensors values like daily produced energy are kept available,
        even when the inverter is in sleep mode and no longer responds to request.
        In contrast to "total" sensors, these "daily" sensors need to be reset to 0 on midnight.
        """
        if (
            not self.coordinator.last_update_success
            or self.coordinator.inverter.work_mode == -1
        ):
            self.coordinator.reset_sensor(self._sensorName)
            self.async_write_ha_state()
            _LOGGER.debug("Goodwe reset %s to 0", self._sensorName)
        next_midnight = dt_util.start_of_local_day(
            dt_util.now() + timedelta(days=1, minutes=1)
        )
        self._stop_reset = async_track_point_in_time(
            self.hass, self.async_reset, next_midnight
        )

    async def async_added_to_hass(self) -> None:
        """Schedule reset task at midnight."""
        if self._sensorName in DAILY_RESET:
            next_midnight = dt_util.start_of_local_day(
                dt_util.now() + timedelta(days=1)
            )
            self._stop_reset = async_track_point_in_time(
                self.hass, self.async_reset, next_midnight
            )
        await super().async_added_to_hass()

    async def async_will_remove_from_hass(self) -> None:
        """Remove reset task at midnight."""
        if self._sensorName in DAILY_RESET and self._stop_reset is not None:
            self._stop_reset()
        await super().async_will_remove_from_hass()
