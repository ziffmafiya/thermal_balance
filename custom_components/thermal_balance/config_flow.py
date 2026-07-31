"""Config flow for Thermal Balance integration."""
from typing import Any, Dict, Optional

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_AC_AIRFLOW,
    CONF_AC_MAX_COOLING,
    CONF_CEILING_HEIGHT,
    CONF_CURRENCY_SYMBOL,
    CONF_ELECTRICITY_RATE,
    CONF_EXTERNAL_WALLS_FRACTION,
    CONF_ILLUMINANCE_THRESHOLD,
    CONF_ROOM_AREA,
    CONF_SENSOR_AC_POWER,
    CONF_SENSOR_ILLUMINANCE,
    CONF_SENSOR_RH_IN,
    CONF_SENSOR_RH_OUT,
    CONF_SENSOR_SOLAR,
    CONF_SENSOR_T_AC_EXIT,
    CONF_SENSOR_T_IN,
    CONF_SENSOR_T_OUT,
    CONF_SENSOR_WIND_SPEED,
    CONF_SENSOR_WIND_DIRECTION,
    CONF_WINDOW_AZIMUTH,
    CONF_SENSOR_WINDOW,
    CONF_U_WALL,
    CONF_U_WINDOW,
    CONF_USE_EMPIRICAL_HLC,
    CONF_WINDOW_AREA,
    DEFAULT_AC_AIRFLOW,
    DEFAULT_AC_MAX_COOLING,
    DEFAULT_CEILING_HEIGHT,
    DEFAULT_CURRENCY_SYMBOL,
    DEFAULT_ELECTRICITY_RATE,
    DEFAULT_EXTERNAL_WALLS_FRACTION,
    DEFAULT_ILLUMINANCE_THRESHOLD,
    DEFAULT_ROOM_AREA,
    DEFAULT_U_WALL,
    DEFAULT_U_WINDOW,
    DEFAULT_USE_EMPIRICAL_HLC,
    DEFAULT_WINDOW_AREA,
    DEFAULT_WINDOW_AZIMUTH,
    DOMAIN,
)


def _safe_float(val: Any, default: float) -> float:
    """Safely convert value to float."""
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def get_schema(defaults: Dict[str, Any]) -> vol.Schema:
    """Return common configuration schema with defaults."""
    ext_walls_default = str(_safe_float(defaults.get(CONF_EXTERNAL_WALLS_FRACTION), DEFAULT_EXTERNAL_WALLS_FRACTION))
    if ext_walls_default not in ("0.25", "0.5", "0.50", "0.75", "1.0", "1.00"):
        ext_walls_default = "0.25"
    if ext_walls_default == "0.5":
        ext_walls_default = "0.50"
    if ext_walls_default == "1.0":
        ext_walls_default = "1.00"

    schema_dict = {
        vol.Required(
            CONF_ROOM_AREA,
            default=_safe_float(defaults.get(CONF_ROOM_AREA), DEFAULT_ROOM_AREA),
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=1.0, max=500.0, step=0.1, unit_of_measurement="m²", mode=selector.NumberSelectorMode.BOX
            )
        ),
        vol.Required(
            CONF_CEILING_HEIGHT,
            default=_safe_float(defaults.get(CONF_CEILING_HEIGHT), DEFAULT_CEILING_HEIGHT),
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=1.0, max=20.0, step=0.1, unit_of_measurement="m", mode=selector.NumberSelectorMode.BOX
            )
        ),
        vol.Required(
            CONF_WINDOW_AREA,
            default=_safe_float(defaults.get(CONF_WINDOW_AREA), DEFAULT_WINDOW_AREA),
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0.0, max=100.0, step=0.1, unit_of_measurement="m²", mode=selector.NumberSelectorMode.BOX
            )
        ),
        vol.Required(
            CONF_EXTERNAL_WALLS_FRACTION,
            default=ext_walls_default,
        ): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[
                    selector.SelectOptionDict(value="0.25", label="0.25 (1 of 4 walls — typical room)"),
                    selector.SelectOptionDict(value="0.50", label="0.50 (2 of 4 walls — corner room)"),
                    selector.SelectOptionDict(value="0.75", label="0.75 (3 of 4 walls)"),
                    selector.SelectOptionDict(value="1.00", label="1.00 (4 walls — detached house)"),
                ],
                mode=selector.SelectSelectorMode.DROPDOWN,
            )
        ),
        vol.Required(
            CONF_AC_MAX_COOLING,
            default=_safe_float(defaults.get(CONF_AC_MAX_COOLING), DEFAULT_AC_MAX_COOLING),
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=100.0, max=20000.0, step=50.0, unit_of_measurement="W", mode=selector.NumberSelectorMode.BOX
            )
        ),
        vol.Required(
            CONF_AC_AIRFLOW,
            default=_safe_float(defaults.get(CONF_AC_AIRFLOW), DEFAULT_AC_AIRFLOW),
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=50.0, max=2000.0, step=10.0, unit_of_measurement="m³/h", mode=selector.NumberSelectorMode.BOX
            )
        ),
        vol.Required(
            CONF_U_WALL,
            default=_safe_float(defaults.get(CONF_U_WALL), DEFAULT_U_WALL),
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0.01, max=10.0, step=0.01, unit_of_measurement="W/(m²·K)", mode=selector.NumberSelectorMode.BOX
            )
        ),
        vol.Required(
            CONF_U_WINDOW,
            default=_safe_float(defaults.get(CONF_U_WINDOW), DEFAULT_U_WINDOW),
        ): selector.NumberSelector(
            selector.NumberSelectorConfig(
                min=0.1, max=10.0, step=0.01, unit_of_measurement="W/(m²·K)", mode=selector.NumberSelectorMode.BOX
            )
        ),
        vol.Optional(
            CONF_USE_EMPIRICAL_HLC,
            default=bool(defaults.get(CONF_USE_EMPIRICAL_HLC, DEFAULT_USE_EMPIRICAL_HLC)),
        ): selector.BooleanSelector(),
    }

    # Entity selectors (Required - allows sensor or input_number)
    for conf_key in (CONF_SENSOR_T_IN, CONF_SENSOR_T_OUT, CONF_SENSOR_SOLAR, CONF_SENSOR_AC_POWER):
        val = defaults.get(conf_key)
        if val and isinstance(val, str) and val.strip():
            schema_dict[vol.Required(conf_key, default=val)] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["sensor", "input_number", "number"])
            )
        else:
            schema_dict[vol.Required(conf_key)] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["sensor", "input_number", "number"])
            )

    # Optional Sensors (Humidity, Measured AC Exit Temperature / Delta T, Window, Illuminance, Wind)
    for conf_key in (CONF_SENSOR_RH_IN, CONF_SENSOR_RH_OUT, CONF_SENSOR_T_AC_EXIT, CONF_SENSOR_ILLUMINANCE, CONF_SENSOR_WIND_SPEED, CONF_SENSOR_WIND_DIRECTION):
        val = defaults.get(conf_key)
        if val and isinstance(val, str) and val.strip():
            schema_dict[vol.Optional(conf_key, default=val)] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["sensor", "input_number", "number"])
            )
        else:
            schema_dict[vol.Optional(conf_key)] = selector.EntitySelector(
                selector.EntitySelectorConfig(domain=["sensor", "input_number", "number"])
            )

    vol_thresh = _safe_float(defaults.get(CONF_ILLUMINANCE_THRESHOLD), DEFAULT_ILLUMINANCE_THRESHOLD)
    schema_dict[vol.Optional(CONF_ILLUMINANCE_THRESHOLD, default=vol_thresh)] = selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=1.0, max=5000.0, step=5.0, unit_of_measurement="lx", mode=selector.NumberSelectorMode.BOX
        )
    )

    vol_rate = _safe_float(defaults.get(CONF_ELECTRICITY_RATE), DEFAULT_ELECTRICITY_RATE)
    schema_dict[vol.Optional(CONF_ELECTRICITY_RATE, default=vol_rate)] = selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=0.0, max=100.0, step=0.01, mode=selector.NumberSelectorMode.BOX
        )
    )

    curr_sym = str(defaults.get(CONF_CURRENCY_SYMBOL, DEFAULT_CURRENCY_SYMBOL))
    schema_dict[vol.Optional(CONF_CURRENCY_SYMBOL, default=curr_sym)] = selector.TextSelector()

    win_val = defaults.get(CONF_SENSOR_WINDOW)
    if win_val and isinstance(win_val, str) and win_val.strip():
        schema_dict[vol.Optional(CONF_SENSOR_WINDOW, default=win_val)] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="binary_sensor")
        )
    else:
        schema_dict[vol.Optional(CONF_SENSOR_WINDOW)] = selector.EntitySelector(
            selector.EntitySelectorConfig(domain="binary_sensor")
        )

    azimuth_val = _safe_float(defaults.get(CONF_WINDOW_AZIMUTH), DEFAULT_WINDOW_AZIMUTH)
    schema_dict[vol.Optional(CONF_WINDOW_AZIMUTH, default=azimuth_val)] = selector.NumberSelector(
        selector.NumberSelectorConfig(
            min=0.0, max=359.9, step=1.0, unit_of_measurement="°", mode=selector.NumberSelectorMode.BOX
        )
    )

    return vol.Schema(schema_dict)


class ThermalBalanceConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Thermal Balance."""

    VERSION = 1

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> config_entries.FlowResult:
        """Handle the initial step."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            title = f"Thermal Balance ({user_input.get(CONF_ROOM_AREA)} m²)"
            return self.async_create_entry(title=title, data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=get_schema({}),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Get options flow for this handler."""
        return ThermalBalanceOptionsFlow(config_entry)


class ThermalBalanceOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Thermal Balance."""

    def __init__(self, config_entry: Optional[config_entries.ConfigEntry] = None) -> None:
        """Initialize options flow compatible with all Home Assistant versions."""
        if config_entry is not None:
            self._config_entry = config_entry

    @property
    def current_config_entry(self) -> config_entries.ConfigEntry:
        """Return active config entry."""
        if hasattr(self, "_config_entry") and self._config_entry is not None:
            return self._config_entry
        return getattr(self, "config_entry", None)

    async def async_step_init(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> config_entries.FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        entry = self.current_config_entry
        current_defaults = {}
        if entry is not None:
            current_defaults = {**entry.data, **entry.options}

        return self.async_show_form(
            step_id="init",
            data_schema=get_schema(current_defaults),
        )
