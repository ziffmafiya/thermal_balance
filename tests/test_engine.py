"""Unit tests for the pure Python domain ThermalEngine and its components."""
from datetime import datetime, timedelta, timezone
import os
import sys
import unittest

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from custom_components.thermal_balance.const import (
    BINARY_SENSOR_INSUFFICIENT_COOLING_CAPACITY,
    BINARY_SENSOR_RECOMMEND_CLOSE_CURTAINS,
    BINARY_SENSOR_RECOMMEND_OPEN_WINDOW,
    HVAC_MODE_AUTO,
    HVAC_MODE_COOLING,
    HVAC_MODE_HEATING,
    SENSOR_AC_CARNOT_COP,
    SENSOR_AC_CONDENSATION_RATE,
    SENSOR_AC_ENERGY_COST,
    SENSOR_AC_HEAT_OUTPUT,
    SENSOR_AC_THERMAL_ENERGY_TOTAL,
    SENSOR_DAILY_THERMAL_BALANCE,
    SENSOR_EMPIRICAL_K_FACTOR,
    SENSOR_EQUILIBRIUM_TEMPERATURE,
    SENSOR_INSTANT_HEAT_GAIN,
    SENSOR_INSTANT_NET_BALANCE,
    SENSOR_NET_THERMAL_BALANCE,
    SENSOR_REQUIRED_AC_POWER,
    SENSOR_SHADING_DAILY_SAVINGS,
    SENSOR_TIME_TO_1DEG,
    SENSOR_TOTAL_HEAT_ABSORBED,
)
from custom_components.thermal_balance.engine import (
    ClimateAdvisor,
    EnergyAccumulator,
    EngineCycleInputs,
    InsulationCalibrator,
    ThermalEngine,
    ThermalHistoryTracker,
    normalize_wind_speed,
    parse_cloud_coverage,
    resolve_curtains_closed,
    resolve_is_heating,
)
from custom_components.thermal_balance.model import RoomGeometry, ThermalCalculationResult


class TestMeteorologicalAdapters(unittest.TestCase):
    """Test pure meteorological and state adapter functions."""

    def test_parse_cloud_coverage_from_attributes(self) -> None:
        """Test cloud coverage parsed from attributes if present."""
        self.assertEqual(parse_cloud_coverage("sunny", {"cloud_coverage": 35}), 35.0)
        self.assertEqual(parse_cloud_coverage("sunny", {"cloud_coverage": "75"}), 75.0)

    def test_parse_cloud_coverage_from_weather_states(self) -> None:
        """Test cloud coverage heuristics based on weather condition string."""
        self.assertEqual(parse_cloud_coverage("sunny"), 0.0)
        self.assertEqual(parse_cloud_coverage("clear"), 0.0)
        self.assertEqual(parse_cloud_coverage("partlycloudy"), 40.0)
        self.assertEqual(parse_cloud_coverage("cloudy"), 80.0)
        self.assertEqual(parse_cloud_coverage("pouring"), 95.0)
        self.assertEqual(parse_cloud_coverage("unknown"), 0.0)
        self.assertEqual(parse_cloud_coverage(None), 0.0)

    def test_normalize_wind_speed(self) -> None:
        """Test wind speed unit conversion."""
        self.assertAlmostEqual(normalize_wind_speed(36.0, "km/h"), 10.0, places=2)
        self.assertAlmostEqual(normalize_wind_speed(18.0, "kmh"), 5.0, places=2)
        self.assertEqual(normalize_wind_speed(5.5, "m/s"), 5.5)
        self.assertEqual(normalize_wind_speed(4.0, None), 4.0)

    def test_resolve_is_heating_modes(self) -> None:
        """Test HVAC heating/cooling mode resolution."""
        # Explicit modes
        self.assertTrue(resolve_is_heating(HVAC_MODE_HEATING, None, None, 25.0, 20.0))
        self.assertFalse(resolve_is_heating(HVAC_MODE_COOLING, None, None, 5.0, 22.0))

        # Auto mode with thermostat action
        self.assertTrue(resolve_is_heating(HVAC_MODE_AUTO, "idle", "heating", 25.0, 20.0))
        self.assertFalse(resolve_is_heating(HVAC_MODE_AUTO, "idle", "cooling", 5.0, 22.0))

        # Auto mode with thermostat state
        self.assertTrue(resolve_is_heating(HVAC_MODE_AUTO, "heat", None, 25.0, 20.0))
        self.assertFalse(resolve_is_heating(HVAC_MODE_AUTO, "cool", None, 5.0, 22.0))

        # Auto mode fallback on temperatures (outdoor cold)
        self.assertTrue(resolve_is_heating(HVAC_MODE_AUTO, None, None, 10.0, 20.0))
        self.assertFalse(resolve_is_heating(HVAC_MODE_AUTO, None, None, 25.0, 22.0))

    def test_resolve_curtains_closed(self) -> None:
        """Test curtain detection based on illuminance and daylight."""
        # Sensor missing
        closed, note = resolve_curtains_closed(100.0, 150.0, has_illuminance_sensor=False, is_daylight=True)
        self.assertFalse(closed)
        self.assertIn("not configured", note)

        # Night time
        closed, note = resolve_curtains_closed(50.0, 150.0, has_illuminance_sensor=True, is_daylight=False)
        self.assertFalse(closed)
        self.assertIn("Night", note)

        # Daylight + dark indoor (closed curtains)
        closed, note = resolve_curtains_closed(80.0, 150.0, has_illuminance_sensor=True, is_daylight=True)
        self.assertTrue(closed)
        self.assertIsNone(note)

        # Daylight + bright indoor (open curtains)
        closed, note = resolve_curtains_closed(300.0, 150.0, has_illuminance_sensor=True, is_daylight=True)
        self.assertFalse(closed)
        self.assertIsNone(note)


class TestThermalHistoryTracker(unittest.TestCase):
    """Test rolling regression temperature derivative estimation."""

    def setUp(self) -> None:
        self.tracker = ThermalHistoryTracker()

    def test_derivative_empty_or_insufficient(self) -> None:
        """Test tracker returns 0.0 when history is empty or span < 45s."""
        now = datetime.now(timezone.utc)
        self.assertEqual(self.tracker.update(now, 22.0), 0.0)
        self.assertEqual(self.tracker.update(now + timedelta(seconds=25), 22.1), 0.0)

    def test_derivative_linear_slope(self) -> None:
        """Test accurate slope estimation over 5 minutes."""
        now = datetime.now(timezone.utc)
        # 1°C increase over 5 minutes (12°C/hour) clamped to 10°C/h
        self.tracker.update(now - timedelta(minutes=5), 20.0)
        self.tracker.update(now - timedelta(minutes=2, seconds=30), 20.5)
        slope = self.tracker.update(now, 21.0)
        self.assertEqual(slope, 10.0)  # Clamped maximum

        # Normal slope: +0.5°C over 10 minutes -> 3.0°C/hour
        self.tracker.reset()
        t0 = now - timedelta(minutes=8)
        self.tracker.update(t0, 20.0)
        self.tracker.update(t0 + timedelta(minutes=4), 20.2)
        slope2 = self.tracker.update(t0 + timedelta(minutes=8), 20.4)
        self.assertAlmostEqual(slope2, 3.0, delta=0.1)


class TestInsulationCalibrator(unittest.TestCase):
    """Test continuous-time EMA K-factor calibrator."""

    def setUp(self) -> None:
        self.initial_hlc = 25.0
        self.calibrator = InsulationCalibrator(self.initial_hlc)

    def test_reset(self) -> None:
        """Test calibrator reset."""
        self.calibrator.empirical_k_val = 40.0
        self.calibrator.samples_count = 15
        self.calibrator.reset(self.initial_hlc)
        self.assertEqual(self.calibrator.empirical_k_val, self.initial_hlc)
        self.assertEqual(self.calibrator.samples_count, 0)

    def test_grade_classification(self) -> None:
        """Test insulation grade thresholds."""
        self.calibrator.empirical_k_val = 25.0
        grade, dev = self.calibrator.get_grade(25.0)
        self.assertEqual(grade, "Excellent (passport)")
        self.assertAlmostEqual(dev, 0.0)

        self.calibrator.empirical_k_val = 32.0  # +28%
        grade, _ = self.calibrator.get_grade(25.0)
        self.assertEqual(grade, "Good (moderate)")

        self.calibrator.empirical_k_val = 45.0  # +80%
        grade, _ = self.calibrator.get_grade(25.0)
        self.assertEqual(grade, "Poor (drafts)")


class TestEnergyAccumulator(unittest.TestCase):
    """Test Riemann energy accumulation and financial calculations."""

    def setUp(self) -> None:
        self.accum = EnergyAccumulator()

    def test_monotonic_integration(self) -> None:
        """Test that negative p_gain does not decrement heat absorbed."""
        now = datetime.now(timezone.utc)
        self.accum.last_update_time = now - timedelta(seconds=30)
        self.accum.total_heat_absorbed = 5.0
        self.accum.daily_heat_absorbed = 2.0

        # Pass negative p_gain (-300W)
        self.accum.integrate_step(
            now=now,
            p_gain=-300.0,
            p_hvac_output=0.0,
            ac_power=0.0,
            p_solar=0.0,
            curtain_g_factor=0.7,
            curtain_saved_fraction=0.0,
            curtains_closed=False,
        )

        self.assertEqual(self.accum.total_heat_absorbed, 5.0)
        self.assertEqual(self.accum.daily_heat_absorbed, 2.0)

    def test_daily_boundary_rollover(self) -> None:
        """Test automatic daily counter reset when date rolls over."""
        t1 = datetime(2026, 6, 1, 23, 59, 0, tzinfo=timezone.utc)
        t2 = datetime(2026, 6, 2, 0, 1, 0, tzinfo=timezone.utc)

        self.accum.last_daily_reset = t1
        self.accum.daily_heat_absorbed = 10.0
        self.accum.total_heat_absorbed = 50.0

        rolled_over = self.accum.check_daily_boundary(t2)
        self.assertTrue(rolled_over)
        self.assertEqual(self.accum.daily_heat_absorbed, 0.0)
        self.assertEqual(self.accum.total_heat_absorbed, 50.0)

    def test_financial_calculations(self) -> None:
        """Test AC electricity cost and shading savings calculations."""
        self.accum.daily_ac_elec_kwh = 10.0
        self.accum.daily_shading_heat_saved_kwh = 6.4

        rate = 5.0  # 5.0 per kWh
        cop = 3.2
        cost, savings = self.accum.calculate_financials(rate, cop)

        self.assertAlmostEqual(cost, 50.0)  # 10 * 5.0
        self.assertAlmostEqual(savings, 10.0)  # (6.4 / 3.2) * 5.0


class TestClimateAdvisor(unittest.TestCase):
    """Test smart rule-based recommendations."""

    def test_recommend_open_window(self) -> None:
        """Test window opening advice when outdoor is cooler and room is warm."""
        rec_open, _ = ClimateAdvisor.evaluate(
            t_in=24.0,
            t_out=19.0,
            window_is_open=False,
            is_heating=False,
            is_daylight=True,
            p_solar_direct=0.0,
            p_solar=0.0,
            solar_val=0.0,
            sun_is_direct=False,
            curtains_closed=False,
        )
        self.assertTrue(rec_open)

        # Do not recommend if window already open
        rec_open_2, _ = ClimateAdvisor.evaluate(
            t_in=24.0,
            t_out=19.0,
            window_is_open=True,
            is_heating=False,
            is_daylight=True,
            p_solar_direct=0.0,
            p_solar=0.0,
            solar_val=0.0,
            sun_is_direct=False,
            curtains_closed=False,
        )
        self.assertFalse(rec_open_2)

    def test_recommend_close_curtains(self) -> None:
        """Test close curtains advice on intense direct sunlight."""
        _, rec_curtains = ClimateAdvisor.evaluate(
            t_in=24.0,
            t_out=30.0,
            window_is_open=False,
            is_heating=False,
            is_daylight=True,
            p_solar_direct=120.0,
            p_solar=250.0,
            solar_val=600.0,
            sun_is_direct=True,
            curtains_closed=False,
        )
        self.assertTrue(rec_curtains)


class TestThermalEngineCycle(unittest.TestCase):
    """Test end-to-end processing cycle through ThermalEngine."""

    def setUp(self) -> None:
        geometry = RoomGeometry(20.0, 2.7, 3.0, 0.25, 0.3, 1.1)
        self.engine = ThermalEngine(geometry)

    def test_full_cycle_execution(self) -> None:
        """Test that process_cycle runs and returns structured data and extra attributes."""
        now = datetime.now(timezone.utc)
        inputs = EngineCycleInputs(
            now=now,
            t_in=24.0,
            t_out=30.0,
            t_ac_exit=14.0,
            rh_in=50.0,
            rh_out=60.0,
            solar_irradiance=500.0,
            ac_power=800.0,
            window_is_open=False,
            curtains_closed=False,
            curtains_note=None,
            curtain_type="roller_gaps",
            wind_speed_ms=2.0,
            wind_dir_deg=180.0,
            window_azimuth=180.0,
            sun_elevation_deg=45.0,
            sun_azimuth_deg=180.0,
            has_sun_position=True,
            is_heating=False,
            hvac_mode=HVAC_MODE_COOLING,
            illuminance_lux=800.0,
            has_window_sensor=True,
            has_illuminance_sensor=True,
            has_wind_speed_sensor=True,
            has_wind_dir_sensor=True,
            has_t_ac_exit_sensor=True,
            has_rh_in_sensor=True,
            has_rh_out_sensor=True,
            electricity_rate=4.5,
            use_empirical_hlc=True,
            ac_max_cooling=3350.0,
            ac_airflow=550.0,
        )

        output = self.engine.process_cycle(inputs)

        # Check data payload
        self.assertIn(SENSOR_INSTANT_HEAT_GAIN, output.data)
        self.assertIn(SENSOR_AC_HEAT_OUTPUT, output.data)
        self.assertIn(SENSOR_INSTANT_NET_BALANCE, output.data)
        self.assertIn(SENSOR_AC_CARNOT_COP, output.data)
        self.assertIn(SENSOR_TOTAL_HEAT_ABSORBED, output.data)
        self.assertIn(BINARY_SENSOR_RECOMMEND_OPEN_WINDOW, output.data)
        self.assertIn(BINARY_SENSOR_RECOMMEND_CLOSE_CURTAINS, output.data)

        # Check extra attributes payload
        self.assertIn(SENSOR_INSTANT_HEAT_GAIN, output.extra_attributes)
        attrs_gain = output.extra_attributes[SENSOR_INSTANT_HEAT_GAIN]
        self.assertIn("p_solar_w", attrs_gain)
        self.assertIn("p_env_w", attrs_gain)
        self.assertIn("hlc_w_k", attrs_gain)
        self.assertEqual(attrs_gain["curtains_state"], "Open")


if __name__ == "__main__":
    unittest.main()
