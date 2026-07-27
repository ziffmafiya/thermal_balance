"""Coordinator for Thermal Balance custom component."""
from datetime import datetime
import logging
import math
from typing import Any, Dict, Optional

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_change
from homeassistant.util import dt as dt_util

from .const import (
    CONF_AC_AIRFLOW,
    CONF_AC_MAX_COOLING,
    CONF_CEILING_HEIGHT,
    CONF_EXTERNAL_WALLS_FRACTION,
    CONF_ROOM_AREA,
    CONF_SENSOR_AC_POWER,
    CONF_SENSOR_RH_IN,
    CONF_SENSOR_RH_OUT,
    CONF_SENSOR_SOLAR,
    CONF_SENSOR_T_AC_EXIT,
    CONF_SENSOR_T_IN,
    CONF_SENSOR_T_OUT,
    CONF_SENSOR_WINDOW,
    CONF_U_WALL,
    CONF_U_WINDOW,
    CONF_WINDOW_AREA,
    DEFAULT_AC_AIRFLOW,
    DEFAULT_AC_MAX_COOLING,
    DEFAULT_CEILING_HEIGHT,
    DEFAULT_EXTERNAL_WALLS_FRACTION,
    DEFAULT_ROOM_AREA,
    DEFAULT_U_WALL,
    DEFAULT_U_WINDOW,
    DEFAULT_WINDOW_AREA,
    DOMAIN,
    SENSOR_AC_CARNOT_COP,
    SENSOR_AC_CONDENSATION_RATE,
    SENSOR_AC_HEAT_OUTPUT,
    SENSOR_AC_THERMAL_ENERGY_TOTAL,
    SENSOR_DAILY_THERMAL_BALANCE,
    SENSOR_INSTANT_HEAT_GAIN,
    SENSOR_INSTANT_NET_BALANCE,
    SENSOR_NET_THERMAL_BALANCE,
    SENSOR_TIME_TO_1DEG,
    SENSOR_TOTAL_HEAT_ABSORBED,
)

_LOGGER = logging.getLogger(__name__)


def _safe_float(val: Any, default: float) -> float:
    """Safely convert value to float."""
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def _calculate_dew_point(t_c: float, rh: float) -> float:
    """Calculate dew point in Celsius using Magnus-Tetens formula."""
    if rh <= 0:
        return t_c
    rh_clamped = max(1.0, min(100.0, rh))
    alpha = ((17.27 * t_c) / (237.7 + t_c)) + math.log(rh_clamped / 100.0)
    return (237.7 * alpha) / (17.27 - alpha)


def _calculate_humidity_ratio(t_c: float, rh: float, p_kpa: float = 101.325) -> float:
    """Calculate humidity ratio W (kg water / kg dry air)."""
    rh_clamped = max(1.0, min(100.0, rh))
    p_ws = 0.61078 * math.exp((17.27 * t_c) / (t_c + 237.3))  # kPa
    p_w = (rh_clamped / 100.0) * p_ws  # kPa
    if p_kpa <= p_w:
        return 0.0
    return 0.622 * (p_w / (p_kpa - p_w))


def _calculate_enthalpy(t_c: float, rh: float, p_kpa: float = 101.325) -> float:
    """Calculate moist air specific enthalpy h (kJ/kg dry air)."""
    w = _calculate_humidity_ratio(t_c, rh, p_kpa)
    return 1.006 * t_c + w * (2501.0 + 1.86 * t_c)


class ThermalBalanceCoordinator:
    """Coordinator to manage thermodynamic calculations and state tracking."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        self.hass = hass
        self.entry = entry

        # Load parameters (combine data and options)
        options = entry.options
        data = entry.data

        self.room_area: float = _safe_float(options.get(CONF_ROOM_AREA, data.get(CONF_ROOM_AREA)), DEFAULT_ROOM_AREA)
        self.ceiling_height: float = _safe_float(options.get(CONF_CEILING_HEIGHT, data.get(CONF_CEILING_HEIGHT)), DEFAULT_CEILING_HEIGHT)
        self.window_area: float = _safe_float(options.get(CONF_WINDOW_AREA, data.get(CONF_WINDOW_AREA)), DEFAULT_WINDOW_AREA)
        self.external_walls_fraction: float = _safe_float(options.get(CONF_EXTERNAL_WALLS_FRACTION, data.get(CONF_EXTERNAL_WALLS_FRACTION)), DEFAULT_EXTERNAL_WALLS_FRACTION)
        self.ac_max_cooling: float = _safe_float(options.get(CONF_AC_MAX_COOLING, data.get(CONF_AC_MAX_COOLING)), DEFAULT_AC_MAX_COOLING)
        self.ac_airflow: float = _safe_float(options.get(CONF_AC_AIRFLOW, data.get(CONF_AC_AIRFLOW)), DEFAULT_AC_AIRFLOW)
        self.u_wall: float = _safe_float(options.get(CONF_U_WALL, data.get(CONF_U_WALL)), DEFAULT_U_WALL)
        self.u_window: float = _safe_float(options.get(CONF_U_WINDOW, data.get(CONF_U_WINDOW)), DEFAULT_U_WINDOW)

        self.sensor_t_in: str = options.get(CONF_SENSOR_T_IN, data.get(CONF_SENSOR_T_IN, ""))
        self.sensor_t_out: str = options.get(CONF_SENSOR_T_OUT, data.get(CONF_SENSOR_T_OUT, ""))
        self.sensor_t_ac_exit: str = options.get(CONF_SENSOR_T_AC_EXIT, data.get(CONF_SENSOR_T_AC_EXIT, ""))
        self.sensor_rh_in: str = options.get(CONF_SENSOR_RH_IN, data.get(CONF_SENSOR_RH_IN, ""))
        self.sensor_rh_out: str = options.get(CONF_SENSOR_RH_OUT, data.get(CONF_SENSOR_RH_OUT, ""))
        self.sensor_solar: str = options.get(CONF_SENSOR_SOLAR, data.get(CONF_SENSOR_SOLAR, ""))
        self.sensor_ac_power: str = options.get(CONF_SENSOR_AC_POWER, data.get(CONF_SENSOR_AC_POWER, ""))
        self.sensor_window: str = options.get(CONF_SENSOR_WINDOW, data.get(CONF_SENSOR_WINDOW, ""))

        # Pre-calculated static thermal capacity values (Step 1)
        self.volume: float = self.room_area * self.ceiling_height
        self.c_air: float = 0.336 * self.volume
        self.c_mass: float = self.room_area * 40.0
        self.c_total: float = self.c_air + self.c_mass

        # External wall area calculation taking external_walls_fraction into account
        a_total_external = (4.0 * math.sqrt(self.room_area) * self.ceiling_height) * self.external_walls_fraction
        self.a_wall: float = max(0.0, a_total_external - self.window_area)
        self.hlc_closed: float = (self.a_wall * self.u_wall) + (self.window_area * self.u_window)
        self.hlc_vent: float = 4.0 * self.volume * 0.336

        # Air mass flow rate (kg/s)
        self.air_mass_flow_kg_s: float = 1.20 * (self.ac_airflow / 3600.0)

        # State storage
        self.t_in_val: float = 20.0
        self.t_out_val: float = 20.0
        self.t_ac_exit_val: float = 20.0
        self.rh_in_val: float = 50.0
        self.rh_out_val: float = 60.0
        self.solar_val: float = 0.0
        self.ac_power_val: float = 0.0
        self.window_is_open: bool = False

        # Energy accumulators (kWh)
        self.total_heat_absorbed: float = 0.0
        self.ac_thermal_energy_total: float = 0.0
        self.daily_heat_absorbed: float = 0.0
        self.daily_ac_thermal_energy: float = 0.0

        # Timing for integration
        self.last_update_time: Optional[datetime] = None
        self.last_daily_reset: Optional[datetime] = None

        # Output states dictionary
        self.data: Dict[str, float] = {
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
        }

        # Extra attributes dictionary
        self.extra_attributes: Dict[str, Dict[str, Any]] = {
            SENSOR_TIME_TO_1DEG: {
                "direction": "equilibrium",
                "direction_text": "Равновесие",
            },
            SENSOR_AC_HEAT_OUTPUT: {
                "sensible_cooling_w": 0.0,
                "latent_cooling_w": 0.0,
                "shr_percent": 100.0,
            }
        }

        # Registered entity listeners update callback
        self._listeners: list = []
        self._unsub_track: list = []

    @property
    def has_window_sensor(self) -> bool:
        """Check if a valid window binary_sensor entity ID is configured."""
        return bool(
            self.sensor_window
            and isinstance(self.sensor_window, str)
            and self.sensor_window.strip().lower() not in ("", "none", "null", "unknown", "unavailable")
        )

    @property
    def has_t_ac_exit_sensor(self) -> bool:
        """Check if AC louver exit temperature sensor entity ID is configured."""
        return bool(
            self.sensor_t_ac_exit
            and isinstance(self.sensor_t_ac_exit, str)
            and self.sensor_t_ac_exit.strip().lower() not in ("", "none", "null", "unknown", "unavailable")
        )

    @property
    def has_rh_in_sensor(self) -> bool:
        """Check if indoor humidity sensor entity ID is configured."""
        return bool(
            self.sensor_rh_in
            and isinstance(self.sensor_rh_in, str)
            and self.sensor_rh_in.strip().lower() not in ("", "none", "null", "unknown", "unavailable")
        )

    @property
    def has_rh_out_sensor(self) -> bool:
        """Check if outdoor humidity sensor entity ID is configured."""
        return bool(
            self.sensor_rh_out
            and isinstance(self.sensor_rh_out, str)
            and self.sensor_rh_out.strip().lower() not in ("", "none", "null", "unknown", "unavailable")
        )

    def register_listener(self, update_callback) -> None:
        """Register entity update callback."""
        self._listeners.append(update_callback)

    def remove_listener(self, update_callback) -> None:
        """Remove entity update callback."""
        if update_callback in self._listeners:
            self._listeners.remove(update_callback)

    def _notify_listeners(self) -> None:
        """Notify all registered sensor entities of state update."""
        for update_callback in self._listeners:
            update_callback()

    async def async_start(self) -> None:
        """Start listening to input state changes and midnight reset."""
        tracked_entities = [
            entity for entity in [
                self.sensor_t_in,
                self.sensor_t_out,
                self.sensor_t_ac_exit,
                self.sensor_rh_in,
                self.sensor_rh_out,
                self.sensor_solar,
                self.sensor_ac_power,
                self.sensor_window,
            ] if entity
        ]

        if tracked_entities:
            unsub = async_track_state_change_event(
                self.hass, tracked_entities, self._async_handle_state_change
            )
            self._unsub_track.append(unsub)

        # Midnight reset listener (00:00:00)
        unsub_midnight = async_track_time_change(
            self.hass, self._async_handle_midnight_reset, hour=0, minute=0, second=0
        )
        self._unsub_track.append(unsub_midnight)

        # Periodic interval update every 30 seconds
        from datetime import timedelta
        from homeassistant.helpers.event import async_track_time_interval
        unsub_interval = async_track_time_interval(
            self.hass, self._async_handle_periodic_update, timedelta(seconds=30)
        )
        self._unsub_track.append(unsub_interval)

        # Perform initial calculation
        self._read_initial_states()
        self.recalculate()

    async def async_stop(self) -> None:
        """Stop tracking."""
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
            _LOGGER.debug("State for %s is unknown/unavailable, keeping previous values", entity_id)
            return

        if entity_id == self.sensor_t_in:
            self.t_in_val = self._safe_float_val(new_state.state, self.t_in_val)
        elif entity_id == self.sensor_t_out:
            self.t_out_val = self._safe_float_val(new_state.state, self.t_out_val)
        elif entity_id == self.sensor_t_ac_exit:
            self.t_ac_exit_val = self._safe_float_val(new_state.state, self.t_ac_exit_val)
        elif entity_id == self.sensor_rh_in:
            self.rh_in_val = self._safe_float_val(new_state.state, self.rh_in_val)
        elif entity_id == self.sensor_rh_out:
            self.rh_out_val = self._safe_float_val(new_state.state, self.rh_out_val)
        elif entity_id == self.sensor_solar:
            self.solar_val = self._safe_float_val(new_state.state, self.solar_val)
        elif entity_id == self.sensor_ac_power:
            self.ac_power_val = self._safe_float_val(new_state.state, self.ac_power_val)
        elif entity_id == self.sensor_window:
            self.window_is_open = new_state.state.lower() in ("on", "true", "1")

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
        self.recalculate()

    def _safe_float_val(self, value: Any, default: float) -> float:
        """Safely convert value to float."""
        try:
            return float(value)
        except (ValueError, TypeError):
            return default

    def recalculate(self) -> None:
        """Perform central calculation according to the PRD mathematical model."""
        now = dt_util.now()

        # Check date boundary for daily reset if midnight timer was delayed
        if self.last_daily_reset is not None and now.date() != self.last_daily_reset.date():
            self.daily_heat_absorbed = 0.0
            self.daily_ac_thermal_energy = 0.0

        self.last_daily_reset = now

        # Determine window state:
        # If sensor_window is provided, use its state.
        # Otherwise: AC OFF (< 20W) => window OPEN (True), AC ON (>= 20W) => window CLOSED (False).
        if self.has_window_sensor:
            self.window_is_open = self._get_bool_state(self.sensor_window, False)
        else:
            self.window_is_open = (self.ac_power_val < 20.0)

        # Psychrometrics: Dew Point and Enthalpy calculations
        dew_point_in = _calculate_dew_point(self.t_in_val, self.rh_in_val)
        dew_point_out = _calculate_dew_point(self.t_out_val, self.rh_out_val)
        h_in_kj_kg = _calculate_enthalpy(self.t_in_val, self.rh_in_val)
        w_in = _calculate_humidity_ratio(self.t_in_val, self.rh_in_val)

        # Step 2: Heat Loss Coefficient HLC (Transmission + Ventilation when window open)
        hlc = self.hlc_closed + (self.hlc_vent if self.window_is_open else 0.0)

        # Step 3: Instantaneous Powers (Watts)
        # 1. Environmental heat exchange P_env, ventilation heat P_vent, conduction P_wall and Heat Gain P_gain
        p_wall = self.hlc_closed * (self.t_out_val - self.t_in_val)
        p_vent = (self.hlc_vent * (self.t_out_val - self.t_in_val)) if self.window_is_open else 0.0
        p_trans = p_wall + p_vent
        p_solar = self.window_area * self.solar_val * 0.70
        p_env = p_trans + p_solar
        p_gain = max(0.0, p_env)

        # 2. AC Cooling P_cooling and Psychrometric Sensible/Latent Split (SHR)
        if self.ac_power_val < 20.0:
            cop_real = 0.0
            p_cooling = 0.0
            p_cooling_sensible = 0.0
            p_cooling_latent = 0.0
            condensation_rate_lh = 0.0
            shr = 0.0
            t_ac_exit = self.t_in_val
            t_ac_exit_calc = self.t_in_val
            delta_t_ac = 0.0
        else:
            # Calculate theoretical model exit temperature for comparison
            cop_carnot = (self.t_in_val + 273.15) / (abs(self.t_out_val - self.t_in_val) + 1.0)
            cop_model = max(1.0, min(5.0, cop_carnot * 0.35))
            p_cooling_model = self.ac_power_val * cop_model

            if self.air_mass_flow_kg_s > 0:
                delta_h_model = p_cooling_model / (1000.0 * self.air_mass_flow_kg_s)
                h_exit_model = h_in_kj_kg - delta_h_model
                t_ac_exit_calc = (h_exit_model - (2501.0 * w_in)) / (1.006 + 1.86 * w_in)
                t_ac_exit_calc = max(4.0, min(self.t_in_val, t_ac_exit_calc))
            else:
                t_ac_exit_calc = self.t_in_val

            if self.has_t_ac_exit_sensor:
                t_ac_exit = self.t_ac_exit_val
                delta_t_ac = max(0.0, self.t_in_val - t_ac_exit)
                h_exit_measured_kj_kg = _calculate_enthalpy(t_ac_exit, self.rh_in_val)
                # Measured cooling capacity directly from airflow & enthalpy delta
                delta_h = max(0.0, h_in_kj_kg - h_exit_measured_kj_kg)
                p_cooling_raw = self.air_mass_flow_kg_s * delta_h * 1000.0
            else:
                t_ac_exit = t_ac_exit_calc
                cop_real = cop_model
                p_cooling_raw = p_cooling_model
                delta_t_ac = max(0.0, self.t_in_val - t_ac_exit)

            p_cooling = min(self.ac_max_cooling, p_cooling_raw)
            if self.ac_power_val > 0:
                cop_real = p_cooling / self.ac_power_val

            # Sensible Heat Ratio (SHR) calculation
            if self.has_rh_in_sensor:
                shr = max(0.65, min(1.0, 1.0 - 0.008 * (self.rh_in_val - 35.0)))
            else:
                shr = 0.85  # Standard nominal indoor AC SHR

            p_cooling_sensible = p_cooling * shr
            p_cooling_latent = p_cooling * (1.0 - shr)

            # Condensation rate (Liters / Hour): 1 Liter water = 2260 kJ latent heat (627.8 W·h/L)
            condensation_rate_lh = p_cooling_latent / 627.8

        # 3. Net Balance P_net (environmental heat flow minus AC cooling capacity)
        p_net = p_env - p_cooling
        p_net_sensible = p_env - p_cooling_sensible

        # Step 4: Time forecast (time to 1 deg C change in minutes) and Direction
        if p_net_sensible > 20.0:
            t_min = (self.c_total / p_net_sensible) * 60.0
            direction = "heating"
            direction_text = "Нагрев (+1°C)"
        elif p_net_sensible < -20.0:
            t_min = (self.c_total / abs(p_net_sensible)) * 60.0
            direction = "cooling"
            direction_text = "Охлаждение (-1°C)"
        else:
            t_min = 0.0
            direction = "equilibrium"
            direction_text = "Равновесие"

        # Step 5: Energy Integrators (kWh)
        if self.last_update_time is not None:
            delta_sec = (now - self.last_update_time).total_seconds()
            if delta_sec > 0:
                delta_hours = delta_sec / 3600.0
                e_heat_new = (p_gain * delta_hours) / 1000.0
                e_cool_new = (p_cooling * delta_hours) / 1000.0

                self.total_heat_absorbed += e_heat_new
                self.ac_thermal_energy_total += e_cool_new
                self.daily_heat_absorbed += e_heat_new
                self.daily_ac_thermal_energy += e_cool_new

        self.last_update_time = now

        daily_balance = self.daily_heat_absorbed - self.daily_ac_thermal_energy
        net_balance = self.total_heat_absorbed - self.ac_thermal_energy_total

        # Empirical HLC auto-estimation (W/°C) based on daily thermal energy & delta T
        delta_t_abs = abs(self.t_out_val - self.t_in_val)
        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
        daily_hours = max(0.1, (now - midnight).total_seconds() / 3600.0)
        if delta_t_abs >= 0.5 and self.daily_ac_thermal_energy > 0:
            empirical_hlc = (self.daily_ac_thermal_energy * 1000.0) / (delta_t_abs * daily_hours)
        else:
            empirical_hlc = hlc

        # Store calculated metrics
        self.data = {
            SENSOR_INSTANT_HEAT_GAIN: round(p_gain, 2),
            SENSOR_AC_HEAT_OUTPUT: round(p_cooling, 2),
            SENSOR_INSTANT_NET_BALANCE: round(p_net, 2),
            SENSOR_AC_CARNOT_COP: round(cop_real, 2),
            SENSOR_TIME_TO_1DEG: round(t_min, 1),
            SENSOR_DAILY_THERMAL_BALANCE: round(daily_balance, 3),
            SENSOR_NET_THERMAL_BALANCE: round(net_balance, 3),
            SENSOR_TOTAL_HEAT_ABSORBED: round(self.total_heat_absorbed, 3),
            SENSOR_AC_THERMAL_ENERGY_TOTAL: round(self.ac_thermal_energy_total, 3),
            SENSOR_AC_CONDENSATION_RATE: round(condensation_rate_lh, 2),
        }

        # Extra attributes
        self.extra_attributes = {
            SENSOR_INSTANT_HEAT_GAIN: {
                "p_solar_w": round(p_solar, 1),
                "p_wall_w": round(p_wall, 1),
                "p_trans_w": round(p_trans, 1),
                "p_vent_w": round(p_vent, 1),
                "hlc_w_k": round(hlc, 2),
                "window_is_open": self.window_is_open,
                "window_mode": "sensor" if self.has_window_sensor else ("auto (ac off = open)" if self.window_is_open else "auto (ac on = closed)"),
            },
            SENSOR_INSTANT_NET_BALANCE: {
                "p_env_w": round(p_env, 1),
                "p_cooling_w": round(p_cooling, 1),
                "p_wall_w": round(p_wall, 1),
                "p_vent_w": round(p_vent, 1),
                "hlc_w_k": round(hlc, 2),
                "window_is_open": self.window_is_open,
            },
            SENSOR_TIME_TO_1DEG: {
                "direction": direction,
                "direction_text": direction_text,
            },
            SENSOR_AC_HEAT_OUTPUT: {
                "delta_t_ac_c": round(delta_t_ac, 1),
                "ac_exit_temperature_c": round(t_ac_exit, 1),
                "ac_calc_exit_temperature_c": round(t_ac_exit_calc, 1),
                "sensible_cooling_w": round(p_cooling_sensible, 1),
                "latent_cooling_w": round(p_cooling_latent, 1),
                "shr_percent": round(shr * 100, 1),
                "indoor_dew_point_c": round(dew_point_in, 1) if self.has_rh_in_sensor else None,
                "outdoor_dew_point_c": round(dew_point_out, 1) if self.has_rh_out_sensor else None,
                "air_enthalpy_in_kj_kg": round(h_in_kj_kg, 2),
                "ac_airflow_m3h": round(self.ac_airflow, 1),
                "has_measured_exit_sensor": self.has_t_ac_exit_sensor,
            },
            SENSOR_DAILY_THERMAL_BALANCE: {
                "daily_heat_absorbed": round(self.daily_heat_absorbed, 3),
                "daily_ac_thermal_energy": round(self.daily_ac_thermal_energy, 3),
                "theoretical_hlc_w_c": round(hlc, 2),
                "measured_hlc_w_c": round(empirical_hlc, 2),
            },
            SENSOR_NET_THERMAL_BALANCE: {
                "total_heat_absorbed": round(self.total_heat_absorbed, 3),
                "ac_thermal_energy_total": round(self.ac_thermal_energy_total, 3),
            },
        }

        self._notify_listeners()
