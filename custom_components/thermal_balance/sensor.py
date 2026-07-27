"""Sensor platform for Thermal Balance custom component."""
from dataclasses import dataclass
import logging
from typing import Any, Optional

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy, UnitOfPower, UnitOfTime
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    DOMAIN,
    SENSOR_AC_CARNOT_COP,
    SENSOR_AC_CONDENSATION_RATE,
    SENSOR_AC_HEAT_OUTPUT,
    SENSOR_AC_THERMAL_ENERGY_TOTAL,
    SENSOR_DAILY_THERMAL_BALANCE,
    SENSOR_INSTANT_HEAT_GAIN,
    SENSOR_INSTANT_NET_BALANCE,
    SENSOR_NET_THERMAL_BALANCE,
    SENSOR_TIME_TO_1DEG,
    SENSOR_TOTAL_HEAT_ABSORBED,
)
from .coordinator import ThermalBalanceCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass
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
    ),
    ThermalBalanceSensorEntityDescription(
        key=SENSOR_AC_HEAT_OUTPUT,
        name="AC Cooling",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ThermalBalanceSensorEntityDescription(
        key=SENSOR_INSTANT_NET_BALANCE,
        name="Net Balance",
        native_unit_of_measurement=UnitOfPower.WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ThermalBalanceSensorEntityDescription(
        key=SENSOR_AC_CARNOT_COP,
        name="AC COP",
        native_unit_of_measurement=None,
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ThermalBalanceSensorEntityDescription(
        key=SENSOR_TIME_TO_1DEG,
        name="Time to 1°C",
        native_unit_of_measurement=UnitOfTime.MINUTES,
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.MEASUREMENT,
    ),
    ThermalBalanceSensorEntityDescription(
        key=SENSOR_DAILY_THERMAL_BALANCE,
        name="Daily Balance",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        is_restorable=True,
    ),
    ThermalBalanceSensorEntityDescription(
        key=SENSOR_NET_THERMAL_BALANCE,
        name="Total Balance",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL,
        is_restorable=True,
    ),
    ThermalBalanceSensorEntityDescription(
        key=SENSOR_TOTAL_HEAT_ABSORBED,
        name="Heat Absorbed",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        is_restorable=True,
    ),
    ThermalBalanceSensorEntityDescription(
        key=SENSOR_AC_THERMAL_ENERGY_TOTAL,
        name="AC Energy",
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        is_restorable=True,
    ),
    ThermalBalanceSensorEntityDescription(
        key=SENSOR_AC_CONDENSATION_RATE,
        name="Condensation Rate",
        native_unit_of_measurement="L/h",
        device_class=None,
        state_class=SensorStateClass.MEASUREMENT,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Thermal Balance sensors from a config entry."""
    coordinator: ThermalBalanceCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        ThermalBalanceSensor(coordinator, entry, description)
        for description in SENSOR_TYPES
    ]

    async_add_entities(entities)


class ThermalBalanceSensor(RestoreEntity, SensorEntity):
    """Representation of a Thermal Balance Sensor."""

    entity_description: ThermalBalanceSensorEntityDescription

    def __init__(self, coordinator: ThermalBalanceCoordinator, entry: ConfigEntry, description: ThermalBalanceSensorEntityDescription) -> None:
        """Initialize the sensor."""
        self.coordinator = coordinator
        self.entry = entry
        self.entity_description = description

        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_has_entity_name = True
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer="Custom Integration",
            model="Thermal Thermodynamics Hub",
        )

    @property
    def native_value(self) -> Optional[float]:
        """Return native value of sensor."""
        return self.coordinator.data.get(self.entity_description.key)

    @property
    def extra_state_attributes(self) -> Optional[dict[str, Any]]:
        """Return extra state attributes for entity."""
        return self.coordinator.extra_attributes.get(self.entity_description.key)

    async def async_added_to_hass(self) -> None:
        """Handle entity addition to Home Assistant."""
        await super().async_added_to_hass()

        # Restore state if applicable
        if self.entity_description.is_restorable:
            last_state = await self.async_get_last_state()
            if last_state is not None and last_state.state not in ("unknown", "unavailable"):
                try:
                    restored_val = float(last_state.state)
                    if self.entity_description.key == SENSOR_TOTAL_HEAT_ABSORBED:
                        self.coordinator.total_heat_absorbed = restored_val
                    elif self.entity_description.key == SENSOR_AC_THERMAL_ENERGY_TOTAL:
                        self.coordinator.ac_thermal_energy_total = restored_val
                    elif self.entity_description.key == SENSOR_DAILY_THERMAL_BALANCE:
                        if last_state.attributes and "daily_heat_absorbed" in last_state.attributes:
                            self.coordinator.daily_heat_absorbed = float(last_state.attributes["daily_heat_absorbed"])
                        if last_state.attributes and "daily_ac_thermal_energy" in last_state.attributes:
                            self.coordinator.daily_ac_thermal_energy = float(last_state.attributes["daily_ac_thermal_energy"])
                    _LOGGER.debug("Restored %s = %f", self.entity_description.key, restored_val)
                except (ValueError, TypeError):
                    pass

        # Register update listener
        self.coordinator.register_listener(self.async_on_coordinator_update)

        # Force coordinator recalculation so restored accumulators reflect immediately in states
        self.coordinator.recalculate()

    async def async_will_remove_from_hass(self) -> None:
        """Handle entity removal from Home Assistant."""
        self.coordinator.remove_listener(self.async_on_coordinator_update)
        await super().async_will_remove_from_hass()

    @callback
    def async_on_coordinator_update(self) -> None:
        """Update sensor state when coordinator notifies."""
        self.async_write_ha_state()
