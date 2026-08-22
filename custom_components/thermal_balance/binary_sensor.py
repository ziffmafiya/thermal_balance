"""Binary sensor platform for Thermal Balance custom component."""
from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
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


@dataclass(frozen=True)
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
    coordinator: ThermalBalanceCoordinator = entry.runtime_data

    async_add_entities(
        ThermalBalanceBinarySensor(coordinator, description, entry)
        for description in BINARY_SENSOR_TYPES
    )


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
    def is_on(self) -> bool:
        """Return true if the binary sensor is on."""
        return bool(self.coordinator.data.get(self.entity_description.key, False))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes for advice and financial impact."""
        key = self.entity_description.key
        attrs: dict[str, Any] = {}
        if key == BINARY_SENSOR_RECOMMEND_OPEN_WINDOW:
            t_in = self.coordinator.t_in_val
            t_out = self.coordinator.t_out_val
            if self.is_on:
                attrs["advice"] = f"Outdoor air ({t_out:.1f}°C) is cooler than indoor ({t_in:.1f}°C). Open window for free cooling!"
            else:
                attrs["advice"] = "Outdoor temperature is higher than indoor. Keep window closed."
            attrs["temp_difference_c"] = round(t_in - t_out, 1)

        elif key == BINARY_SENSOR_RECOMMEND_CLOSE_CURTAINS:
            solar = self.coordinator.solar_val
            rate = self.coordinator.electricity_rate
            symbol = self.coordinator.currency_symbol

            factors = self.coordinator.data
            saved_fraction = 0.52
            curtain_factors = self.coordinator.extra_attributes.get(key, {})
            
            pot_w = self.coordinator.geometry.window_area * solar * 0.52
            saved_kwh_day = (pot_w / 3.2 / 1000.0) * 12.0
            saved_cost_day = saved_kwh_day * rate

            if self.is_on:
                attrs["advice"] = f"High solar radiation ({solar:.0f} W/m²). Close curtains to reduce solar heat gain!"
            else:
                attrs["advice"] = "Solar radiation is low or curtains are already closed."
            attrs["solar_radiation_w_m2"] = round(solar, 1)
            attrs["potential_heat_reduction_w"] = round(pot_w, 0)
            attrs["potential_daily_savings"] = f"{saved_cost_day:.2f} {symbol}/day"

        return attrs
