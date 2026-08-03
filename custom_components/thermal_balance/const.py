"""Constants for Thermal Balance integration."""
from typing import Final

DOMAIN: Final = "thermal_balance"

# Configuration options
CONF_ROOM_AREA: Final = "room_area"
CONF_CEILING_HEIGHT: Final = "ceiling_height"
CONF_WINDOW_AREA: Final = "window_area"
CONF_U_WALL: Final = "u_wall"
CONF_U_WINDOW: Final = "u_window"
CONF_EXTERNAL_WALLS_FRACTION: Final = "external_walls_fraction"
CONF_AC_MAX_COOLING: Final = "ac_max_cooling"
CONF_AC_AIRFLOW: Final = "ac_airflow"
CONF_USE_EMPIRICAL_HLC: Final = "use_empirical_hlc"

CONF_SENSOR_T_IN: Final = "sensor_t_in"
CONF_SENSOR_T_OUT: Final = "sensor_t_out"
CONF_SENSOR_SOLAR: Final = "sensor_solar"
CONF_SENSOR_AC_POWER: Final = "sensor_ac_power"
CONF_SENSOR_WINDOW: Final = "sensor_window"
CONF_SENSOR_RH_IN: Final = "sensor_rh_in"
CONF_SENSOR_RH_OUT: Final = "sensor_rh_out"
CONF_SENSOR_T_AC_EXIT: Final = "sensor_t_ac_exit"
CONF_SENSOR_ILLUMINANCE: Final = "sensor_illuminance"
CONF_SENSOR_WIND_SPEED: Final = "sensor_wind_speed"
CONF_SENSOR_WIND_DIRECTION: Final = "sensor_wind_direction"
CONF_WINDOW_AZIMUTH: Final = "window_azimuth"
CONF_ILLUMINANCE_THRESHOLD: Final = "illuminance_threshold"

CONF_ELECTRICITY_RATE: Final = "electricity_rate"
CONF_CURRENCY_SYMBOL: Final = "currency_symbol"
CONF_CURTAIN_TYPE: Final = "curtain_type"

# Defaults
DEFAULT_U_WALL: Final = 0.3
DEFAULT_U_WINDOW: Final = 1.1
DEFAULT_ROOM_AREA: Final = 20.0
DEFAULT_CEILING_HEIGHT: Final = 2.7
DEFAULT_WINDOW_AREA: Final = 3.0
DEFAULT_EXTERNAL_WALLS_FRACTION: Final = 0.25
DEFAULT_AC_MAX_COOLING: Final = 3350.0
DEFAULT_AC_AIRFLOW: Final = 370.0  # m³/h (from Cooper&Hunter spec 210/320/370/480)
DEFAULT_USE_EMPIRICAL_HLC: Final = False
DEFAULT_ILLUMINANCE_THRESHOLD: Final = 150.0
DEFAULT_ELECTRICITY_RATE: Final = 4.32
DEFAULT_CURRENCY_SYMBOL: Final = "₴"
DEFAULT_WINDOW_AZIMUTH: Final = 0.0
DEFAULT_CURTAIN_TYPE: Final = "roller_gaps"

# Sensor keys
SENSOR_INSTANT_HEAT_GAIN: Final = "instant_heat_gain"
SENSOR_AC_HEAT_OUTPUT: Final = "ac_heat_output"
SENSOR_INSTANT_NET_BALANCE: Final = "instant_net_balance"
SENSOR_AC_CARNOT_COP: Final = "ac_carnot_cop"
SENSOR_TIME_TO_1DEG: Final = "time_to_1deg"
SENSOR_DAILY_THERMAL_BALANCE: Final = "daily_thermal_balance"
SENSOR_NET_THERMAL_BALANCE: Final = "net_thermal_balance"
SENSOR_TOTAL_HEAT_ABSORBED: Final = "total_heat_absorbed"
SENSOR_AC_THERMAL_ENERGY_TOTAL: Final = "ac_thermal_energy_total"
SENSOR_AC_CONDENSATION_RATE: Final = "ac_condensation_rate"
SENSOR_EMPIRICAL_K_FACTOR: Final = "empirical_k_factor"

SENSOR_AC_ENERGY_COST: Final = "ac_energy_cost"
SENSOR_SHADING_DAILY_SAVINGS: Final = "shading_daily_savings"

# Binary sensor keys
BINARY_SENSOR_RECOMMEND_OPEN_WINDOW: Final = "recommend_open_window"
BINARY_SENSOR_RECOMMEND_CLOSE_CURTAINS: Final = "recommend_close_curtains"
