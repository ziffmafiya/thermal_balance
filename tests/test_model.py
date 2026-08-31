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
    calculate_dynamic_k_factor,
    calculate_enthalpy,
    calculate_equilibrium_temperature,
    calculate_humidity_ratio,
    calculate_required_hvac_power,
    calculate_solar_radiation,
    calculate_thermal_balance,
    estimate_solar_irradiance,
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

    def test_thermal_balance_negative_heat_loss(self) -> None:
        """Test negative heat flux (heat loss) when outdoor is cooler and window is open."""
        inputs = ThermodynamicInputs(
            t_in=24.0,
            t_out=18.0,
            solar_irradiance=0.0,
            ac_power=0.0,
            window_is_open=True,
        )
        result = calculate_thermal_balance(self.geometry, inputs, 3350.0, 370.0)

        # In cold weather with window open, p_gain / p_env must be negative (heat loss)
        self.assertLess(result.p_gain, 0.0)
        self.assertLess(result.p_env, 0.0)
        self.assertLess(result.p_net, 0.0)
        self.assertEqual(result.direction, "cooling")

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

    def test_solar_radiation_south_facing_noon(self) -> None:
        """Test direct sun entering a South-facing window at solar noon."""
        # Window faces South (180°), Sun at South (180°), Elevation 60°
        p_total, p_dir, p_diff, aoi_deg, cos_aoi, is_direct = calculate_solar_radiation(
            window_area=3.0,
            solar_irradiance=800.0,
            curtain_g_factor=0.70,
            window_azimuth=180.0,
            sun_elevation_deg=60.0,
            sun_azimuth_deg=180.0,
            has_sun_position=True,
        )

        self.assertTrue(is_direct)
        self.assertAlmostEqual(cos_aoi, 0.50, delta=0.01)
        self.assertAlmostEqual(aoi_deg, 60.0, delta=0.5)
        self.assertGreater(p_dir, 0.0)
        self.assertGreater(p_diff, 0.0)
        self.assertAlmostEqual(p_total, p_dir + p_diff, delta=0.01)
        self.assertGreater(p_dir, p_diff)

    def test_solar_radiation_north_facing_noon(self) -> None:
        """Test that a North-facing window receives only diffuse radiation at solar noon."""
        # Window faces North (0°), Sun at South (180°), Elevation 60°
        p_total, p_dir, p_diff, aoi_deg, cos_aoi, is_direct = calculate_solar_radiation(
            window_area=3.0,
            solar_irradiance=800.0,
            curtain_g_factor=0.70,
            window_azimuth=0.0,
            sun_elevation_deg=60.0,
            sun_azimuth_deg=180.0,
            has_sun_position=True,
        )

        self.assertFalse(is_direct)
        self.assertLess(cos_aoi, 0.0)
        self.assertEqual(p_dir, 0.0)
        self.assertGreater(p_diff, 0.0)
        self.assertEqual(p_total, p_diff)

    def test_solar_radiation_east_vs_west_morning(self) -> None:
        """Test morning sun on East vs West facing windows."""
        # Morning: Sun at East (90°), elevation 30°
        # East window (90°)
        _, p_dir_east, _, _, _, is_direct_east = calculate_solar_radiation(
            window_area=3.0,
            solar_irradiance=600.0,
            curtain_g_factor=0.70,
            window_azimuth=90.0,
            sun_elevation_deg=30.0,
            sun_azimuth_deg=90.0,
            has_sun_position=True,
        )

        # West window (270°)
        _, p_dir_west, _, _, _, is_direct_west = calculate_solar_radiation(
            window_area=3.0,
            solar_irradiance=600.0,
            curtain_g_factor=0.70,
            window_azimuth=270.0,
            sun_elevation_deg=30.0,
            sun_azimuth_deg=90.0,
            has_sun_position=True,
        )

        self.assertTrue(is_direct_east)
        self.assertGreater(p_dir_east, 500.0)

        self.assertFalse(is_direct_west)
        self.assertEqual(p_dir_west, 0.0)

    def test_solar_radiation_night_and_zero_irradiance(self) -> None:
        """Test solar radiation is zero at night or zero irradiance."""
        # Sun below horizon (-10°)
        p_total, p_dir, p_diff, aoi_deg, cos_aoi, is_direct = calculate_solar_radiation(
            window_area=3.0,
            solar_irradiance=0.0,
            curtain_g_factor=0.70,
            window_azimuth=180.0,
            sun_elevation_deg=-10.0,
            sun_azimuth_deg=0.0,
            has_sun_position=True,
        )
        self.assertEqual(p_total, 0.0)
        self.assertEqual(p_dir, 0.0)
        self.assertEqual(p_diff, 0.0)
        self.assertFalse(is_direct)

    def test_solar_radiation_fallback_without_sun_position(self) -> None:
        """Test fallback calculation when sun position is not provided."""
        p_total, p_dir, p_diff, aoi_deg, cos_aoi, is_direct = calculate_solar_radiation(
            window_area=3.0,
            solar_irradiance=500.0,
            curtain_g_factor=0.70,
            window_azimuth=180.0,
            sun_elevation_deg=0.0,
            sun_azimuth_deg=180.0,
            has_sun_position=False,
        )
        self.assertAlmostEqual(p_total, 3.0 * 500.0 * 0.70, delta=0.01)
        self.assertAlmostEqual(p_dir, p_total * 0.8, delta=0.01)
        self.assertAlmostEqual(p_diff, p_total * 0.2, delta=0.01)

    def test_ac_performance_heating_mode(self) -> None:
        """Test AC performance in heat pump heating mode."""
        inputs = ThermodynamicInputs(
            t_in=20.0,
            t_out=2.0,
            solar_irradiance=0.0,
            ac_power=800.0,
            is_heating=True,
            hvac_mode="heating",
        )
        perf = calculate_ac_performance(inputs, ac_max_cooling=3500.0, ac_airflow_m3h=370.0)

        self.assertTrue(perf.is_heating)
        self.assertEqual(perf.p_cooling, 0.0)
        self.assertEqual(perf.p_cooling_latent, 0.0)
        self.assertEqual(perf.condensation_rate_lh, 0.0)
        self.assertEqual(perf.shr, 1.0)
        self.assertGreater(perf.p_heating, 1500.0)
        self.assertGreater(perf.cop, 2.0)
        self.assertGreater(perf.t_ac_exit, inputs.t_in)

    def test_ac_performance_heating_standby(self) -> None:
        """Test heating mode when AC is in standby / off (power < 20W)."""
        inputs = ThermodynamicInputs(
            t_in=20.0,
            t_out=0.0,
            solar_irradiance=0.0,
            ac_power=5.0,
            is_heating=True,
            hvac_mode="heating",
        )
        perf = calculate_ac_performance(inputs, ac_max_cooling=3500.0, ac_airflow_m3h=370.0)

        self.assertTrue(perf.is_heating)
        self.assertEqual(perf.p_heating, 0.0)
        self.assertEqual(perf.p_cooling, 0.0)
        self.assertEqual(perf.cop, 0.0)
        self.assertEqual(perf.t_ac_exit, inputs.t_in)

    def test_thermal_balance_winter_heating(self) -> None:
        """Test winter sub-zero scenario with walls losing heat and AC heating."""
        inputs = ThermodynamicInputs(
            t_in=21.0,
            t_out=-5.0,
            solar_irradiance=0.0,
            ac_power=900.0,
            is_heating=True,
            hvac_mode="heating",
        )
        result = calculate_thermal_balance(
            self.geometry,
            inputs,
            ac_max_cooling=3500.0,
            ac_airflow_m3h=370.0,
        )

        self.assertTrue(result.is_heating)
        self.assertEqual(result.hvac_mode, "heating")
        self.assertLess(result.p_wall, 0.0)  # Walls losing heat in winter
        self.assertGreater(result.p_heating, 2000.0)  # Heat pump supplying heat
        self.assertEqual(result.p_cooling, 0.0)
        # Net balance is positive (room heating up)
        self.assertGreater(result.p_net, 0.0)
        self.assertEqual(result.direction, "heating")
        self.assertGreater(result.time_to_1deg_min, 0.0)

    def test_dynamic_k_factor_steady_state(self) -> None:
        """Test dynamic K-factor calculation under steady state conditions (dT/dt = 0)."""
        # T_in = 24°C, T_out = 34°C, Delta T = 10K, HLC_theor = 15.3 W/K
        # Real wall transmission = 153 W, Solar = 100 W, AC sensible = 253 W
        k_instant, p_storage, p_wall_dyn = calculate_dynamic_k_factor(
            t_in=24.0,
            t_out=34.0,
            p_hvac=253.0,
            p_solar=100.0,
            c_total=800.0,
            dt_dt_c_per_h=0.0,
            hlc_theoretical=15.3,
            is_heating=False,
        )
        self.assertIsNotNone(k_instant)
        self.assertEqual(p_storage, 0.0)
        self.assertAlmostEqual(p_wall_dyn, 153.0, delta=0.1)
        self.assertAlmostEqual(k_instant, 15.3, delta=0.1)

    def test_dynamic_k_factor_rapid_cooling_pulldown(self) -> None:
        """Test that rapid pulldown cooldown discharges thermal mass without inflating K-factor."""
        # T_in = 24°C, T_out = 34°C, Delta T = 10K, true HLC = 15.3 W/K (wall flux = 153 W)
        # AC is running hard: sensible cooling = 1753 W, solar = 0 W
        # Room cooling at rate dT/dt = -2.0 °C/h, mass discharge = 800 * (-2.0) = -1600 W
        # Old formula without dT/dt: K_old = 1753 / 10 = 175.3 W/K (overestimated 11x!)
        # Dynamic formula: P_wall = 1753 - 1600 = 153 W -> K = 15.3 W/K (Exact!)
        k_instant, p_storage, p_wall_dyn = calculate_dynamic_k_factor(
            t_in=24.0,
            t_out=34.0,
            p_hvac=1753.0,
            p_solar=0.0,
            c_total=800.0,
            dt_dt_c_per_h=-2.0,
            hlc_theoretical=15.3,
            is_heating=False,
        )
        self.assertIsNotNone(k_instant)
        self.assertAlmostEqual(p_storage, -1600.0, delta=0.1)
        self.assertAlmostEqual(p_wall_dyn, 153.0, delta=0.1)
        self.assertAlmostEqual(k_instant, 15.3, delta=0.1)

    def test_dynamic_k_factor_rapid_heating_warmup(self) -> None:
        """Test dynamic K-factor calculation during rapid heat pump winter warmup."""
        # T_in = 20°C, T_out = 0°C, Delta T = 20K, true HLC = 20.0 W/K (wall heat loss = 400 W)
        # Heat pump delivering 2000 W, solar = 0 W
        # Room warming at rate dT/dt = +2.0 °C/h, thermal mass storage = 800 * 2.0 = +1600 W
        # P_wall_dyn = 2000 - 1600 = 400 W -> K = 400 / 20 = 20.0 W/K
        k_instant, p_storage, p_wall_dyn = calculate_dynamic_k_factor(
            t_in=20.0,
            t_out=0.0,
            p_hvac=2000.0,
            p_solar=0.0,
            c_total=800.0,
            dt_dt_c_per_h=2.0,
            hlc_theoretical=20.0,
            is_heating=True,
        )
        self.assertIsNotNone(k_instant)
        self.assertAlmostEqual(p_storage, 1600.0, delta=0.1)
        self.assertAlmostEqual(p_wall_dyn, 400.0, delta=0.1)
        self.assertAlmostEqual(k_instant, 20.0, delta=0.1)

    def test_dynamic_k_factor_small_delta_t_rejection(self) -> None:
        """Test that K-factor estimation is skipped when delta_t < 1.5K."""
        k_instant, p_storage, p_wall_dyn = calculate_dynamic_k_factor(
            t_in=22.0,
            t_out=22.5,
            p_hvac=500.0,
            p_solar=0.0,
            c_total=800.0,
            dt_dt_c_per_h=0.0,
            hlc_theoretical=15.0,
            is_heating=False,
        )
        self.assertIsNone(k_instant)

    def test_calculate_equilibrium_temperature(self) -> None:
        """Test passive equilibrium temperature calculation without HVAC."""
        # T_out = 30°C, P_solar = 300W, HLC = 15 W/K -> T_eq = 30 + 300/15 = 50°C
        t_eq = calculate_equilibrium_temperature(t_out=30.0, p_solar=300.0, hlc_total=15.0)
        self.assertAlmostEqual(t_eq, 50.0, delta=0.1)

        # Zero solar -> T_eq = T_out
        t_eq_night = calculate_equilibrium_temperature(t_out=18.0, p_solar=0.0, hlc_total=15.0)
        self.assertAlmostEqual(t_eq_night, 18.0, delta=0.1)

    def test_calculate_required_hvac_power_cooling(self) -> None:
        """Test required cooling power calculation to hold 23°C target."""
        # T_target = 23°C, T_out = 33°C, P_solar = 200W, HLC = 15 W/K
        # P_req = 15 * (33 - 23) + 200 = 350 W
        p_req = calculate_required_hvac_power(
            t_target=23.0,
            t_out=33.0,
            p_solar=200.0,
            hlc_total=15.0,
            is_heating=False,
        )
        self.assertAlmostEqual(p_req, 350.0, delta=0.1)

    def test_calculate_required_hvac_power_heating(self) -> None:
        """Test required heating power calculation in winter to hold 22°C target."""
        # T_target = 22°C, T_out = -8°C, P_solar = 100W, HLC = 20 W/K
        # P_req = 20 * (22 - (-8)) - 100 = 600 - 100 = 500 W
        p_req = calculate_required_hvac_power(
            t_target=22.0,
            t_out=-8.0,
            p_solar=100.0,
            hlc_total=20.0,
            is_heating=True,
        )
        self.assertAlmostEqual(p_req, 500.0, delta=0.1)

    def test_insufficient_cooling_capacity_alert(self) -> None:
        """Test insufficient capacity alert when heat gain exceeds max AC capacity."""
        inputs = ThermodynamicInputs(
            t_in=25.0,
            t_out=42.0,
            solar_irradiance=1000.0,
            curtains_closed=False,
            ac_power=1000.0,
            is_heating=False,
        )
        # AC max cooling = 2000 W, but total gain will be > 2000 W
        result = calculate_thermal_balance(
            self.geometry,
            inputs,
            ac_max_cooling=2000.0,
            ac_airflow_m3h=300.0,
        )
        self.assertTrue(result.is_capacity_insufficient)
        self.assertGreater(result.p_gain, 2000.0)

    def test_estimate_solar_irradiance_noon_summer(self) -> None:
        """Test Clear-Sky solar irradiance estimation on a sunny summer noon (elevation 65°)."""
        irr = estimate_solar_irradiance(sun_elevation_deg=65.0, cloud_coverage_pct=0.0)
        self.assertGreater(irr, 850.0)
        self.assertLess(irr, 1050.0)

    def test_estimate_solar_irradiance_night_and_zero(self) -> None:
        """Test solar irradiance estimation when sun is at or below horizon."""
        self.assertEqual(estimate_solar_irradiance(sun_elevation_deg=0.0, cloud_coverage_pct=0.0), 0.0)
        self.assertEqual(estimate_solar_irradiance(sun_elevation_deg=-15.0, cloud_coverage_pct=0.0), 0.0)

    def test_estimate_solar_irradiance_cloud_attenuation(self) -> None:
        """Test cloud cover attenuation reduces clear-sky irradiance."""
        irr_clear = estimate_solar_irradiance(sun_elevation_deg=50.0, cloud_coverage_pct=0.0)
        irr_partly = estimate_solar_irradiance(sun_elevation_deg=50.0, cloud_coverage_pct=50.0)
        irr_overcast = estimate_solar_irradiance(sun_elevation_deg=50.0, cloud_coverage_pct=100.0)

        self.assertGreater(irr_clear, irr_partly)
        self.assertGreater(irr_partly, irr_overcast)
        # 100% overcast attenuates by ~75%
        self.assertAlmostEqual(irr_overcast, irr_clear * 0.25, delta=irr_clear * 0.05)


if __name__ == "__main__":
    unittest.main()




