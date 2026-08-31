"""Unit tests for Thermal Balance diagnostics dump."""
import asyncio
import os
import sys
import unittest

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from mock_ha import MockConfigEntry, MockHomeAssistant, setup_mock_homeassistant

setup_mock_homeassistant()

from custom_components.thermal_balance.coordinator import ThermalBalanceCoordinator
from custom_components.thermal_balance.diagnostics import async_get_config_entry_diagnostics
from custom_components.thermal_balance.const import (
    CONF_AC_MAX_COOLING,
    CONF_ELECTRICITY_RATE,
    CONF_ROOM_AREA,
    CONF_SENSOR_AC_POWER,
    CONF_SENSOR_T_IN,
    CONF_SENSOR_T_OUT,
)


class TestThermalBalanceDiagnostics(unittest.TestCase):
    """Test suite for diagnostics dump."""

    def test_diagnostics_dump(self) -> None:
        """Test full diagnostic output structure and integrity."""
        hass = MockHomeAssistant()
        entry_data = {
            CONF_ROOM_AREA: 22.5,
            CONF_AC_MAX_COOLING: 3350.0,
            CONF_ELECTRICITY_RATE: 4.32,
            CONF_SENSOR_T_IN: "sensor.test_in",
            CONF_SENSOR_T_OUT: "sensor.test_out",
            CONF_SENSOR_AC_POWER: "sensor.test_pwr",
        }
        entry = MockConfigEntry(data=entry_data)
        coordinator = ThermalBalanceCoordinator(hass, entry)
        coordinator.total_heat_absorbed = 15.5
        coordinator.daily_heat_absorbed = 3.2
        entry.runtime_data = coordinator

        diag = asyncio.run(async_get_config_entry_diagnostics(hass, entry))

        # Check geometry section
        self.assertIn("geometry", diag)
        self.assertEqual(diag["geometry"]["room_area"], 22.5)
        self.assertGreater(diag["geometry"]["volume_m3"], 0)

        # Check coordinator state
        self.assertIn("coordinator_state", diag)
        self.assertEqual(diag["coordinator_state"]["electricity_rate"], 4.32)

        # Check accumulators
        self.assertIn("accumulators", diag)
        self.assertEqual(diag["accumulators"]["total_heat_absorbed_kwh"], 15.5)
        self.assertEqual(diag["accumulators"]["daily_heat_absorbed_kwh"], 3.2)


if __name__ == "__main__":
    unittest.main()
