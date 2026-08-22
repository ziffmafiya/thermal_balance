"""Sensor platform for Thermal Balance custom component."""
from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy, UnitOfPower, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    SENSOR_AC_CARNOT_COP,
    SENSOR_AC_CONDENSATION_RATE,
    SENSOR_AC_ENERGY_COST,
    SENSOR_AC_HEAT_OUTPUT,
    SENSOR_AC_THERMAL_ENERGY_TOTAL,
    SENSOR_DAILY_THERMAL_BALANCE,
    SENSOR_EMPIRICAL_K_FACTOR,
    SENSOR_INSTANT_HEAT_GAIN,
    SENSOR_INSTANT_NET_BALANCE,
    SENSOR_NET_THERMAL_BALANCE,
    SENSOR_SHADING_DAILY_SAVINGS,
    SENSOR_TIME_TO_1DEG,
    SENSOR_TOTAL_HEAT_ABSORBED,
)
from .coordinator import ThermalBalanceCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class ThermalBalanceSensorEntityDescription(SensorEntityDescription):
    """Class describing Thermal Balance sensor entities."""

    is_restorable: bool = False


SENSOR_TYPES: tuple[ThermalBalanceSensorEntityDescription, ...] = (
    ThermalBalanceSensorEntityDescription(
        key=SENSOR_INSTANT_HEAT_GAIN,
        name="Heat Gain",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    ThermalBalanceSensorEntityDescription(
        key=SENSOR_AC_HEAT_OUTPUT,
        name="AC Cooling",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    ThermalBalanceSensorEntityDescription(
        key=SENSOR_INSTANT_NET_BALANCE,
        name="Net Balance",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
    ),
    ThermalBalanceSensorEntityDescription(
        key=SENSOR_AC_CARNOT_COP,
        name="AC COP",
        native_unit_of_measurement=None,
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
    ),
    ThermalBalanceSensorEntityDescription(
        key=SENSOR_TIME_TO_1DEG,
        name="Time to 1°C",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=0,
    ),
    ThermalBalanceSensorEntityDescription(
        key=SENSOR_DAILY_THERMAL_BALANCE,
        name="Daily Balance",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        is_restorable=True,
        suggested_display_precision=3,
    ),
    ThermalBalanceSensorEntityDescription(
        key=SENSOR_NET_THERMAL_BALANCE,
        name="Total Balance",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        is_restorable=True,
        suggested_display_precision=3,
    ),
    ThermalBalanceSensorEntityDescription(
        key=SENSOR_TOTAL_HEAT_ABSORBED,
        name="Heat Absorbed",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        is_restorable=True,
        suggested_display_precision=3,
    ),
    ThermalBalanceSensorEntityDescription(
        key=SENSOR_AC_THERMAL_ENERGY_TOTAL,
        name="AC Energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        is_restorable=True,
        suggested_display_precision=3,
    ),
    ThermalBalanceSensorEntityDescription(
        key=SENSOR_AC_CONDENSATION_RATE,
        name="Condensation Rate",
        native_unit_of_measurement="L/h",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=2,
    ),
    ThermalBalanceSensorEntityDescription(
        key=SENSOR_EMPIRICAL_K_FACTOR,
        name="Empirical K-Factor",
        native_unit_of_measurement="W/K",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
        is_restorable=True,
        suggested_display_precision=2,
    ),
    ThermalBalanceSensorEntityDescription(
        key=SENSOR_AC_ENERGY_COST,
        name="AC Energy Cost",
        native_unit_of_measurement=None,
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        is_restorable=True,
        suggested_display_precision=2,
    ),
    ThermalBalanceSensorEntityDescription(
        key=SENSOR_SHADING_DAILY_SAVINGS,
        name="Shading Daily Savings",
        native_unit_of_measurement=None,
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.TOTAL,
        is_restorable=True,
        suggested_display_precision=2,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Thermal Balance sensors from a config entry."""
    coordinator: ThermalBalanceCoordinator = entry.runtime_data

    async_add_entities(
        ThermalBalanceSensor(coordinator, entry, description)
        for description in SENSOR_TYPES
    )


class ThermalBalanceSensor(CoordinatorEntity[ThermalBalanceCoordinator], RestoreEntity, SensorEntity):
    """Representation of a Thermal Balance Sensor."""

    entity_description: ThermalBalanceSensorEntityDescription

    def __init__(
        self,
        coordinator: ThermalBalanceCoordinator,
        entry: ConfigEntry,
        description: ThermalBalanceSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entry = entry
        self.entity_description = description

        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_has_entity_name = True
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Thermal Balance",
            model="Thermodynamics Hub",
        )

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return dynamic unit of measurement for monetary sensors."""
        key = self.entity_description.key
        if key in (SENSOR_AC_ENERGY_COST, SENSOR_SHADING_DAILY_SAVINGS):
            return self.coordinator.currency_symbol
        return self.entity_description.native_unit_of_measurement

    @property
    def native_value(self) -> float | None:
        """Return native value of sensor."""
        return self.coordinator.data.get(self.entity_description.key)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra state attributes for entity."""
        return self.coordinator.extra_attributes.get(self.entity_description.key)

    async def async_added_to_hass(self) -> None:
        """Handle entity addition to Home Assistant."""
        await super().async_added_to_hass()

        if self.entity_description.is_restorable:
            last_state = await self.async_get_last_state()
            if last_state is not None and last_state.state not in ("unknown", "unavailable"):
                try:
                    restored_val = float(last_state.state)
                    if self.entity_description.key == SENSOR_TOTAL_HEAT_ABSORBED:
                        self.coordinator.total_heat_absorbed = restored_val
                    elif self.entity_description.key == SENSOR_AC_THERMAL_ENERGY_TOTAL:
                        self.coordinator.ac_thermal_energy_total = restored_val
                    elif self.entity_description.key == SENSOR_EMPIRICAL_K_FACTOR:
                        self.coordinator.empirical_k_val = restored_val
                    elif self.entity_description.key == SENSOR_DAILY_THERMAL_BALANCE and last_state.attributes:
                        if "daily_heat_absorbed" in last_state.attributes:
                            self.coordinator.daily_heat_absorbed = float(last_state.attributes["daily_heat_absorbed"])
                        if "daily_ac_thermal_energy" in last_state.attributes:
                            self.coordinator.daily_ac_thermal_energy = float(last_state.attributes["daily_ac_thermal_energy"])
                        if "daily_ac_elec_kwh" in last_state.attributes:
                            self.coordinator.daily_ac_elec_kwh = float(last_state.attributes["daily_ac_elec_kwh"])
                        if "daily_shading_heat_saved_kwh" in last_state.attributes:
                            self.coordinator.daily_shading_heat_saved_kwh = float(last_state.attributes["daily_shading_heat_saved_kwh"])
                    _LOGGER.debug("Restored %s = %f", self.entity_description.key, restored_val)
                except (ValueError, TypeError):
                    pass
