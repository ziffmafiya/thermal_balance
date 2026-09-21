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
    sun_elevation_deg: float = 0.0
    sun_azimuth_deg: float = 180.0
    is_heating: bool = False
    hvac_mode: str = "cooling"
    has_rh_in: bool = False
    has_rh_out: bool = False
    has_t_ac_exit: bool = False
    has_wind_speed: bool = False
    has_wind_dir: bool = False
    has_sun_position: bool = False


@dataclass
class ACPerformanceResult:
    """AC cooling/heating performance metrics."""

    p_cooling: float
    p_cooling_sensible: float
    p_cooling_latent: float
    p_heating: float
    cop: float
    shr: float
    condensation_rate_lh: float
    t_ac_exit: float
    t_ac_exit_calc: float
    delta_t_ac: float
    dew_point_in: float | None
    dew_point_out: float | None
    enthalpy_in_kj_kg: float
    is_heating: bool = False


@dataclass
class ThermalCalculationResult:
    """Full thermal balance state result."""

    p_env: float
    p_gain: float
    p_wall: float
    p_vent: float
    p_trans: float
    p_solar: float
    p_solar_direct: float
    p_solar_diffuse: float
    solar_aoi_deg: float | None
    solar_cos_aoi: float
    sun_is_direct: bool
    p_cooling: float
    p_cooling_sensible: float
    p_cooling_latent: float
    p_heating: float
    p_hvac_output: float
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
    is_heating: bool = False
    hvac_mode: str = "cooling"
    t_equilibrium: float = 20.0
    p_required_hvac: float = 0.0
    is_capacity_insufficient: bool = False
    p_loss: float = 0.0


def calculate_ac_performance(
    inputs: ThermodynamicInputs,
    ac_max_cooling: float,
    ac_airflow_m3h: float,
) -> ACPerformanceResult:
    """Calculate AC cooling/heating output, COP, psychrometrics and sensible/latent split."""
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
            p_heating=0.0,
            cop=0.0,
            shr=0.0 if not inputs.is_heating else 1.0,
            condensation_rate_lh=0.0,
            t_ac_exit=inputs.t_in,
            t_ac_exit_calc=inputs.t_in,
            delta_t_ac=0.0,
            dew_point_in=dew_point_in,
            dew_point_out=dew_point_out,
            enthalpy_in_kj_kg=h_in_kj_kg,
            is_heating=inputs.is_heating,
        )

    if inputs.is_heating:
        # Heating mode (Heat pump / reverse cycle)
        # COP for heating: Carnot COP = (T_in + 273.15) / (max(1.0, T_in - T_out) + 1.0)
        temp_delta = max(1.0, inputs.t_in - inputs.t_out)
        cop_carnot_h = (inputs.t_in + 273.15) / (temp_delta + 1.0)
        cop_model_h = max(1.2, min(5.5, cop_carnot_h * 0.38))
        p_heating_model = inputs.ac_power * cop_model_h

        if air_mass_flow > 0:
            delta_h_model = p_heating_model / (1000.0 * air_mass_flow)
            h_exit_model = h_in_kj_kg + delta_h_model
            t_ac_exit_calc = (h_exit_model - (2501.0 * w_in)) / (1.006 + 1.86 * w_in)
            t_ac_exit_calc = max(inputs.t_in, min(60.0, t_ac_exit_calc))
        else:
            t_ac_exit_calc = inputs.t_in

        if inputs.has_t_ac_exit and inputs.t_ac_exit is not None:
            t_ac_exit = inputs.t_ac_exit
            delta_t_ac = max(0.0, t_ac_exit - inputs.t_in)
            h_exit_measured = calculate_enthalpy(t_ac_exit, inputs.rh_in)
            delta_h = max(0.0, h_exit_measured - h_in_kj_kg)
            p_heating_raw = air_mass_flow * delta_h * 1000.0
        else:
            t_ac_exit = t_ac_exit_calc
            p_heating_raw = p_heating_model
            delta_t_ac = max(0.0, t_ac_exit - inputs.t_in)

        # Heating capacity typically up to 1.15-1.25x of nominal cooling capacity
        ac_max_heating = ac_max_cooling * 1.20
        p_heating = min(ac_max_heating, p_heating_raw)
        cop_real = (p_heating / inputs.ac_power) if inputs.ac_power > 0 else 0.0

        return ACPerformanceResult(
            p_cooling=0.0,
            p_cooling_sensible=0.0,
            p_cooling_latent=0.0,
            p_heating=p_heating,
            cop=cop_real,
            shr=1.0,
            condensation_rate_lh=0.0,
            t_ac_exit=t_ac_exit,
            t_ac_exit_calc=t_ac_exit_calc,
            delta_t_ac=delta_t_ac,
            dew_point_in=dew_point_in,
            dew_point_out=dew_point_out,
            enthalpy_in_kj_kg=h_in_kj_kg,
            is_heating=True,
        )

    # Cooling mode
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
        p_heating=0.0,
        cop=cop_real,
        shr=shr,
        condensation_rate_lh=condensation_rate_lh,
        t_ac_exit=t_ac_exit,
        t_ac_exit_calc=t_ac_exit_calc,
        delta_t_ac=delta_t_ac,
        dew_point_in=dew_point_in,
        dew_point_out=dew_point_out,
        enthalpy_in_kj_kg=h_in_kj_kg,
        is_heating=False,
    )


def estimate_solar_irradiance(
    sun_elevation_deg: float,
    cloud_coverage_pct: float = 0.0,
) -> float:
    """Estimate Global Horizontal Solar Irradiance (GHI) in W/m² using Haurwitz Clear-Sky model and Kasten-Czeplak cloud attenuation.

    Args:
        sun_elevation_deg: Solar elevation angle above horizon in degrees.
        cloud_coverage_pct: Cloud cover percentage (0.0 to 100.0).

    Returns:
        Estimated solar irradiance in W/m² (0.0 at night / sub-zero elevation).
    """
    if sun_elevation_deg <= 0.0:
        return 0.0

    elev_rad = math.radians(sun_elevation_deg)
    sin_elev = math.sin(elev_rad)

    # Haurwitz clear-sky global horizontal irradiance (W/m²)
    i_clear_sky = 1098.0 * sin_elev * math.exp(-0.057 / max(0.01, sin_elev))
    i_clear_sky = max(0.0, min(1100.0, i_clear_sky))

    # Kasten-Czeplak cloud cover attenuation: I = I_clear * (1 - 0.75 * (N/100)^3.4)
    cloud_fraction = max(0.0, min(1.0, cloud_coverage_pct / 100.0))
    attenuation = 1.0 - 0.75 * (cloud_fraction ** 3.4)

    return max(0.0, i_clear_sky * attenuation)


def calculate_solar_radiation(
    window_area: float,
    solar_irradiance: float,
    curtain_g_factor: float,
    window_azimuth: float,
    sun_elevation_deg: float,
    sun_azimuth_deg: float,
    has_sun_position: bool,
) -> tuple[float, float, float, float | None, float, bool]:
    """Calculate solar power incident on a vertical window decomposing direct beam and diffuse radiation.

    Returns:
        tuple containing:
        - p_solar_total (W)
        - p_solar_direct (W)
        - p_solar_diffuse (W)
        - solar_aoi_deg (degrees, Angle of Incidence, or None)
        - solar_cos_aoi (cos of AOI)
        - sun_is_direct (True if direct beam strikes the window surface)
    """
    if solar_irradiance <= 0.0 or window_area <= 0.0:
        return 0.0, 0.0, 0.0, None, 0.0, False

    if not has_sun_position:
        p_total = window_area * solar_irradiance * curtain_g_factor
        return p_total, p_total * 0.8, p_total * 0.2, None, 0.0, True

    if sun_elevation_deg <= 0.0:
        # Sun is at or below the horizon (night / twilight)
        return 0.0, 0.0, 0.0, None, 0.0, False

    # 1. Calculate Solar Angle of Incidence (AOI) on a vertical window (tilt beta = 90 deg)
    # cos(theta) = cos(gamma_s) * cos(alpha_s - alpha_w)
    elev_rad = math.radians(sun_elevation_deg)
    azimuth_diff_deg = (sun_azimuth_deg - window_azimuth) % 360.0
    azimuth_diff_rad = math.radians(azimuth_diff_deg)
    cos_aoi = math.cos(elev_rad) * math.cos(azimuth_diff_rad)

    clamped_cos = max(-1.0, min(1.0, cos_aoi))
    solar_aoi_deg = math.degrees(math.acos(clamped_cos))
    sun_is_direct = (cos_aoi > 0.0)

    # 2. Decompose Global Horizontal Irradiance (GHI) into Direct Horizontal and Diffuse Horizontal
    sin_elev = math.sin(elev_rad)
    if sun_elevation_deg < 2.0 or solar_irradiance < 50.0:
        kd = 1.0  # Entirely diffuse under low sun elevation or heavy cloud overcast
    else:
        kd = max(0.15, min(1.0, 0.15 + 0.15 * (1.0 - sin_elev)))

    i_diffuse_horiz = solar_irradiance * kd
    i_beam_horiz = max(0.0, solar_irradiance - i_diffuse_horiz)

    # 3. Direct Beam Irradiance on vertical window
    if sun_is_direct:
        # Direct Normal Irradiance (DNI)
        dni = i_beam_horiz / max(0.05, sin_elev)
        dni = min(1100.0, dni)  # Physical cap to solar constant at sea level
        i_beam_window = dni * cos_aoi
    else:
        i_beam_window = 0.0

    # 4. Diffuse Sky & Ground-Reflected Irradiance on vertical window
    # View factor for vertical surface to sky is 0.5, to ground is 0.5 with ground albedo ~0.20
    i_diffuse_sky = 0.5 * i_diffuse_horiz
    i_diffuse_ground = 0.5 * 0.20 * solar_irradiance
    i_diffuse_window = i_diffuse_sky + i_diffuse_ground

    # 5. Solar heat power through window glass with shading factor
    p_solar_direct = window_area * i_beam_window * curtain_g_factor
    p_solar_diffuse = window_area * i_diffuse_window * curtain_g_factor
    p_solar_total = p_solar_direct + p_solar_diffuse

    return (
        p_solar_total,
        p_solar_direct,
        p_solar_diffuse,
        solar_aoi_deg,
        cos_aoi,
        sun_is_direct,
    )


def calculate_dynamic_k_factor(
    t_in: float,
    t_out: float,
    p_hvac: float,
    p_solar: float,
    c_total: float,
    dt_dt_c_per_h: float,
    hlc_theoretical: float,
    is_heating: bool = False,
) -> tuple[float | None, float, float]:
    """Calculate dynamic instant K-factor (HLC) with thermal inertia storage rate correction.

    Returns:
        tuple of (k_instant, p_storage_w, p_wall_dynamic_w)
        where k_instant is None if preconditions (delta_t, positive flux) are not met.
    """
    delta_t_env = abs(t_out - t_in)
    if delta_t_env < 1.5:
        return None, 0.0, 0.0

    # Rate of energy stored in building thermal mass (W)
    # c_total is in W·h/K, dt_dt is in °C/h -> W·h/K * K/h = W
    p_storage = c_total * dt_dt_c_per_h

    if is_heating:
        # In heating mode: C_total * dT/dt = P_wall + P_solar + P_heating
        # Transmission loss magnitude: |P_wall| = P_heating + P_solar - P_storage
        p_wall_dynamic = p_hvac + p_solar - p_storage
    else:
        # In cooling mode: C_total * dT/dt = P_wall + P_solar - P_cooling_sensible
        # Heat entering through walls: P_wall = P_cooling_sensible - P_solar + P_storage
        p_wall_dynamic = p_hvac - p_solar + p_storage

    if p_wall_dynamic <= 0.0:
        return None, p_storage, p_wall_dynamic

    k_raw = p_wall_dynamic / delta_t_env
    min_valid_k = 0.5 * hlc_theoretical
    max_valid_k = 2.0 * hlc_theoretical

    if min_valid_k <= k_raw <= max_valid_k:
        return k_raw, p_storage, p_wall_dynamic

    return None, p_storage, p_wall_dynamic


def calculate_equilibrium_temperature(
    t_out: float,
    p_solar: float,
    hlc_total: float,
) -> float:
    """Calculate passive equilibrium room temperature (°C) without HVAC."""
    effective_hlc = max(0.5, hlc_total)
    return t_out + (p_solar / effective_hlc)


def calculate_required_hvac_power(
    t_target: float,
    t_out: float,
    p_solar: float,
    hlc_total: float,
    is_heating: bool = False,
) -> float:
    """Calculate required thermal power (W) to maintain target comfort temperature."""
    effective_hlc = max(0.5, hlc_total)
    if is_heating:
        p_req = (effective_hlc * (t_target - t_out)) - p_solar
    else:
        p_req = (effective_hlc * (t_out - t_target)) + p_solar
    return max(0.0, p_req)


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

    # Solar power entering room with AOI decomposition
    (
        p_solar,
        p_solar_direct,
        p_solar_diffuse,
        solar_aoi_deg,
        solar_cos_aoi,
        sun_is_direct,
    ) = calculate_solar_radiation(
        window_area=geometry.window_area,
        solar_irradiance=max(0.0, inputs.solar_irradiance),
        curtain_g_factor=curtain_g_factor,
        window_azimuth=inputs.window_azimuth,
        sun_elevation_deg=inputs.sun_elevation_deg,
        sun_azimuth_deg=inputs.sun_azimuth_deg,
        has_sun_position=inputs.has_sun_position,
    )

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
    p_loss = max(0.0, -p_env)

    # 4. AC Cooling/Heating calculations
    ac_perf = calculate_ac_performance(inputs, ac_max_cooling, ac_airflow_m3h)

    # 5. Net Power Balance
    if inputs.is_heating:
        p_hvac_output = ac_perf.p_heating
        p_net = p_env + ac_perf.p_heating
        p_net_sensible = p_env + ac_perf.p_heating
    else:
        p_hvac_output = ac_perf.p_cooling
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

    # 7. Advanced analytical metrics
    t_equilibrium = calculate_equilibrium_temperature(inputs.t_out, p_solar, hlc_total)
    t_comfort_target = 23.0
    p_required_hvac = calculate_required_hvac_power(
        t_target=t_comfort_target,
        t_out=inputs.t_out,
        p_solar=p_solar,
        hlc_total=hlc_total,
        is_heating=inputs.is_heating,
    )

    if inputs.is_heating:
        ac_max_heating = ac_max_cooling * 1.20
        is_capacity_insufficient = p_required_hvac > ac_max_heating
    else:
        is_capacity_insufficient = p_gain > ac_max_cooling

    return ThermalCalculationResult(
        p_env=p_env,
        p_gain=p_gain,
        p_wall=p_wall,
        p_vent=p_vent,
        p_trans=p_trans,
        p_solar=p_solar,
        p_solar_direct=p_solar_direct,
        p_solar_diffuse=p_solar_diffuse,
        solar_aoi_deg=solar_aoi_deg,
        solar_cos_aoi=solar_cos_aoi,
        sun_is_direct=sun_is_direct,
        p_cooling=ac_perf.p_cooling,
        p_cooling_sensible=ac_perf.p_cooling_sensible,
        p_cooling_latent=ac_perf.p_cooling_latent,
        p_heating=ac_perf.p_heating,
        p_hvac_output=p_hvac_output,
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
        is_heating=inputs.is_heating,
        hvac_mode=inputs.hvac_mode,
        t_equilibrium=t_equilibrium,
        p_required_hvac=p_required_hvac,
        is_capacity_insufficient=is_capacity_insufficient,
        p_loss=p_loss,
    )
