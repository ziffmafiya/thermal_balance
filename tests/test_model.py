"""Unit tests for pure Python thermodynamic model of Thermal Balance."""
import os
import sys
import unittest

# Allow importing model directly without triggering custom_components/__init__.py
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "custom_components", "thermal_balance")))

from model import (
    CURTAIN_TYPE_FACTORS,
    RoomGeometry,
    ThermodynamicInputs,
    calculate_ac_performance,
    calculate_dew_point,
    calculate_enthalpy,
    calculate_humidity_ratio,
    calculate_thermal_balance,
)


class TestThermodynamicModel(unittest.TestCase):
    """Test suite for thermodynamic model functions and classes."""

    def setUp(self) -> None:
        """Set up standard room geometry for testing."""
        self.geometry = RoomGeometry(
            room_area=20.0,
            ceiling_height=2.7,
            window_area=3.0,
            external_walls_fraction=0.25,
            u_wall=0.3,
            u_window=1.1,
        )

    def test_dew_point_calculation(self) -> None:
        """Test Magnus-Tetens dew point formula accuracy."""
        dp = calculate_dew_point(25.0, 50.0)
        self.assertAlmostEqual(dp, 13.9, delta=0.3)

        dp_100 = calculate_dew_point(20.0, 100.0)
        self.assertAlmostEqual(dp_100, 20.0, delta=0.1)

        dp_zero = calculate_dew_point(20.0, 0.0)
        self.assertEqual(dp_zero, 20.0)

    def test_humidity_ratio_and_enthalpy(self) -> None:
        """Test humidity ratio and moist air specific enthalpy calculations."""
        w = calculate_humidity_ratio(25.0, 50.0)
        self.assertGreater(w, 0.009)
        self.assertLess(w, 0.011)

        h = calculate_enthalpy(25.0, 50.0)
        self.assertAlmostEqual(h, 50.5, delta=1.5)

    def test_room_geometry_properties(self) -> None:
        """Test room capacity and theoretical HLC calculation."""
        self.assertAlmostEqual(self.geometry.volume, 54.0, delta=0.01)
        self.assertAlmostEqual(self.geometry.c_air, 18.144, delta=0.01)
        self.assertAlmostEqual(self.geometry.c_mass, 800.0, delta=0.01)
        self.assertAlmostEqual(self.geometry.c_total, 818.144, delta=0.01)

        self.assertGreater(self.geometry.hlc_theoretical, 0.0)
        self.assertLess(self.geometry.hlc_theoretical, 20.0)

    def test_ac_performance_when_off(self) -> None:
        """Test AC performance when electrical power is below 20W threshold."""
        inputs = ThermodynamicInputs(
            t_in=25.0,
            t_out=32.0,
            solar_irradiance=500.0,
            ac_power=10.0,
        )
        perf = calculate_ac_performance(inputs, ac_max_cooling=3500.0, ac_airflow_m3h=370.0)

        self.assertEqual(perf.p_cooling, 0.0)
        self.assertEqual(perf.p_cooling_sensible, 0.0)
        self.assertEqual(perf.cop, 0.0)
        self.assertEqual(perf.condensation_rate_lh, 0.0)
        self.assertEqual(perf.t_ac_exit, 25.0)

    def test_ac_performance_when_running_model(self) -> None:
        """Test AC performance in theoretical COP mode (no louver exit sensor)."""
        inputs = ThermodynamicInputs(
            t_in=24.0,
            t_out=32.0,
            solar_irradiance=400.0,
            ac_power=600.0,
            rh_in=50.0,
            has_rh_in=True,
        )
        perf = calculate_ac_performance(inputs, ac_max_cooling=3500.0, ac_airflow_m3h=370.0)

        self.assertGreater(perf.p_cooling, 1500.0)
        self.assertGreater(perf.cop, 2.5)
        self.assertLess(perf.cop, 5.5)
        self.assertGreater(perf.p_cooling_sensible, 0.0)
        self.assertGreater(perf.p_cooling_latent, 0.0)
        self.assertLess(perf.t_ac_exit, 24.0)

    def test_ac_performance_with_measured_louver_sensor(self) -> None:
        """Test AC performance when physical outlet temperature sensor is available."""
        inputs = ThermodynamicInputs(
            t_in=25.0,
            t_out=33.0,
            solar_irradiance=600.0,
            ac_power=750.0,
            t_ac_exit=12.0,
            has_t_ac_exit=True,
            rh_in=55.0,
            has_rh_in=True,
        )
        perf = calculate_ac_performance(inputs, ac_max_cooling=3500.0, ac_airflow_m3h=370.0)

        self.assertEqual(perf.t_ac_exit, 12.0)
        self.assertEqual(perf.delta_t_ac, 13.0)
        self.assertGreater(perf.p_cooling, 1000.0)

    def test_thermal_balance_heating_scenario(self) -> None:
        """Test thermal balance under hot sunny conditions with AC off."""
        inputs = ThermodynamicInputs(
            t_in=22.0,
            t_out=32.0,
            solar_irradiance=600.0,
            ac_power=0.0,
            window_is_open=False,
            curtains_closed=False,
        )
        result = calculate_thermal_balance(self.geometry, inputs, 3350.0, 370.0)

        self.assertGreater(result.p_gain, 1000.0)
        self.assertEqual(result.direction, "heating")
        self.assertGreater(result.time_to_1deg_min, 0.0)
        self.assertGreater(result.p_net, 0.0)

    def test_thermal_balance_cooling_scenario(self) -> None:
        """Test thermal balance when AC cooling exceeds heat gain."""
        inputs = ThermodynamicInputs(
            t_in=25.0,
            t_out=28.0,
            solar_irradiance=100.0,
            ac_power=800.0,
            window_is_open=False,
            curtains_closed=True,
            curtain_type="blackout",
        )
        result = calculate_thermal_balance(self.geometry, inputs, 3350.0, 370.0)

        self.assertLess(result.p_net, 0.0)
        self.assertEqual(result.direction, "cooling")
        self.assertGreater(result.time_to_1deg_min, 0.0)

    def test_curtain_shading_effect(self) -> None:
        """Test reduction of solar heat gain with curtains closed."""
        inputs_open = ThermodynamicInputs(
            t_in=24.0,
            t_out=30.0,
            solar_irradiance=700.0,
            ac_power=0.0,
            curtains_closed=False,
        )
        res_open = calculate_thermal_balance(self.geometry, inputs_open, 3350.0, 370.0)

        inputs_closed = ThermodynamicInputs(
            t_in=24.0,
            t_out=30.0,
            solar_irradiance=700.0,
            ac_power=0.0,
            curtains_closed=True,
            curtain_type="blackout",
        )
        res_closed = calculate_thermal_balance(self.geometry, inputs_closed, 3350.0, 370.0)

        self.assertAlmostEqual(res_closed.p_solar / res_open.p_solar, 0.05 / 0.70, delta=0.01)

    def test_wind_driven_ventilation(self) -> None:
        """Test increased infiltration when window is open with wind blowing into the window."""
        inputs_no_wind = ThermodynamicInputs(
            t_in=22.0,
            t_out=28.0,
            solar_irradiance=0.0,
            ac_power=0.0,
            window_is_open=True,
            has_wind_speed=False,
        )
        res_no_wind = calculate_thermal_balance(self.geometry, inputs_no_wind, 3350.0, 370.0)

        inputs_wind = ThermodynamicInputs(
            t_in=22.0,
            t_out=28.0,
            solar_irradiance=0.0,
            ac_power=0.0,
            window_is_open=True,
            has_wind_speed=True,
            wind_speed_ms=4.0,
            wind_dir_deg=180.0,
            window_azimuth=180.0,
        )
        res_wind = calculate_thermal_balance(self.geometry, inputs_wind, 3350.0, 370.0)

        self.assertGreater(res_wind.ventilation_ach, res_no_wind.ventilation_ach)
        self.assertGreater(res_wind.hlc_vent, res_no_wind.hlc_vent)


if __name__ == "__main__":
    unittest.main()
