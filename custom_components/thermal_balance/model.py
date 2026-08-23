"""Pure Python thermodynamic model for Thermal Balance integration."""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any

# Shading factors: (transmittance factor when closed, saved fraction of incident solar)
CURTAIN_TYPE_FACTORS: dict[str, tuple[float, float]] = {
    "roller_gaps": (0.18, 0.52),  # Indoor roller blinds with gaps (blocks 74% window heat / 52% total solar)
    "blackout": (0.05, 0.65),     # Sealed blackout curtains (blocks 93% window heat / 65% total solar)
    "standard": (0.20, 0.50),     # Standard curtains (blocks 71% window heat / 50% total solar)
    "blinds": (0.35, 0.35),       # Light blinds / sheers (blocks 50% window heat / 35% total solar)
    "external": (0.00, 0.70),     # External roller shutters (blocks 100% window heat / 70% total solar)
}


def calculate_dew_point(t_c: float, rh: float) -> float:
    """Calculate dew point in Celsius using Magnus-Tetens formula."""
    if rh <= 0:
        return t_c
    rh_clamped = max(1.0, min(100.0, rh))
    alpha = ((17.27 * t_c) / (237.7 + t_c)) + math.log(rh_clamped / 100.0)
    return (237.7 * alpha) / (17.27 - alpha)


def calculate_humidity_ratio(t_c: float, rh: float, p_kpa: float = 101.325) -> float:
    """Calculate humidity ratio W (kg water / kg dry air)."""
    rh_clamped = max(1.0, min(100.0, rh))
    p_ws = 0.61078 * math.exp((17.27 * t_c) / (t_c + 237.3))  # kPa
    p_w = (rh_clamped / 100.0) * p_ws  # kPa
    if p_kpa <= p_w:
        return 0.0
    return 0.622 * (p_w / (p_kpa - p_w))


def calculate_enthalpy(t_c: float, rh: float, p_kpa: float = 101.325) -> float:
    """Calculate moist air specific enthalpy h (kJ/kg dry air)."""
    w = calculate_humidity_ratio(t_c, rh, p_kpa)
    return 1.006 * t_c + w * (2501.0 + 1.86 * t_c)


@dataclass(frozen=True)
class RoomGeometry:
    """Room geometric and physical parameters."""

    room_area: float
    ceiling_height: float
    window_area: float
    external_walls_fraction: float
    u_wall: float
    u_window: float

    @property
    def volume(self) -> float:
        """Room air volume in m³."""
        return self.room_area * self.ceiling_height

    @property
    def c_air(self) -> float:
        """Thermal capacity of air in W·h/K."""
        return 0.336 * self.volume

    @property
    def c_mass(self) -> float:
        """Thermal capacity of walls/furniture mass in W·h/K."""
        return self.room_area * 40.0

    @property
    def c_total(self) -> float:
        """Total room thermal capacity in W·h/K."""
        return self.c_air + self.c_mass

    @property
    def a_wall(self) -> float:
        """External wall surface area in m²."""
        total_external = (4.0 * math.sqrt(max(0.1, self.room_area)) * self.ceiling_height) * self.external_walls_fraction
        return max(0.0, total_external - self.window_area)

    @property
    def hlc_theoretical(self) -> float:
        """Theoretical Heat Loss Coefficient in W/K."""
        return (self.a_wall * self.u_wall) + (self.window_area * self.u_window)


@dataclass
class ThermodynamicInputs:
    """Dynamic sensor inputs for thermal calculations."""

    t_in: float
    t_out: float
    solar_irradiance: float
    ac_power: float
    t_ac_exit: float | None = None
    rh_in: float = 50.0
    rh_out: float = 60.0
    window_is_open: bool = False
    curtains_closed: bool = False
    curtain_type: str = "roller_gaps"
    wind_speed_ms: float = 0.0
    wind_dir_deg: float = 0.0
    window_azimuth: float = 0.0
    has_rh_in: bool = False
    has_rh_out: bool = False
    has_t_ac_exit: bool = False
    has_wind_speed: bool = False
    has_wind_dir: bool = False


@dataclass
class ACPerformanceResult:
    """AC cooling performance metrics."""

    p_cooling: float
    p_cooling_sensible: float
    p_cooling_latent: float
    cop: float
    shr: float
    condensation_rate_lh: float
    t_ac_exit: float
    t_ac_exit_calc: float
    delta_t_ac: float
    dew_point_in: float | None
    dew_point_out: float | None
    enthalpy_in_kj_kg: float


@dataclass
class ThermalCalculationResult:
    """Full thermal balance state result."""

    p_env: float
    p_gain: float
    p_wall: float
    p_vent: float
    p_trans: float
    p_solar: float
    p_cooling: float
    p_cooling_sensible: float
    p_cooling_latent: float
    p_net: float
    p_net_sensible: float
    cop: float
    time_to_1deg_min: float
    direction: str
    direction_text: str
    hlc_total: float
    hlc_closed: float
    hlc_vent: float
    ventilation_ach: float
    condensation_rate_lh: float
    ac_performance: ACPerformanceResult
    curtain_g_factor: float
    curtain_saved_fraction: float


def calculate_ac_performance(
    inputs: ThermodynamicInputs,
    ac_max_cooling: float,
    ac_airflow_m3h: float,
) -> ACPerformanceResult:
    """Calculate AC cooling output, COP, psychrometrics and sensible/latent split."""
    dew_point_in = calculate_dew_point(inputs.t_in, inputs.rh_in) if inputs.has_rh_in else None
    dew_point_out = calculate_dew_point(inputs.t_out, inputs.rh_out) if inputs.has_rh_out else None
    h_in_kj_kg = calculate_enthalpy(inputs.t_in, inputs.rh_in)
    w_in = calculate_humidity_ratio(inputs.t_in, inputs.rh_in)
    air_mass_flow = 1.20 * (ac_airflow_m3h / 3600.0)

    if inputs.ac_power < 20.0:
        return ACPerformanceResult(
            p_cooling=0.0,
            p_cooling_sensible=0.0,
            p_cooling_latent=0.0,
            cop=0.0,
            shr=0.0,
            condensation_rate_lh=0.0,
            t_ac_exit=inputs.t_in,
            t_ac_exit_calc=inputs.t_in,
            delta_t_ac=0.0,
            dew_point_in=dew_point_in,
            dew_point_out=dew_point_out,
            enthalpy_in_kj_kg=h_in_kj_kg,
        )

    # Theoretical Carnot and empirical COP model
    cop_carnot = (inputs.t_in + 273.15) / (abs(inputs.t_out - inputs.t_in) + 1.0)
    cop_model = max(1.0, min(5.0, cop_carnot * 0.35))
    p_cooling_model = inputs.ac_power * cop_model

    if air_mass_flow > 0:
        delta_h_model = p_cooling_model / (1000.0 * air_mass_flow)
        h_exit_model = h_in_kj_kg - delta_h_model
        t_ac_exit_calc = (h_exit_model - (2501.0 * w_in)) / (1.006 + 1.86 * w_in)
        t_ac_exit_calc = max(4.0, min(inputs.t_in, t_ac_exit_calc))
    else:
        t_ac_exit_calc = inputs.t_in

    if inputs.has_t_ac_exit and inputs.t_ac_exit is not None:
        t_ac_exit = inputs.t_ac_exit
        delta_t_ac = max(0.0, inputs.t_in - t_ac_exit)
        h_exit_measured = calculate_enthalpy(t_ac_exit, inputs.rh_in)
        delta_h = max(0.0, h_in_kj_kg - h_exit_measured)
        p_cooling_raw = air_mass_flow * delta_h * 1000.0
    else:
        t_ac_exit = t_ac_exit_calc
        p_cooling_raw = p_cooling_model
        delta_t_ac = max(0.0, inputs.t_in - t_ac_exit)

    p_cooling = min(ac_max_cooling, p_cooling_raw)
    cop_real = (p_cooling / inputs.ac_power) if inputs.ac_power > 0 else 0.0

    # Sensible Heat Ratio (SHR)
    if inputs.has_rh_in:
        shr = max(0.65, min(1.0, 1.0 - 0.008 * (inputs.rh_in - 35.0)))
    else:
        shr = 0.85

    p_cooling_sensible = p_cooling * shr
    p_cooling_latent = p_cooling * (1.0 - shr)
    condensation_rate_lh = p_cooling_latent / 627.8  # 1L water = 2260 kJ = 627.8 W·h

    return ACPerformanceResult(
        p_cooling=p_cooling,
        p_cooling_sensible=p_cooling_sensible,
        p_cooling_latent=p_cooling_latent,
        cop=cop_real,
        shr=shr,
        condensation_rate_lh=condensation_rate_lh,
        t_ac_exit=t_ac_exit,
        t_ac_exit_calc=t_ac_exit_calc,
        delta_t_ac=delta_t_ac,
        dew_point_in=dew_point_in,
        dew_point_out=dew_point_out,
        enthalpy_in_kj_kg=h_in_kj_kg,
    )


def calculate_thermal_balance(
    geometry: RoomGeometry,
    inputs: ThermodynamicInputs,
    ac_max_cooling: float,
    ac_airflow_m3h: float,
    active_hlc_closed: float | None = None,
) -> ThermalCalculationResult:
    """Execute full thermodynamics model calculations."""
    hlc_closed = active_hlc_closed if active_hlc_closed is not None else geometry.hlc_theoretical

    # 1. Curtain / Shading Factors
    curtain_factors = CURTAIN_TYPE_FACTORS.get(inputs.curtain_type, CURTAIN_TYPE_FACTORS["roller_gaps"])
    curtain_g_factor = curtain_factors[0] if inputs.curtains_closed else 0.70
    curtain_saved_fraction = curtain_factors[1]

    # Solar power entering room
    p_solar = geometry.window_area * max(0.0, inputs.solar_irradiance) * curtain_g_factor

    # 2. Ventilation and wind-driven infiltration
    if inputs.window_is_open:
        base_ach = 1.0
        wind_effect = 0.0
        if inputs.has_wind_speed:
            angle_diff = abs(inputs.wind_dir_deg - inputs.window_azimuth) % 360
            if angle_diff > 180:
                angle_diff = 360 - angle_diff
            cos_factor = math.cos(math.radians(angle_diff))
            if cos_factor > 0:
                wind_effect = inputs.wind_speed_ms * 1.5 * cos_factor
        current_ach = base_ach + wind_effect
        hlc_vent = current_ach * geometry.volume * 0.336
    else:
        current_ach = 0.0
        hlc_vent = 0.0

    hlc_total = hlc_closed + hlc_vent

    # 3. Transmission and environmental heat fluxes
    delta_t = inputs.t_out - inputs.t_in
    p_wall = hlc_closed * delta_t
    p_vent = hlc_vent * delta_t if inputs.window_is_open else 0.0
    p_trans = p_wall + p_vent
    p_env = p_trans + p_solar
    p_gain = p_env

    # 4. AC Cooling calculations
    ac_perf = calculate_ac_performance(inputs, ac_max_cooling, ac_airflow_m3h)

    # 5. Net Power Balance
    p_net = p_env - ac_perf.p_cooling
    p_net_sensible = p_env - ac_perf.p_cooling_sensible

    # 6. Time to 1 deg C change
    if p_net_sensible > 20.0:
        time_to_1deg_min = (geometry.c_total / p_net_sensible) * 60.0
        direction = "heating"
        direction_text = "Heating (+1°C)"
    elif p_net_sensible < -20.0:
        time_to_1deg_min = (geometry.c_total / abs(p_net_sensible)) * 60.0
        direction = "cooling"
        direction_text = "Cooling (-1°C)"
    else:
        time_to_1deg_min = 0.0
        direction = "equilibrium"
        direction_text = "Equilibrium"

    return ThermalCalculationResult(
        p_env=p_env,
        p_gain=p_gain,
        p_wall=p_wall,
        p_vent=p_vent,
        p_trans=p_trans,
        p_solar=p_solar,
        p_cooling=ac_perf.p_cooling,
        p_cooling_sensible=ac_perf.p_cooling_sensible,
        p_cooling_latent=ac_perf.p_cooling_latent,
        p_net=p_net,
        p_net_sensible=p_net_sensible,
        cop=ac_perf.cop,
        time_to_1deg_min=time_to_1deg_min,
        direction=direction,
        direction_text=direction_text,
        hlc_total=hlc_total,
        hlc_closed=hlc_closed,
        hlc_vent=hlc_vent,
        ventilation_ach=current_ach,
        condensation_rate_lh=ac_perf.condensation_rate_lh,
        ac_performance=ac_perf,
        curtain_g_factor=curtain_g_factor,
        curtain_saved_fraction=curtain_saved_fraction,
    )
