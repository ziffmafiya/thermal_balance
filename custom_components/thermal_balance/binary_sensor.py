"""Binary sensor platform for Thermal Balance custom component."""
from dataclasses import dataclass
import logging
from typing import Any, Optional

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    BINARY_SENSOR_RECOMMEND_CLOSE_CURTAINS,
    BINARY_SENSOR_RECOMMEND_OPEN_WINDOW,
    DOMAIN,
)
from .coordinator import ThermalBalanceCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass
class ThermalBalanceBinarySensorDescription(BinarySensorEntityDescription):
    """Class describing Thermal Balance binary sensor entities."""


BINARY_SENSOR_TYPES: tuple[ThermalBalanceBinarySensorDescription, ...] = (
    ThermalBalanceBinarySensorDescription(
        key=BINARY_SENSOR_RECOMMEND_OPEN_WINDOW,
        name="Open Window Recommended",
        icon="mdi:window-open-variant",
    ),
    ThermalBalanceBinarySensorDescription(
        key=BINARY_SENSOR_RECOMMEND_CLOSE_CURTAINS,
        name="Close Curtains Recommended",
        icon="mdi:curtains-closed",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Thermal Balance binary sensors from a config entry."""
    coordinator: ThermalBalanceCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        ThermalBalanceBinarySensor(coordinator, description, entry)
        for description in BINARY_SENSOR_TYPES
    ]

    async_add_entities(entities)


class ThermalBalanceBinarySensor(CoordinatorEntity[ThermalBalanceCoordinator], BinarySensorEntity):
    """Representation of a Thermal Balance binary sensor."""

    entity_description: ThermalBalanceBinarySensorDescription

    def __init__(
        self,
        coordinator: ThermalBalanceCoordinator,
        description: ThermalBalanceBinarySensorDescription,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"Thermal Balance ({coordinator.room_area:.0f}m²)",
            manufacturer="Thermal Balance Physics Engine",
            model="Open-System Thermodynamic Calculator",
            sw_version="1.6.0",
        )

    @property
    def is_on(self) -> bool:
        """Return true if the binary sensor is on."""
        key = self.entity_description.key
        if key == BINARY_SENSOR_RECOMMEND_OPEN_WINDOW:
            return bool(self.coordinator.data.get("recommend_open_window", False))
        if key == BINARY_SENSOR_RECOMMEND_CLOSE_CURTAINS:
            return bool(self.coordinator.data.get("recommend_close_curtains", False))
        return False

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes for advice and financial impact."""
        key = self.entity_description.key
        attrs = {}
        if key == BINARY_SENSOR_RECOMMEND_OPEN_WINDOW:
            t_in = self.coordinator.t_in_val
            t_out = self.coordinator.t_out_val
            is_rec = self.is_on
            if is_rec:
                attrs["advice"] = f"Outdoor air ({t_out:.1f}°C) is cooler than indoor ({t_in:.1f}°C). Open window for free cooling!"
            else:
                attrs["advice"] = "Outdoor temperature is higher than indoor. Keep window closed."
            attrs["temp_difference_c"] = round(t_in - t_out, 1)

        elif key == BINARY_SENSOR_RECOMMEND_CLOSE_CURTAINS:
            solar = self.coordinator.solar_val
            rate = self.coordinator.electricity_rate
            symbol = self.coordinator.currency_symbol
            is_rec = self.is_on
            
            # Potential heat reduction in Watts
            pot_w = self.coordinator.window_area * solar * 0.50
            # Estimated electricity saved in UAH/day (assuming COP ~ 3.2)
            saved_kwh_day = (pot_w / 3.2 / 1000.0) * 12.0
            saved_cost_day = saved_kwh_day * rate

            if is_rec:
                attrs["advice"] = f"High solar radiation ({solar:.0f} W/m²). Close curtains to reduce solar heat gain by 70%!"
            else:
                attrs["advice"] = "Solar radiation is low or curtains are already closed."
            attrs["solar_radiation_w_m2"] = round(solar, 1)
            attrs["potential_heat_reduction_w"] = round(pot_w, 0)
            attrs["potential_daily_savings"] = f"{saved_cost_day:.2f} {symbol}/day"

        return attrs
