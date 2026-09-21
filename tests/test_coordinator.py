"""Unit tests for ThermalBalanceCoordinator."""
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from mock_ha import MockConfigEntry, MockHomeAssistant, MockState, setup_mock_homeassistant

setup_mock_homeassistant()

from custom_components.thermal_balance.coordinator import ThermalBalanceCoordinator
from custom_components.thermal_balance.const import (
    CONF_AC_MAX_COOLING,
    CONF_CURTAIN_TYPE,
    CONF_ELECTRICITY_RATE,
    CONF_HVAC_MODE,
    CONF_ROOM_AREA,
    CONF_SENSOR_AC_POWER,
    CONF_SENSOR_ILLUMINANCE,
    CONF_SENSOR_SOLAR,
    CONF_SENSOR_T_IN,
    CONF_SENSOR_T_OUT,
    CONF_SENSOR_WEATHER,
    CONF_SENSOR_WINDOW,
    CONF_USE_EMPIRICAL_HLC,
    HVAC_MODE_COOLING,
    HVAC_MODE_HEATING,
    SENSOR_DAILY_THERMAL_BALANCE,
    SENSOR_EMPIRICAL_K_FACTOR,
    SENSOR_EQUILIBRIUM_TEMPERATURE,
    SENSOR_INSTANT_HEAT_GAIN,
    SENSOR_REQUIRED_AC_POWER,
    SENSOR_TOTAL_HEAT_ABSORBED,
)


class TestThermalBalanceCoordinator(unittest.TestCase):
    """Test suite for ThermalBalanceCoordinator."""

    def setUp(self) -> None:
        """Set up test environment with mock HA and coordinator."""
        self.hass = MockHomeAssistant()
        self.entry_data = {
            CONF_ROOM_AREA: 20.0,
            CONF_AC_MAX_COOLING: 3350.0,
            CONF_ELECTRICITY_RATE: 4.32,
            CONF_SENSOR_T_IN: "sensor.indoor_temp",
            CONF_SENSOR_T_OUT: "sensor.outdoor_temp",
            CONF_SENSOR_AC_POWER: "sensor.ac_power",
            CONF_SENSOR_WEATHER: "weather.forecast",
            CONF_SENSOR_ILLUMINANCE: "sensor.room_lux",
            CONF_SENSOR_WINDOW: "binary_sensor.window_contact",
            CONF_HVAC_MODE: HVAC_MODE_COOLING,
            CONF_USE_EMPIRICAL_HLC: True,
        }
        self.entry = MockConfigEntry(data=self.entry_data)
        self.coordinator = ThermalBalanceCoordinator(self.hass, self.entry)

    def test_coordinator_init(self) -> None:
        """Test coordinator initialization geometry and parameters."""
        self.assertEqual(self.coordinator.geometry.room_area, 20.0)
        self.assertEqual(self.coordinator.ac_max_cooling, 3350.0)
        self.assertEqual(self.coordinator.electricity_rate, 4.32)
        self.assertTrue(self.coordinator.has_weather_sensor)
        self.assertFalse(self.coordinator.has_solar_sensor)

    def test_recalculate_clear_sky_solar_estimation(self) -> None:
        """Test that solar irradiance is automatically estimated when solar sensor is absent."""
        # Set sun elevation to 60 degrees (summer noon) and clear weather
        self.hass.states.set("sun.sun", "above_horizon", {"elevation": 60.0, "azimuth": 180.0})
        self.hass.states.set("weather.forecast", "sunny", {"cloud_coverage": 0})
        self.hass.states.set("sensor.indoor_temp", "24.0")
        self.hass.states.set("sensor.outdoor_temp", "32.0")
        self.hass.states.set("sensor.ac_power", "800.0")

        self.coordinator.t_in_val = 24.0
        self.coordinator.t_out_val = 32.0
        self.coordinator.ac_power_val = 800.0

        self.coordinator.recalculate()

        # Solar value should be calculated automatically (> 800 W/m²)
        self.assertGreater(self.coordinator.solar_val, 750.0)
        self.assertIn(SENSOR_INSTANT_HEAT_GAIN, self.coordinator.data)
        self.assertIn(SENSOR_EQUILIBRIUM_TEMPERATURE, self.coordinator.data)
        self.assertIn(SENSOR_REQUIRED_AC_POWER, self.coordinator.data)
        self.assertGreater(self.coordinator.data[SENSOR_EQUILIBRIUM_TEMPERATURE], 32.0)

    def test_curtain_lux_auto_detection(self) -> None:
        """Test that curtains are detected closed when room illuminance is below threshold in daylight."""
        self.hass.states.set("sun.sun", "above_horizon", {"elevation": 45.0, "azimuth": 180.0})
        self.coordinator.illuminance_val = 50.0  # Lux < threshold 150
        self.coordinator.recalculate()
        self.assertTrue(self.coordinator.curtains_closed)

        # Higher lux -> curtains open
        self.coordinator.illuminance_val = 450.0
        self.coordinator.recalculate()
        self.assertFalse(self.coordinator.curtains_closed)

    def test_midnight_reset_accumulators(self) -> None:
        """Test that midnight reset zeros out daily accumulators."""
        self.coordinator.daily_heat_absorbed = 12.5
        self.coordinator.daily_ac_thermal_energy = 10.2
        self.coordinator.daily_ac_elec_kwh = 3.5
        self.coordinator.daily_shading_heat_saved_kwh = 2.1

        now = datetime.now(timezone.utc)
        self.coordinator._async_handle_midnight_reset(now)

        self.assertEqual(self.coordinator.daily_heat_absorbed, 0.0)
        self.assertEqual(self.coordinator.daily_ac_thermal_energy, 0.0)
        self.assertEqual(self.coordinator.daily_ac_elec_kwh, 0.0)
        self.assertEqual(self.coordinator.daily_shading_heat_saved_kwh, 0.0)

    def test_interactive_coordinator_actions(self) -> None:
        """Test button/number/select interactive coordinator actions."""
        import asyncio

        # Reset daily
        self.coordinator.daily_heat_absorbed = 5.0
        asyncio.run(self.coordinator.async_reset_daily())
        self.assertEqual(self.coordinator.daily_heat_absorbed, 0.0)

        # Set electricity rate
        asyncio.run(self.coordinator.async_set_electricity_rate(5.50))
        self.assertEqual(self.coordinator.electricity_rate, 5.50)

        # Set curtain type
        asyncio.run(self.coordinator.async_set_curtain_type("blackout"))
        self.assertEqual(self.coordinator.curtain_type, "blackout")

        # Reset K-factor
        self.coordinator._k_samples_count = 50
        asyncio.run(self.coordinator.async_reset_k_factor())
        self.assertEqual(self.coordinator._k_samples_count, 0)

    def test_temperature_derivative_regression(self) -> None:
        """Test indoor temperature linear regression derivative slope."""
        now = datetime.now(timezone.utc)

        # Populate rolling temperature readings: 22.0°C -> 20.0°C over 10 minutes (-12°C/hour slope clamped)
        self.coordinator.t_in_val = 22.0
        self.coordinator._calculate_t_in_derivative(now - timedelta(minutes=10))

        self.coordinator.t_in_val = 21.0
        self.coordinator._calculate_t_in_derivative(now - timedelta(minutes=5))

        self.coordinator.t_in_val = 20.0
        slope = self.coordinator._calculate_t_in_derivative(now)

        self.assertLess(slope, 0.0)  # Cooling down

    def test_monotonic_heat_accumulation_when_cooler_outside(self) -> None:
        """Test that heat accumulator does not decrease when outdoor is colder than indoor."""
        now = datetime.now(timezone.utc)
        self.coordinator.total_heat_absorbed = 10.0
        self.coordinator.daily_heat_absorbed = 5.0
        self.coordinator.last_update_time = now - timedelta(seconds=30)

        # Outdoor is cooler than indoor, solar is 0 -> p_env is negative (heat loss)
        self.coordinator.t_in_val = 24.0
        self.coordinator.t_out_val = 15.0
        self.coordinator.solar_val = 0.0
        self.coordinator.ac_power_val = 0.0

        self.coordinator.recalculate()

        # Net environmental flux should be negative
        self.assertLess(self.coordinator.data[SENSOR_INSTANT_HEAT_GAIN], 0.0)
        # But accumulated heat absorbed must NOT decrease!
        self.assertGreaterEqual(self.coordinator.total_heat_absorbed, 10.0)
        self.assertGreaterEqual(self.coordinator.daily_heat_absorbed, 5.0)

    def test_k_factor_ema_sampling_invariance(self) -> None:
        """Test that rapid sensor update bursts do not cause runaway K-factor smoothing."""
        self.coordinator.empirical_k_val = 10.0
        self.coordinator._k_samples_count = 0
        self.coordinator.window_is_open = False
        self.coordinator.ac_power_val = 500.0
        self.coordinator.t_in_val = 24.0
        self.coordinator.t_out_val = 32.0

        # Simulate 20 rapid recalculations arriving within sub-second intervals (e.g. sensor flutter)
        for _ in range(20):
            self.coordinator.recalculate()

        # Because minimum calibration interval is 15s, samples count must not increment 20 times!
        self.assertLessEqual(self.coordinator._k_samples_count, 1)

    def test_dt_dt_history_resilience_to_sensor_flood(self) -> None:
        """Test that rapid non-temperature updates do not exhaust the 10-minute dT/dt regression window."""
        now = datetime.now(timezone.utc)

        # Record genuine temperature drop: 23°C at t-8m, 21°C at t-4m
        self.coordinator.t_in_val = 23.0
        self.coordinator._calculate_t_in_derivative(now - timedelta(minutes=8))
        self.coordinator.t_in_val = 21.0
        self.coordinator._calculate_t_in_derivative(now - timedelta(minutes=4))

        # Now simulate 100 rapid power/lux sensor updates in 5 seconds where indoor temp is unchanged (20°C)
        self.coordinator.t_in_val = 20.0
        for i in range(100):
            t_instant = now + timedelta(milliseconds=i * 50)
            self.coordinator._calculate_t_in_derivative(t_instant)

        # Buffer must NOT be cleared of historical points from 8 and 4 minutes ago
        self.assertGreaterEqual(len(self.coordinator._t_in_history), 3)
        t_span = (self.coordinator._t_in_history[-1][0] - self.coordinator._t_in_history[0][0]).total_seconds()
        self.assertGreater(t_span, 200.0)

        # Slope must still accurately reflect the cooling trend (< 0)
        slope = self.coordinator._calculate_t_in_derivative(now + timedelta(seconds=6))
        self.assertLess(slope, 0.0)

    def test_restore_state_same_day_vs_previous_day(self) -> None:
        """Test that state restoration preserves all-time accumulators and only restores daily on same day."""
        import asyncio
        from custom_components.thermal_balance.sensor import ThermalBalanceSensor, SENSOR_TYPES

        now = datetime.now(timezone.utc)
        yesterday = now - timedelta(days=1)

        total_desc = next(d for d in SENSOR_TYPES if d.key == SENSOR_TOTAL_HEAT_ABSORBED)
        daily_desc = next(d for d in SENSOR_TYPES if d.key == SENSOR_DAILY_THERMAL_BALANCE)

        # --- Test 1: Restore from same day ---
        sensor_daily = ThermalBalanceSensor(self.coordinator, self.entry, daily_desc)
        sensor_daily._mock_last_state = MockState(
            state="2.5",
            attributes={"daily_heat_absorbed": 3.0, "daily_ac_thermal_energy": 0.5},
            last_updated=now,
        )
        asyncio.run(sensor_daily.async_added_to_hass())

        self.assertEqual(self.coordinator.daily_heat_absorbed, 3.0)
        self.assertEqual(self.coordinator.daily_ac_thermal_energy, 0.5)

        # --- Test 2: Restore from previous day ---
        self.coordinator.daily_heat_absorbed = 0.0
        self.coordinator.daily_ac_thermal_energy = 0.0

        sensor_daily_old = ThermalBalanceSensor(self.coordinator, self.entry, daily_desc)
        sensor_daily_old._mock_last_state = MockState(
            state="2.5",
            attributes={"daily_heat_absorbed": 9.0, "daily_ac_thermal_energy": 7.0},
            last_updated=yesterday,
        )
        asyncio.run(sensor_daily_old.async_added_to_hass())

        # Stale daily accumulators from yesterday must NOT be restored!
        self.assertEqual(self.coordinator.daily_heat_absorbed, 0.0)
        self.assertEqual(self.coordinator.daily_ac_thermal_energy, 0.0)

        # But total heat absorbed must be restored regardless of day
        sensor_total = ThermalBalanceSensor(self.coordinator, self.entry, total_desc)
        sensor_total._mock_last_state = MockState(state="125.4", last_updated=yesterday)
        asyncio.run(sensor_total.async_added_to_hass())
        self.assertEqual(self.coordinator.total_heat_absorbed, 125.4)
        self.assertEqual(self.coordinator.data[SENSOR_TOTAL_HEAT_ABSORBED], 125.4)


if __name__ == "__main__":
    unittest.main()
