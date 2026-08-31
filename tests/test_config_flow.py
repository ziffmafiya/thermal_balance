"""Unit tests for Thermal Balance Config Flow, Options Flow, and Reconfigure Flow."""
import asyncio
import os
import sys
import unittest

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from mock_ha import MockConfigEntry, MockHomeAssistant, setup_mock_homeassistant

setup_mock_homeassistant()

from custom_components.thermal_balance.config_flow import ThermalBalanceConfigFlow, ThermalBalanceOptionsFlow
from custom_components.thermal_balance.const import (
    CONF_AC_AIRFLOW,
    CONF_AC_MAX_COOLING,
    CONF_CEILING_HEIGHT,
    CONF_CURTAIN_TYPE,
    CONF_ELECTRICITY_RATE,
    CONF_EXTERNAL_WALLS_FRACTION,
    CONF_HVAC_MODE,
    CONF_ROOM_AREA,
    CONF_SENSOR_AC_POWER,
    CONF_SENSOR_T_IN,
    CONF_SENSOR_T_OUT,
    CONF_U_WALL,
    CONF_U_WINDOW,
    CONF_WINDOW_AREA,
    CONF_WINDOW_AZIMUTH,
    HVAC_MODE_COOLING,
)


class TestThermalBalanceConfigFlow(unittest.TestCase):
    """Test suite for Config Flow, Options Flow, and Reconfiguration."""

    def test_config_flow_3_step_wizard(self) -> None:
        """Test full 3-step initial configuration wizard flow."""
        flow = ThermalBalanceConfigFlow()

        # Step 1: Geometry
        step1_form = asyncio.run(flow.async_step_user(user_input=None))
        self.assertEqual(step1_form["type"], "form")
        self.assertEqual(step1_form["step_id"], "user")

        step1_data = {
            CONF_ROOM_AREA: 25.0,
            CONF_CEILING_HEIGHT: 2.8,
            CONF_WINDOW_AREA: 4.0,
            CONF_EXTERNAL_WALLS_FRACTION: "0.50",
            CONF_WINDOW_AZIMUTH: 180.0,
            CONF_U_WALL: 0.28,
            CONF_U_WINDOW: 1.1,
        }
        step2_form = asyncio.run(flow.async_step_user(user_input=step1_data))
        self.assertEqual(step2_form["type"], "form")
        self.assertEqual(step2_form["step_id"], "equipment")

        # Step 2: Equipment
        step2_data = {
            CONF_AC_MAX_COOLING: 3500.0,
            CONF_AC_AIRFLOW: 400.0,
            CONF_HVAC_MODE: HVAC_MODE_COOLING,
            CONF_CURTAIN_TYPE: "blackout",
            CONF_ELECTRICITY_RATE: 4.32,
        }
        step3_form = asyncio.run(flow.async_step_equipment(user_input=step2_data))
        self.assertEqual(step3_form["type"], "form")
        self.assertEqual(step3_form["step_id"], "sensors")

        # Step 3: Sensors
        step3_data = {
            CONF_SENSOR_T_IN: "sensor.indoor_temp",
            CONF_SENSOR_T_OUT: "sensor.outdoor_temp",
            CONF_SENSOR_AC_POWER: "sensor.ac_power",
        }
        result = asyncio.run(flow.async_step_sensors(user_input=step3_data))
        self.assertEqual(result["type"], "create_entry")
        self.assertEqual(result["title"], "Thermal Balance (25.0 m²)")
        self.assertEqual(result["data"][CONF_ROOM_AREA], 25.0)
        self.assertEqual(result["data"][CONF_AC_MAX_COOLING], 3500.0)
        self.assertEqual(result["data"][CONF_SENSOR_T_IN], "sensor.indoor_temp")

    def test_options_flow_3_step_wizard(self) -> None:
        """Test 3-step Options Flow wizard for existing entries."""
        entry = MockConfigEntry(
            data={
                CONF_ROOM_AREA: 20.0,
                CONF_AC_MAX_COOLING: 3350.0,
                CONF_SENSOR_T_IN: "sensor.room_temp",
                CONF_SENSOR_T_OUT: "sensor.ext_temp",
                CONF_SENSOR_AC_POWER: "sensor.ac_pwr",
            }
        )
        flow = ThermalBalanceOptionsFlow(entry)

        # Step 1: Geometry
        step1_res = asyncio.run(flow.async_step_init(user_input={CONF_ROOM_AREA: 30.0}))
        self.assertEqual(step1_res["type"], "form")
        self.assertEqual(step1_res["step_id"], "equipment")

        # Step 2: Equipment
        step2_res = asyncio.run(flow.async_step_equipment(user_input={CONF_AC_MAX_COOLING: 5000.0}))
        self.assertEqual(step2_res["type"], "form")
        self.assertEqual(step2_res["step_id"], "sensors")

        # Step 3: Sensors
        step3_res = asyncio.run(flow.async_step_sensors(user_input={CONF_SENSOR_T_IN: "sensor.new_room_temp"}))
        self.assertEqual(step3_res["type"], "create_entry")
        self.assertEqual(step3_res["data"][CONF_ROOM_AREA], 30.0)
        self.assertEqual(step3_res["data"][CONF_AC_MAX_COOLING], 5000.0)
        self.assertEqual(step3_res["data"][CONF_SENSOR_T_IN], "sensor.new_room_temp")

    def test_reconfigure_flow_3_step_wizard(self) -> None:
        """Test Gold Quality Scale 3-step reconfigure flow."""
        entry = MockConfigEntry(
            data={
                CONF_ROOM_AREA: 20.0,
                CONF_AC_MAX_COOLING: 3350.0,
            }
        )
        flow = ThermalBalanceConfigFlow()
        flow._reconfigure_entry = entry

        # Step 1: Reconfigure Geometry
        step1 = asyncio.run(flow.async_step_reconfigure(user_input={CONF_ROOM_AREA: 22.0}))
        self.assertEqual(step1["type"], "form")
        self.assertEqual(step1["step_id"], "reconfigure_equipment")

        # Step 2: Reconfigure Equipment
        step2 = asyncio.run(flow.async_step_reconfigure_equipment(user_input={CONF_AC_MAX_COOLING: 4000.0}))
        self.assertEqual(step2["type"], "form")
        self.assertEqual(step2["step_id"], "reconfigure_sensors")

        # Step 3: Reconfigure Sensors
        step3 = asyncio.run(flow.async_step_reconfigure_sensors(user_input={CONF_SENSOR_T_IN: "sensor.updated_temp"}))
        self.assertEqual(step3["type"], "abort")
        self.assertEqual(step3["reason"], "reconfigure_successful")
        self.assertEqual(step3["data"][CONF_ROOM_AREA], 22.0)
        self.assertEqual(step3["data"][CONF_AC_MAX_COOLING], 4000.0)


if __name__ == "__main__":
    unittest.main()
