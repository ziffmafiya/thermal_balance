"""Diagnostics support for Thermal Balance integration."""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .coordinator import ThermalBalanceCoordinator

TO_REDACT: list[str] = []


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    coordinator: ThermalBalanceCoordinator = entry.runtime_data

    return {
        "entry_data": async_redact_data(entry.data, TO_REDACT),
        "entry_options": async_redact_data(entry.options, TO_REDACT),
        "geometry": {
            "room_area": coordinator.geometry.room_area,
            "ceiling_height": coordinator.geometry.ceiling_height,
            "window_area": coordinator.geometry.window_area,
            "external_walls_fraction": coordinator.geometry.external_walls_fraction,
            "u_wall": coordinator.geometry.u_wall,
            "u_window": coordinator.geometry.u_window,
            "volume_m3": coordinator.geometry.volume,
            "c_total_wh_k": coordinator.geometry.c_total,
            "hlc_theoretical_w_k": coordinator.geometry.hlc_theoretical,
        },
        "coordinator_state": {
            "hlc_closed": coordinator.hlc_closed,
            "empirical_k_val": coordinator.empirical_k_val,
            "k_samples_count": coordinator._k_samples_count,
            "use_empirical_hlc": coordinator.use_empirical_hlc,
            "curtain_type": coordinator.curtain_type,
            "electricity_rate": coordinator.electricity_rate,
            "currency_symbol": coordinator.currency_symbol,
            "window_is_open": coordinator.window_is_open,
            "curtains_closed": coordinator.curtains_closed,
        },
        "accumulators": {
            "total_heat_absorbed_kwh": coordinator.total_heat_absorbed,
            "ac_thermal_energy_total_kwh": coordinator.ac_thermal_energy_total,
            "daily_heat_absorbed_kwh": coordinator.daily_heat_absorbed,
            "daily_ac_thermal_energy_kwh": coordinator.daily_ac_thermal_energy,
            "daily_ac_elec_kwh": coordinator.daily_ac_elec_kwh,
            "daily_shading_heat_saved_kwh": coordinator.daily_shading_heat_saved_kwh,
        },
        "data": coordinator.data,
        "extra_attributes": coordinator.extra_attributes,
    }
