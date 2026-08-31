"""Coordinator for Thermal Balance custom component."""
from __future__ import annotations

from collections import deque
from datetime import datetime, timedelta
import logging
import math
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_change,
    async_track_time_interval,
)
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    BINARY_SENSOR_INSUFFICIENT_COOLING_CAPACITY,
    BINARY_SENSOR_RECOMMEND_CLOSE_CURTAINS,
    BINARY_SENSOR_RECOMMEND_OPEN_WINDOW,
    CONF_AC_AIRFLOW,
    CONF_AC_MAX_COOLING,
    CONF_CEILING_HEIGHT,
    CONF_CURRENCY_SYMBOL,
    CONF_CURTAIN_TYPE,
    CONF_ELECTRICITY_RATE,
    CONF_EXTERNAL_WALLS_FRACTION,
    CONF_HVAC_MODE,
    CONF_ILLUMINANCE_THRESHOLD,
    CONF_ROOM_AREA,
    CONF_SENSOR_AC_POWER,
    CONF_SENSOR_CLIMATE,
    CONF_SENSOR_ILLUMINANCE,
    CONF_SENSOR_RH_IN,
    CONF_SENSOR_RH_OUT,
    CONF_SENSOR_SOLAR,
    CONF_SENSOR_T_AC_EXIT,
    CONF_SENSOR_T_IN,
    CONF_SENSOR_T_OUT,
    CONF_SENSOR_WEATHER,
    CONF_SENSOR_WIND_DIRECTION,
    CONF_SENSOR_WIND_SPEED,
    CONF_SENSOR_WINDOW,
    CONF_U_WALL,
    CONF_U_WINDOW,
    CONF_USE_EMPIRICAL_HLC,
    CONF_WINDOW_AREA,
    CONF_WINDOW_AZIMUTH,
    DEFAULT_AC_AIRFLOW,
    DEFAULT_AC_MAX_COOLING,
    DEFAULT_CEILING_HEIGHT,
    DEFAULT_CURTAIN_TYPE,
    DEFAULT_ELECTRICITY_RATE,
    DEFAULT_EXTERNAL_WALLS_FRACTION,
    DEFAULT_HVAC_MODE,
    DEFAULT_ILLUMINANCE_THRESHOLD,
    DEFAULT_ROOM_AREA,
    DEFAULT_U_WALL,
    DEFAULT_U_WINDOW,
    DEFAULT_USE_EMPIRICAL_HLC,
    DEFAULT_WINDOW_AREA,
    DEFAULT_WINDOW_AZIMUTH,
    DOMAIN,
    HVAC_MODE_AUTO,
    HVAC_MODE_COOLING,
    HVAC_MODE_HEATING,
    SELECT_CURTAIN_TYPE,
    SELECT_HVAC_MODE,
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
from .model import (
    RoomGeometry,
    ThermalCalculationResult,
    ThermodynamicInputs,
    calculate_dynamic_k_factor,
    calculate_thermal_balance,
    estimate_solar_irradiance,
)

_LOGGER = logging.getLogger(__name__)


def _safe_float(val: Any, default: float) -> float:
    """Safely convert value to float."""
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


class ThermalBalanceCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to manage thermodynamic calculations and state tracking."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"Thermal Balance ({entry.title})",
            always_update=False,
        )
        self.entry = entry

        options = entry.options
        data = entry.data

        # Room geometry
        room_area = _safe_float(options.get(CONF_ROOM_AREA, data.get(CONF_ROOM_AREA)), DEFAULT_ROOM_AREA)
        ceiling_height = _safe_float(options.get(CONF_CEILING_HEIGHT, data.get(CONF_CEILING_HEIGHT)), DEFAULT_CEILING_HEIGHT)
        window_area = _safe_float(options.get(CONF_WINDOW_AREA, data.get(CONF_WINDOW_AREA)), DEFAULT_WINDOW_AREA)
        external_walls_fraction = _safe_float(
            options.get(CONF_EXTERNAL_WALLS_FRACTION, data.get(CONF_EXTERNAL_WALLS_FRACTION)),
            DEFAULT_EXTERNAL_WALLS_FRACTION,
        )
        u_wall = _safe_float(options.get(CONF_U_WALL, data.get(CONF_U_WALL)), DEFAULT_U_WALL)
        u_window = _safe_float(options.get(CONF_U_WINDOW, data.get(CONF_U_WINDOW)), DEFAULT_U_WINDOW)

        self.geometry = RoomGeometry(
            room_area=room_area,
            ceiling_height=ceiling_height,
            window_area=window_area,
            external_walls_fraction=external_walls_fraction,
            u_wall=u_wall,
            u_window=u_window,
        )

        self.ac_max_cooling: float = _safe_float(options.get(CONF_AC_MAX_COOLING, data.get(CONF_AC_MAX_COOLING)), DEFAULT_AC_MAX_COOLING)
        self.ac_airflow: float = _safe_float(options.get(CONF_AC_AIRFLOW, data.get(CONF_AC_AIRFLOW)), DEFAULT_AC_AIRFLOW)

        # Entity IDs
        self.sensor_t_in: str = options.get(CONF_SENSOR_T_IN, data.get(CONF_SENSOR_T_IN, ""))
        self.sensor_t_out: str = options.get(CONF_SENSOR_T_OUT, data.get(CONF_SENSOR_T_OUT, ""))
        self.sensor_t_ac_exit: str = options.get(CONF_SENSOR_T_AC_EXIT, data.get(CONF_SENSOR_T_AC_EXIT, ""))
        self.sensor_rh_in: str = options.get(CONF_SENSOR_RH_IN, data.get(CONF_SENSOR_RH_IN, ""))
        self.sensor_rh_out: str = options.get(CONF_SENSOR_RH_OUT, data.get(CONF_SENSOR_RH_OUT, ""))
        self.sensor_solar: str = options.get(CONF_SENSOR_SOLAR, data.get(CONF_SENSOR_SOLAR, ""))
        self.sensor_weather: str = options.get(CONF_SENSOR_WEATHER, data.get(CONF_SENSOR_WEATHER, ""))
        self.sensor_ac_power: str = options.get(CONF_SENSOR_AC_POWER, data.get(CONF_SENSOR_AC_POWER, ""))
        self.sensor_climate: str = options.get(CONF_SENSOR_CLIMATE, data.get(CONF_SENSOR_CLIMATE, ""))
        self.hvac_mode: str = str(options.get(CONF_HVAC_MODE, data.get(CONF_HVAC_MODE, DEFAULT_HVAC_MODE)))
        self.is_heating: bool = (self.hvac_mode == HVAC_MODE_HEATING)
        self.sensor_window: str = options.get(CONF_SENSOR_WINDOW, data.get(CONF_SENSOR_WINDOW, ""))
        self.sensor_illuminance: str = options.get(CONF_SENSOR_ILLUMINANCE, data.get(CONF_SENSOR_ILLUMINANCE, ""))
        self.sensor_wind_speed: str = options.get(CONF_SENSOR_WIND_SPEED, data.get(CONF_SENSOR_WIND_SPEED, ""))
        self.sensor_wind_direction: str = options.get(CONF_SENSOR_WIND_DIRECTION, data.get(CONF_SENSOR_WIND_DIRECTION, ""))
        self.window_azimuth: float = _safe_float(options.get(CONF_WINDOW_AZIMUTH, data.get(CONF_WINDOW_AZIMUTH)), DEFAULT_WINDOW_AZIMUTH)
        self.illuminance_threshold: float = _safe_float(
            options.get(CONF_ILLUMINANCE_THRESHOLD, data.get(CONF_ILLUMINANCE_THRESHOLD)),
            DEFAULT_ILLUMINANCE_THRESHOLD,
        )

        self.electricity_rate: float = _safe_float(
            options.get(CONF_ELECTRICITY_RATE, data.get(CONF_ELECTRICITY_RATE, DEFAULT_ELECTRICITY_RATE)),
            DEFAULT_ELECTRICITY_RATE,
        )
        
        # Determine currency symbol: user setting -> hass default currency -> "USD"
        hass_currency = getattr(hass.config, "currency", None) or "USD"
        raw_currency = options.get(CONF_CURRENCY_SYMBOL, data.get(CONF_CURRENCY_SYMBOL))
        self.currency_symbol: str = str(raw_currency) if raw_currency else hass_currency

        self.curtain_type: str = str(options.get(CONF_CURTAIN_TYPE, data.get(CONF_CURTAIN_TYPE, DEFAULT_CURTAIN_TYPE)))
        self.use_empirical_hlc: bool = bool(options.get(CONF_USE_EMPIRICAL_HLC, data.get(CONF_USE_EMPIRICAL_HLC, DEFAULT_USE_EMPIRICAL_HLC)))

        # Empirical K-Factor state
        self.empirical_k_val: float = self.geometry.hlc_theoretical
        self._k_samples_count: int = 0
        self.hlc_closed: float = self.geometry.hlc_theoretical

        # Temperature history for dT/dt derivative estimation (timestamp, t_in)
        self._t_in_history: deque[tuple[datetime, float]] = deque(maxlen=60)
        self.dt_dt_c_per_h: float = 0.0
        self.p_storage_w: float = 0.0
        self.p_wall_dynamic_w: float = 0.0

        # Current sensor values
        self.t_in_val: float = 20.0
        self.t_out_val: float = 20.0
        self.t_ac_exit_val: float = 20.0
        self.rh_in_val: float = 50.0
        self.rh_out_val: float = 60.0
        self.solar_val: float = 0.0
        self.ac_power_val: float = 0.0
        self.window_is_open: bool = False
        self.illuminance_val: float = 500.0
        self.curtains_closed: bool = False
        self.curtains_note: str | None = None
        self.wind_speed_ms: float = 0.0
        self.wind_dir_deg: float = 0.0

        # Energy accumulators (kWh)
        self.total_heat_absorbed: float = 0.0
        self.ac_thermal_energy_total: float = 0.0
        self.daily_heat_absorbed: float = 0.0
        self.daily_ac_thermal_energy: float = 0.0
        self.daily_ac_elec_kwh: float = 0.0
        self.daily_shading_heat_saved_kwh: float = 0.0

        # Integration timing
        self.last_update_time: datetime | None = None
        self.last_daily_reset: datetime | None = None

        # Data & Extra Attributes
        self.extra_attributes: dict[str, dict[str, Any]] = {}
        self._unsub_track: list[Any] = []

        # Initial data map
        self.data = {
            SENSOR_INSTANT_HEAT_GAIN: 0.0,
            SENSOR_AC_HEAT_OUTPUT: 0.0,
            SENSOR_INSTANT_NET_BALANCE: 0.0,
            SENSOR_AC_CARNOT_COP: 0.0,
            SENSOR_TIME_TO_1DEG: 0.0,
            SENSOR_DAILY_THERMAL_BALANCE: 0.0,
            SENSOR_NET_THERMAL_BALANCE: 0.0,
            SENSOR_TOTAL_HEAT_ABSORBED: 0.0,
            SENSOR_AC_THERMAL_ENERGY_TOTAL: 0.0,
            SENSOR_AC_CONDENSATION_RATE: 0.0,
            SENSOR_EMPIRICAL_K_FACTOR: round(self.empirical_k_val, 2),
            SENSOR_EQUILIBRIUM_TEMPERATURE: 20.0,
            SENSOR_REQUIRED_AC_POWER: 0.0,
            SENSOR_AC_ENERGY_COST: 0.0,
            SENSOR_SHADING_DAILY_SAVINGS: 0.0,
            BINARY_SENSOR_RECOMMEND_OPEN_WINDOW: False,
            BINARY_SENSOR_RECOMMEND_CLOSE_CURTAINS: False,
            BINARY_SENSOR_INSUFFICIENT_COOLING_CAPACITY: False,
        }

    async def async_set_hvac_mode(self, mode: str) -> None:
        """Set HVAC operation mode (cooling / heating / auto)."""
        if mode in (HVAC_MODE_COOLING, HVAC_MODE_HEATING, HVAC_MODE_AUTO):
            self.hvac_mode = mode
            self.recalculate()

    async def async_set_curtain_type(self, curtain_type: str) -> None:
        """Set window curtain shading type."""
        self.curtain_type = curtain_type
        self.recalculate()

    async def async_set_electricity_rate(self, rate: float) -> None:
        """Set dynamic electricity rate."""
        self.electricity_rate = max(0.0, float(rate))
        self.recalculate()

    async def async_reset_daily(self) -> None:
        """Reset daily energy and financial accumulators."""
        self.daily_heat_absorbed = 0.0
        self.daily_ac_thermal_energy = 0.0
        self.daily_ac_elec_kwh = 0.0
        self.daily_shading_heat_saved_kwh = 0.0
        self.last_daily_reset = dt_util.now()
        self.recalculate()

    async def async_reset_k_factor(self) -> None:
        """Reset empirical K-factor learning samples."""
        self.empirical_k_val = self.geometry.hlc_theoretical
        self._k_samples_count = 0
        self.hlc_closed = self.geometry.hlc_theoretical
        self.recalculate()

    async def async_reset_accumulators(self) -> None:
        """Reset both daily and all-time accumulators."""
        self.total_heat_absorbed = 0.0
        self.ac_thermal_energy_total = 0.0
        await self.async_reset_daily()

    def _calculate_t_in_derivative(self, now: datetime) -> float:
        """Calculate indoor temperature derivative dT/dt in °C/hour using rolling linear regression."""
        # Append current reading
        self._t_in_history.append((now, self.t_in_val))

        # Filter out readings older than 10 minutes
        cutoff = now - timedelta(minutes=10)
        while self._t_in_history and self._t_in_history[0][0] < cutoff:
            self._t_in_history.popleft()

        # Need at least 3 points spanning at least 45 seconds for meaningful slope
        if len(self._t_in_history) < 3:
            return 0.0

        t0 = self._t_in_history[0][0]
        t_span = (self._t_in_history[-1][0] - t0).total_seconds()
        if t_span < 45.0:
            return 0.0

        # Linear regression slope in °C per hour
        times_h = [(t - t0).total_seconds() / 3600.0 for t, _ in self._t_in_history]
        temps = [temp for _, temp in self._t_in_history]

        n = len(times_h)
        mean_t = sum(times_h) / n
        mean_temp = sum(temps) / n

        denom = sum((t - mean_t) ** 2 for t in times_h)
        if denom <= 1e-7:
            return 0.0

        numer = sum((times_h[i] - mean_t) * (temps[i] - mean_temp) for i in range(n))
        slope = numer / denom

        # Clamp slope to realistic building thermodynamic bounds (-10°C/h to +10°C/h)
        return max(-10.0, min(10.0, slope))

    @property
    def has_solar_sensor(self) -> bool:
        """Check if a solar irradiance sensor entity ID is configured."""
        return bool(self.sensor_solar and self.sensor_solar.strip().lower() not in ("", "none", "null", "unknown", "unavailable"))

    @property
    def has_weather_sensor(self) -> bool:
        """Check if a weather entity ID is configured."""
        return bool(self.sensor_weather and self.sensor_weather.strip().lower() not in ("", "none", "null", "unknown", "unavailable"))

    @property
    def has_climate_sensor(self) -> bool:
        """Check if a climate thermostat entity ID is configured."""
        return bool(self.sensor_climate and self.sensor_climate.strip().lower() not in ("", "none", "null", "unknown", "unavailable"))

    @property
    def has_window_sensor(self) -> bool:
        """Check if a valid window binary_sensor entity ID is configured."""
        return bool(self.sensor_window and self.sensor_window.strip().lower() not in ("", "none", "null", "unknown", "unavailable"))

    @property
    def has_t_ac_exit_sensor(self) -> bool:
        """Check if AC louver exit temperature sensor entity ID is configured."""
        return bool(self.sensor_t_ac_exit and self.sensor_t_ac_exit.strip().lower() not in ("", "none", "null", "unknown", "unavailable"))

    @property
    def has_rh_in_sensor(self) -> bool:
        """Check if indoor humidity sensor entity ID is configured."""
        return bool(self.sensor_rh_in and self.sensor_rh_in.strip().lower() not in ("", "none", "null", "unknown", "unavailable"))

    @property
    def has_rh_out_sensor(self) -> bool:
        """Check if outdoor humidity sensor entity ID is configured."""
        return bool(self.sensor_rh_out and self.sensor_rh_out.strip().lower() not in ("", "none", "null", "unknown", "unavailable"))

    @property
    def has_illuminance_sensor(self) -> bool:
        """Check if illuminance sensor entity ID is configured."""
        return bool(self.sensor_illuminance and self.sensor_illuminance.strip().lower() not in ("", "none", "null", "unknown", "unavailable"))

    @property
    def has_wind_speed_sensor(self) -> bool:
        """Check if wind speed sensor entity ID is configured."""
        return bool(self.sensor_wind_speed and self.sensor_wind_speed.strip().lower() not in ("", "none", "null", "unknown", "unavailable"))

    @property
    def has_wind_dir_sensor(self) -> bool:
        """Check if wind direction sensor entity ID is configured."""
        return bool(self.sensor_wind_direction and self.sensor_wind_direction.strip().lower() not in ("", "none", "null", "unknown", "unavailable"))

    async def async_start(self) -> None:
        """Start listening to input state changes, interval timer, and midnight reset."""
        tracked_entities = [
            entity for entity in [
                self.sensor_t_in,
                self.sensor_t_out,
                self.sensor_t_ac_exit,
                self.sensor_rh_in,
                self.sensor_rh_out,
                self.sensor_solar,
                self.sensor_weather,
                self.sensor_ac_power,
                self.sensor_window,
                self.sensor_illuminance,
                self.sensor_wind_speed,
                self.sensor_wind_direction,
                self.sensor_climate,
                "sun.sun",
            ] if entity
        ]

        if tracked_entities:
            unsub_state = async_track_state_change_event(
                self.hass, tracked_entities, self._async_handle_state_change
            )
            self._unsub_track.append(unsub_state)

        unsub_midnight = async_track_time_change(
            self.hass, self._async_handle_midnight_reset, hour=0, minute=0, second=0
        )
        self._unsub_track.append(unsub_midnight)

        unsub_interval = async_track_time_interval(
            self.hass, self._async_handle_periodic_update, timedelta(seconds=30)
        )
        self._unsub_track.append(unsub_interval)

        # Initial calculation
        self._read_initial_states()
        self.recalculate()

    async def async_stop(self) -> None:
        """Stop tracking events."""
        for unsub in self._unsub_track:
            unsub()
        self._unsub_track.clear()

    @callback
    def _read_initial_states(self) -> None:
        """Read initial state of sensors from Hass state machine."""
        self.t_in_val = self._get_float_state(self.sensor_t_in, 20.0)
        self.t_out_val = self._get_float_state(self.sensor_t_out, 20.0)
        self.t_ac_exit_val = self._get_float_state(self.sensor_t_ac_exit, self.t_in_val)
        self.rh_in_val = self._get_float_state(self.sensor_rh_in, 50.0)
        self.rh_out_val = self._get_float_state(self.sensor_rh_out, 60.0)
        self.solar_val = self._get_float_state(self.sensor_solar, 0.0)
        self.ac_power_val = self._get_float_state(self.sensor_ac_power, 0.0)

        if self.has_window_sensor:
            self.window_is_open = self._get_bool_state(self.sensor_window, False)
        else:
            self.window_is_open = (self.ac_power_val < 20.0)

        if self.has_illuminance_sensor:
            self.illuminance_val = self._get_float_state(self.sensor_illuminance, 500.0)
            self.curtains_closed = (self.illuminance_val < self.illuminance_threshold)

        if self.has_wind_speed_sensor:
            state = self.hass.states.get(self.sensor_wind_speed)
            val = self._get_float_state(self.sensor_wind_speed, 0.0)
            if state and state.attributes.get("unit_of_measurement", "").lower() in ["km/h", "kmh"]:
                val = val / 3.6
            self.wind_speed_ms = val

        if self.has_wind_dir_sensor:
            self.wind_dir_deg = self._get_float_state(self.sensor_wind_direction, 0.0)

    def _get_float_state(self, entity_id: str, default: float) -> float:
        """Extract float value safely from Home Assistant state machine."""
        if not entity_id:
            return default
        state = self.hass.states.get(entity_id)
        if state is None or state.state in ("unknown", "unavailable"):
            return default
        try:
            return float(state.state)
        except (ValueError, TypeError):
            return default

    def _get_bool_state(self, entity_id: str, default: bool) -> bool:
        """Extract binary state safely from Home Assistant state machine."""
        if not entity_id:
            return default
        state = self.hass.states.get(entity_id)
        if state is None or state.state in ("unknown", "unavailable"):
            return default
        return state.state.lower() in ("on", "true", "1")

    @callback
    def _async_handle_state_change(self, event: Event) -> None:
        """Handle state change event for tracked sensors."""
        entity_id = event.data.get("entity_id")
        new_state = event.data.get("new_state")

        if new_state is None or new_state.state in ("unknown", "unavailable"):
            return

        if entity_id == self.sensor_t_in:
            self.t_in_val = _safe_float(new_state.state, self.t_in_val)
        elif entity_id == self.sensor_t_out:
            self.t_out_val = _safe_float(new_state.state, self.t_out_val)
        elif entity_id == self.sensor_t_ac_exit:
            self.t_ac_exit_val = _safe_float(new_state.state, self.t_ac_exit_val)
        elif entity_id == self.sensor_rh_in:
            self.rh_in_val = _safe_float(new_state.state, self.rh_in_val)
        elif entity_id == self.sensor_rh_out:
            self.rh_out_val = _safe_float(new_state.state, self.rh_out_val)
        elif entity_id == self.sensor_solar:
            self.solar_val = _safe_float(new_state.state, self.solar_val)
        elif entity_id == self.sensor_ac_power:
            self.ac_power_val = _safe_float(new_state.state, self.ac_power_val)
        elif entity_id == self.sensor_window:
            self.window_is_open = new_state.state.lower() in ("on", "true", "1")
        elif entity_id == self.sensor_illuminance:
            self.illuminance_val = _safe_float(new_state.state, self.illuminance_val)
            self.curtains_closed = (self.illuminance_val < self.illuminance_threshold)
        elif entity_id == self.sensor_wind_speed:
            val = _safe_float(new_state.state, 0.0)
            if new_state.attributes.get("unit_of_measurement", "").lower() in ["km/h", "kmh"]:
                val = val / 3.6
            self.wind_speed_ms = val
        elif entity_id == self.sensor_wind_direction:
            self.wind_dir_deg = _safe_float(new_state.state, self.wind_dir_deg)

        self.recalculate()

    @callback
    def _async_handle_periodic_update(self, now: datetime) -> None:
        """Periodically recalculate energy accumulators and states every 30 seconds."""
        self.recalculate()

    @callback
    def _async_handle_midnight_reset(self, now: datetime) -> None:
        """Reset daily energy accumulators at 00:00."""
        _LOGGER.info("Resetting daily thermal balance accumulators at midnight")
        self.daily_heat_absorbed = 0.0
        self.daily_ac_thermal_energy = 0.0
        self.daily_ac_elec_kwh = 0.0
        self.daily_shading_heat_saved_kwh = 0.0
        self.recalculate()

    def recalculate(self) -> None:
        """Perform central calculation using thermodynamic model."""
        now = dt_util.now()

        # Date boundary reset
        if self.last_daily_reset is not None and now.date() != self.last_daily_reset.date():
            self.daily_heat_absorbed = 0.0
            self.daily_ac_thermal_energy = 0.0
            self.daily_ac_elec_kwh = 0.0
            self.daily_shading_heat_saved_kwh = 0.0

        self.last_daily_reset = now

        # Window state check
        if self.has_window_sensor:
            self.window_is_open = self._get_bool_state(self.sensor_window, False)
        else:
            self.window_is_open = (self.ac_power_val < 20.0)

        # Daylight and Solar Position (Safe check for sun.sun)
        is_sun_above_horizon = False
        sun_elevation = 0.0
        sun_azimuth = 180.0
        has_sun_position = False
        sun_state = self.hass.states.get("sun.sun")
        if sun_state is not None:
            sun_elevation = _safe_float(sun_state.attributes.get("elevation"), 0.0)
            sun_azimuth = _safe_float(sun_state.attributes.get("azimuth"), 180.0)
            has_sun_position = True
            if sun_state.state == "above_horizon" or sun_elevation > 0.0:
                is_sun_above_horizon = True

        # Solar Irradiance: physical sensor OR clear-sky + weather cloud cover model
        cloud_coverage_pct = 0.0
        if self.has_weather_sensor:
            w_state = self.hass.states.get(self.sensor_weather)
            if w_state is not None and w_state.state not in ("unknown", "unavailable"):
                if "cloud_coverage" in w_state.attributes:
                    try:
                        cloud_coverage_pct = float(w_state.attributes["cloud_coverage"])
                    except (ValueError, TypeError):
                        pass
                else:
                    cond = str(w_state.state).lower()
                    if cond in ("sunny", "clear-night", "clear"):
                        cloud_coverage_pct = 0.0
                    elif cond in ("partlycloudy", "windy", "windy-variant"):
                        cloud_coverage_pct = 40.0
                    elif cond in ("cloudy", "fog"):
                        cloud_coverage_pct = 80.0
                    elif cond in ("rainy", "pouring", "lightning", "lightning-rainy", "snowy", "snowy-rainy", "hail"):
                        cloud_coverage_pct = 95.0

        if not self.has_solar_sensor:
            self.solar_val = estimate_solar_irradiance(sun_elevation, cloud_coverage_pct)
        else:
            s_state = self.hass.states.get(self.sensor_solar)
            if s_state is not None and s_state.state not in ("unknown", "unavailable"):
                try:
                    self.solar_val = max(0.0, float(s_state.state))
                except (ValueError, TypeError):
                    self.solar_val = estimate_solar_irradiance(sun_elevation, cloud_coverage_pct)
            else:
                self.solar_val = estimate_solar_irradiance(sun_elevation, cloud_coverage_pct)

        is_daylight = (self.solar_val > 10.0) or is_sun_above_horizon

        if self.has_illuminance_sensor and is_daylight:
            self.curtains_closed = (self.illuminance_val < self.illuminance_threshold)
        else:
            self.curtains_closed = False

        if not self.has_illuminance_sensor:
            self.curtains_note = "Illuminance sensor not configured"
        elif not is_daylight:
            self.curtains_note = "Night: auto curtain detection disabled (lux threshold not applied)"
        else:
            self.curtains_note = None

        # Determine active heating vs cooling state
        if self.hvac_mode == HVAC_MODE_HEATING:
            self.is_heating = True
        elif self.hvac_mode == HVAC_MODE_COOLING:
            self.is_heating = False
        else:  # AUTO mode
            if self.sensor_climate:
                climate_state = self.hass.states.get(self.sensor_climate)
                if climate_state is not None and climate_state.state not in ("unknown", "unavailable"):
                    action = str(climate_state.attributes.get("hvac_action", "")).lower()
                    state = str(climate_state.state).lower()
                    if action in ("heating", "heat") or state in ("heat", "heating"):
                        self.is_heating = True
                    elif action in ("cooling", "cool") or state in ("cool", "cooling"):
                        self.is_heating = False
                    else:
                        self.is_heating = (self.t_out_val < 16.0 and self.t_out_val < self.t_in_val)
                else:
                    self.is_heating = (self.t_out_val < 16.0 and self.t_out_val < self.t_in_val)
            else:
                self.is_heating = (self.t_out_val < 16.0 and self.t_out_val < self.t_in_val)

        # Build thermodynamic inputs
        inputs = ThermodynamicInputs(
            t_in=self.t_in_val,
            t_out=self.t_out_val,
            solar_irradiance=self.solar_val,
            ac_power=self.ac_power_val,
            t_ac_exit=self.t_ac_exit_val if self.has_t_ac_exit_sensor else None,
            rh_in=self.rh_in_val,
            rh_out=self.rh_out_val,
            window_is_open=self.window_is_open,
            curtains_closed=self.curtains_closed,
            curtain_type=self.curtain_type,
            wind_speed_ms=self.wind_speed_ms,
            wind_dir_deg=self.wind_dir_deg,
            window_azimuth=self.window_azimuth,
            sun_elevation_deg=sun_elevation,
            sun_azimuth_deg=sun_azimuth,
            is_heating=self.is_heating,
            hvac_mode=self.hvac_mode,
            has_rh_in=self.has_rh_in_sensor,
            has_rh_out=self.has_rh_out_sensor,
            has_t_ac_exit=self.has_t_ac_exit_sensor,
            has_wind_speed=self.has_wind_speed_sensor,
            has_wind_dir=self.has_wind_dir_sensor,
            has_sun_position=has_sun_position,
        )

        # Calculate dynamic derivative dT/dt in °C/hour
        self.dt_dt_c_per_h = self._calculate_t_in_derivative(now)

        # Dynamic Empirical K-Factor Estimation with thermal inertia correction
        if not self.window_is_open and self.ac_power_val >= 50.0:
            ac_perf_quick = calculate_thermal_balance(
                self.geometry, inputs, self.ac_max_cooling, self.ac_airflow, self.hlc_closed
            )
            p_hvac = ac_perf_quick.p_heating if self.is_heating else ac_perf_quick.p_cooling_sensible

            k_instant, p_storage, p_wall_dyn = calculate_dynamic_k_factor(
                t_in=self.t_in_val,
                t_out=self.t_out_val,
                p_hvac=p_hvac,
                p_solar=ac_perf_quick.p_solar,
                c_total=self.geometry.c_total,
                dt_dt_c_per_h=self.dt_dt_c_per_h,
                hlc_theoretical=self.geometry.hlc_theoretical,
                is_heating=self.is_heating,
            )
            self.p_storage_w = p_storage
            self.p_wall_dynamic_w = p_wall_dyn

            if k_instant is not None:
                alpha = 0.02 if self._k_samples_count > 50 else 0.05
                self.empirical_k_val = (1.0 - alpha) * self.empirical_k_val + alpha * k_instant
                self._k_samples_count += 1
        else:
            self.p_storage_w = self.geometry.c_total * self.dt_dt_c_per_h
            self.p_wall_dynamic_w = 0.0

        self.empirical_k_val = max(0.5 * self.geometry.hlc_theoretical, min(2.0 * self.geometry.hlc_theoretical, self.empirical_k_val))
        if self.use_empirical_hlc and self._k_samples_count >= 5:
            self.hlc_closed = self.empirical_k_val
        else:
            self.hlc_closed = self.geometry.hlc_theoretical

        dev_pct = ((self.empirical_k_val - self.geometry.hlc_theoretical) / max(0.1, self.geometry.hlc_theoretical)) * 100.0
        if dev_pct <= 15.0:
            insulation_grade = "Excellent (passport)"
        elif dev_pct <= 35.0:
            insulation_grade = "Good (moderate)"
        elif dev_pct <= 65.0:
            insulation_grade = "Average (thermal bridges)"
        else:
            insulation_grade = "Poor (drafts)"

        # Run complete calculation
        result: ThermalCalculationResult = calculate_thermal_balance(
            self.geometry,
            inputs,
            self.ac_max_cooling,
            self.ac_airflow,
            self.hlc_closed,
        )

        # Bounded Energy Integration (max 60 seconds per step to prevent sleeping/offline spikes)
        if self.last_update_time is not None:
            delta_sec = (now - self.last_update_time).total_seconds()
            if delta_sec > 0:
                clamped_sec = min(delta_sec, 60.0)
                delta_hours = clamped_sec / 3600.0

                e_heat_new = (result.p_env * delta_hours) / 1000.0
                e_hvac_new = (result.p_hvac_output * delta_hours) / 1000.0
                e_ac_elec_new = (self.ac_power_val * delta_hours) / 1000.0

                incident_solar_w = (result.p_solar / max(0.01, result.curtain_g_factor)) if result.curtain_g_factor > 0 else 0.0
                p_solar_saved = (incident_solar_w * result.curtain_saved_fraction) if self.curtains_closed else 0.0
                e_shading_saved_new = (p_solar_saved * delta_hours) / 1000.0

                self.total_heat_absorbed += e_heat_new
                self.ac_thermal_energy_total += e_hvac_new
                self.daily_heat_absorbed += e_heat_new
                self.daily_ac_thermal_energy += e_hvac_new
                self.daily_ac_elec_kwh += e_ac_elec_new
                self.daily_shading_heat_saved_kwh += e_shading_saved_new

        self.last_update_time = now

        daily_balance = self.daily_heat_absorbed - self.daily_ac_thermal_energy
        net_balance = self.total_heat_absorbed - self.ac_thermal_energy_total

        # Financial cost calculations
        ac_energy_cost = self.daily_ac_elec_kwh * self.electricity_rate
        cop_for_calc = result.cop if result.cop > 0 else 3.2
        shading_saved_elec_kwh = self.daily_shading_heat_saved_kwh / max(1.0, cop_for_calc)
        shading_daily_savings = shading_saved_elec_kwh * self.electricity_rate

        # Smart advice & recommendations
        rec_open_window = bool((self.t_out_val < self.t_in_val - 1.0) and (self.t_in_val >= 22.0) and not self.window_is_open and not self.is_heating)
        rec_close_curtains = bool(
            is_daylight
            and ((result.p_solar_direct > 50.0) or (result.p_solar > 100.0) or (self.solar_val >= 200.0 and result.sun_is_direct))
            and not self.curtains_closed
            and not self.is_heating
        )

        # Store output states
        self.data = {
            SENSOR_INSTANT_HEAT_GAIN: round(result.p_gain, 2),
            SENSOR_AC_HEAT_OUTPUT: round(result.p_hvac_output, 2),
            SENSOR_INSTANT_NET_BALANCE: round(result.p_net, 2),
            SENSOR_AC_CARNOT_COP: round(result.cop, 2),
            SENSOR_TIME_TO_1DEG: round(result.time_to_1deg_min, 1),
            SENSOR_DAILY_THERMAL_BALANCE: round(daily_balance, 3),
            SENSOR_NET_THERMAL_BALANCE: round(net_balance, 3),
            SENSOR_TOTAL_HEAT_ABSORBED: round(self.total_heat_absorbed, 3),
            SENSOR_AC_THERMAL_ENERGY_TOTAL: round(self.ac_thermal_energy_total, 3),
            SENSOR_AC_CONDENSATION_RATE: round(result.condensation_rate_lh, 2),
            SENSOR_EMPIRICAL_K_FACTOR: round(self.empirical_k_val, 2),
            SENSOR_EQUILIBRIUM_TEMPERATURE: round(result.t_equilibrium, 1),
            SENSOR_REQUIRED_AC_POWER: round(result.p_required_hvac, 0),
            SENSOR_AC_ENERGY_COST: round(ac_energy_cost, 2),
            SENSOR_SHADING_DAILY_SAVINGS: round(shading_daily_savings, 2),
            BINARY_SENSOR_RECOMMEND_OPEN_WINDOW: rec_open_window,
            BINARY_SENSOR_RECOMMEND_CLOSE_CURTAINS: rec_close_curtains,
            BINARY_SENSOR_INSUFFICIENT_COOLING_CAPACITY: bool(result.is_capacity_insufficient),
        }

        # Extra attributes
        self.extra_attributes = {
            SENSOR_INSTANT_HEAT_GAIN: {
                "p_solar_w": round(result.p_solar, 1),
                "p_solar_direct_w": round(result.p_solar_direct, 1),
                "p_solar_diffuse_w": round(result.p_solar_diffuse, 1),
                "solar_aoi_deg": round(result.solar_aoi_deg, 1) if result.solar_aoi_deg is not None else None,
                "solar_cos_aoi": round(result.solar_cos_aoi, 3),
                "sun_is_direct_to_window": result.sun_is_direct,
                "sun_elevation_deg": round(sun_elevation, 1) if has_sun_position else None,
                "sun_azimuth_deg": round(sun_azimuth, 1) if has_sun_position else None,
                "p_wall_w": round(result.p_wall, 1),
                "p_trans_w": round(result.p_trans, 1),
                "p_vent_w": round(result.p_vent, 1),
                "p_env_w": round(result.p_env, 1),
                "hlc_w_k": round(result.hlc_total, 2),
                "window_is_open": self.window_is_open,
                "window_mode": "sensor" if self.has_window_sensor else ("auto (ac off = open)" if self.window_is_open else "auto (ac on = closed)"),
                "curtains_closed": self.curtains_closed,
                "curtains_state": "Closed" if self.curtains_closed else "Open",
                "curtains_note": self.curtains_note,
                "curtain_type": self.curtain_type,
                "curtain_saved_percent": int(round(result.curtain_saved_fraction * 100)),
                "curtain_glass_reduce_percent": int(round((0.70 - result.curtain_g_factor) / 0.70 * 100)),
                "illuminance_lux": round(self.illuminance_val, 1) if self.has_illuminance_sensor else None,
                "g_solar_factor": result.curtain_g_factor,
                "wind_speed_ms": round(self.wind_speed_ms, 2) if self.has_wind_speed_sensor else None,
                "wind_dir_deg": round(self.wind_dir_deg, 1) if self.has_wind_dir_sensor else None,
                "window_azimuth": round(self.window_azimuth, 1),
                "ventilation_ach": round(result.ventilation_ach, 2),
            },
            SENSOR_INSTANT_NET_BALANCE: {
                "p_env_w": round(result.p_env, 1),
                "p_cooling_w": round(result.p_cooling, 1),
                "p_heating_w": round(result.p_heating, 1),
                "p_hvac_output_w": round(result.p_hvac_output, 1),
                "p_wall_w": round(result.p_wall, 1),
                "p_vent_w": round(result.p_vent, 1),
                "hlc_w_k": round(result.hlc_total, 2),
                "window_is_open": self.window_is_open,
                "is_heating": self.is_heating,
                "hvac_mode": self.hvac_mode,
            },
            SENSOR_TIME_TO_1DEG: {
                "direction": result.direction,
                "direction_text": result.direction_text,
            },
            SENSOR_AC_HEAT_OUTPUT: {
                "is_heating": self.is_heating,
                "hvac_mode": self.hvac_mode,
                "mode": "heating" if self.is_heating else "cooling",
                "p_heating_w": round(result.p_heating, 1),
                "p_cooling_w": round(result.p_cooling, 1),
                "delta_t_ac_c": round(result.ac_performance.delta_t_ac, 1),
                "ac_exit_temperature_c": round(result.ac_performance.t_ac_exit, 1),
                "ac_calc_exit_temperature_c": round(result.ac_performance.t_ac_exit_calc, 1),
                "sensible_cooling_w": round(result.p_cooling_sensible, 1),
                "latent_cooling_w": round(result.p_cooling_latent, 1),
                "shr_percent": round(result.ac_performance.shr * 100, 1),
                "indoor_dew_point_c": round(result.ac_performance.dew_point_in, 1) if result.ac_performance.dew_point_in is not None else None,
                "outdoor_dew_point_c": round(result.ac_performance.dew_point_out, 1) if result.ac_performance.dew_point_out is not None else None,
                "air_enthalpy_in_kj_kg": round(result.ac_performance.enthalpy_in_kj_kg, 2),
                "ac_airflow_m3h": round(self.ac_airflow, 1),
                "has_measured_exit_sensor": self.has_t_ac_exit_sensor,
            },
            SENSOR_DAILY_THERMAL_BALANCE: {
                "daily_heat_absorbed": round(self.daily_heat_absorbed, 3),
                "daily_ac_thermal_energy": round(self.daily_ac_thermal_energy, 3),
                "daily_ac_elec_kwh": round(self.daily_ac_elec_kwh, 3),
                "daily_shading_heat_saved_kwh": round(self.daily_shading_heat_saved_kwh, 3),
            },
            SENSOR_NET_THERMAL_BALANCE: {
                "total_heat_absorbed": round(self.total_heat_absorbed, 3),
                "ac_thermal_energy_total": round(self.ac_thermal_energy_total, 3),
            },
            SENSOR_EMPIRICAL_K_FACTOR: {
                "theoretical_hlc_w_k": round(self.geometry.hlc_theoretical, 2),
                "active_hlc_w_k": round(self.hlc_closed, 2),
                "deviation_percent": round(dev_pct, 1),
                "insulation_grade": insulation_grade,
                "auto_calibrated": self.use_empirical_hlc and self._k_samples_count >= 5,
                "samples_count": self._k_samples_count,
                "dt_dt_c_per_h": round(self.dt_dt_c_per_h, 3),
                "p_storage_w": round(self.p_storage_w, 1),
                "p_wall_dynamic_w": round(self.p_wall_dynamic_w, 1),
            },
        }

        # Notify all CoordinatorEntity instances
        self.async_set_updated_data(self.data)
