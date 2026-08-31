"""Lightweight Home Assistant mock harness for standalone unit testing."""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from enum import StrEnum
from types import ModuleType
from typing import Any, Callable
from unittest.mock import MagicMock
import voluptuous as vol


class MockState:
    """Mock Home Assistant State object."""

    def __init__(self, state: str, attributes: dict[str, Any] | None = None) -> None:
        self.state = state
        self.attributes = attributes or {}


class MockStateMachine:
    """Mock Home Assistant state machine."""

    def __init__(self) -> None:
        self._states: dict[str, MockState] = {}

    def get(self, entity_id: str) -> MockState | None:
        return self._states.get(entity_id)

    def set(self, entity_id: str, state: str, attributes: dict[str, Any] | None = None) -> None:
        self._states[entity_id] = MockState(state, attributes)


class MockConfig:
    """Mock Home Assistant config."""

    def __init__(self, currency: str = "USD") -> None:
        self.currency = currency


class MockHomeAssistant:
    """Mock Home Assistant instance."""

    def __init__(self) -> None:
        self.states = MockStateMachine()
        self.config = MockConfig()
        self.services = MagicMock()
        self.http = MagicMock()


class MockConfigEntry:
    """Mock ConfigEntry object."""

    def __init__(
        self,
        entry_id: str = "test_entry_123",
        data: dict[str, Any] | None = None,
        options: dict[str, Any] | None = None,
        title: str = "Thermal Balance",
    ) -> None:
        self.entry_id = entry_id
        self.data = data or {}
        self.options = options or {}
        self.title = title
        self.runtime_data: Any = None


class Platform(StrEnum):
    """Mock Platform enum."""

    SENSOR = "sensor"
    BINARY_SENSOR = "binary_sensor"
    BUTTON = "button"
    NUMBER = "number"
    SELECT = "select"


def setup_mock_homeassistant() -> None:
    """Install mock homeassistant modules in sys.modules if not present."""
    if "homeassistant" in sys.modules and hasattr(sys.modules["homeassistant"], "_is_mock"):
        return

    ha = ModuleType("homeassistant")
    ha._is_mock = True
    ha.__path__ = []

    ha_const = ModuleType("homeassistant.const")
    ha_const.Platform = Platform
    ha_const.SUN_EVENT_SUNRISE = "sunrise"
    ha_const.SUN_EVENT_SUNSET = "sunset"

    ha_core = ModuleType("homeassistant.core")
    ha_core.__path__ = []

    ha_config_entries = ModuleType("homeassistant.config_entries")
    ha_config_entries.__path__ = []

    ha_helpers = ModuleType("homeassistant.helpers")
    ha_helpers.__path__ = []

    ha_helpers_typing = ModuleType("homeassistant.helpers.typing")
    ha_helpers_typing.ConfigType = dict[str, Any]
    ha_helpers_typing.DiscoveryInfoType = dict[str, Any]

    ha_helpers_cv = ModuleType("homeassistant.helpers.config_validation")
    ha_helpers_cv.string = cv_string = lambda v: str(v)
    ha_helpers_cv.positive_float = lambda v: float(v)
    ha_helpers_cv.boolean = lambda v: bool(v)
    ha_helpers_cv.make_entity_service_schema = lambda schema: vol.Schema(schema)
    ha_helpers_cv.config_entry_only_config_schema = lambda domain: vol.Schema({})
    ha_helpers_cv.empty_config_schema = lambda domain: vol.Schema({})
    ha_helpers_cv.platform_only_config_schema = lambda domain: vol.Schema({})

    ha_helpers_event = ModuleType("homeassistant.helpers.event")
    ha_helpers_selector = ModuleType("homeassistant.helpers.selector")
    ha_helpers_entity = ModuleType("homeassistant.helpers.entity")
    ha_helpers_restore_state = ModuleType("homeassistant.helpers.restore_state")

    ha_helpers_update_coordinator = ModuleType("homeassistant.helpers.update_coordinator")

    class MockDataUpdateCoordinator:
        def __init__(
            self,
            hass: Any,
            logger: Any,
            name: str,
            update_interval: Any = None,
            always_update: bool = True,
            **kwargs: Any,
        ) -> None:
            self.hass = hass
            self.logger = logger
            self.name = name
            self.update_interval = update_interval
            self.always_update = always_update
            self.data: dict[str, Any] = {}

        def __class_getitem__(cls, item: Any) -> Any:
            return cls

        def async_set_updated_data(self, data: dict[str, Any]) -> None:
            self.data = data

    ha_helpers_update_coordinator.DataUpdateCoordinator = MockDataUpdateCoordinator
    ha_helpers_update_coordinator.UpdateFailed = Exception

    ha_components = ModuleType("homeassistant.components")
    ha_components.__path__ = []

    ha_components_frontend = ModuleType("homeassistant.components.frontend")
    ha_components_frontend.add_extra_js_url = MagicMock()

    ha_components_http = ModuleType("homeassistant.components.http")
    ha_components_http.StaticPathConfig = MagicMock()

    ha_components_diagnostics = ModuleType("homeassistant.components.diagnostics")
    ha_components_sensor = ModuleType("homeassistant.components.sensor")
    ha_components_binary_sensor = ModuleType("homeassistant.components.binary_sensor")
    ha_components_button = ModuleType("homeassistant.components.button")
    ha_components_number = ModuleType("homeassistant.components.number")
    ha_components_select = ModuleType("homeassistant.components.select")

    ha_util = ModuleType("homeassistant.util")
    ha_util.__path__ = []
    ha_util_dt = ModuleType("homeassistant.util.dt")

    # core
    def callback(func: Callable) -> Callable:
        return func

    ha_core.callback = callback
    ha_core.HomeAssistant = MockHomeAssistant
    ha_core.Event = MagicMock
    ha_core.ServiceCall = MagicMock
    ha_core.ServiceResponse = dict[str, Any]
    ha_core.SupportsResponse = MagicMock()
    ha_core.SupportsResponse.OPTIONAL = "optional"

    # config_entries
    class BaseConfigFlow:
        VERSION = 1
        DOMAIN = "thermal_balance"

        def __init_subclass__(cls, domain: str | None = None, **kwargs: Any) -> None:
            super().__init_subclass__(**kwargs)
            if domain:
                cls.DOMAIN = domain

        def __init__(self) -> None:
            self._reconfigure_entry = None

        def _get_reconfigure_entry(self) -> Any:
            return self._reconfigure_entry

        def async_show_form(self, step_id: str, data_schema: Any, errors: dict[str, str] | None = None) -> dict[str, Any]:
            return {"type": "form", "step_id": step_id, "data_schema": data_schema, "errors": errors or {}}

        def async_create_entry(self, title: str, data: dict[str, Any]) -> dict[str, Any]:
            return {"type": "create_entry", "title": title, "data": data}

        def async_update_reload_and_abort(self, entry: Any, data: dict[str, Any], reason: str) -> dict[str, Any]:
            return {"type": "abort", "reason": reason, "data": data}

    class BaseOptionsFlow:
        def __init__(self, config_entry: Any = None) -> None:
            self.config_entry = config_entry

        def async_show_form(self, step_id: str, data_schema: Any, errors: dict[str, str] | None = None) -> dict[str, Any]:
            return {"type": "form", "step_id": step_id, "data_schema": data_schema, "errors": errors or {}}

        def async_create_entry(self, title: str, data: dict[str, Any]) -> dict[str, Any]:
            return {"type": "create_entry", "title": title, "data": data}

    ha_config_entries.ConfigFlow = BaseConfigFlow
    ha_config_entries.OptionsFlow = BaseOptionsFlow
    ha_config_entries.ConfigEntry = MockConfigEntry
    ha_config_entries.ConfigFlowResult = dict[str, Any]

    # helpers.selector
    class MockSelector:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def __call__(self, data: Any) -> Any:
            return data

    ha_helpers_selector.NumberSelector = MockSelector
    ha_helpers_selector.NumberSelectorConfig = MockSelector
    ha_helpers_selector.NumberSelectorMode = MagicMock()
    ha_helpers_selector.NumberSelectorMode.BOX = "box"
    ha_helpers_selector.SelectSelector = MockSelector
    ha_helpers_selector.SelectSelectorConfig = MockSelector
    ha_helpers_selector.SelectSelectorMode = MagicMock()
    ha_helpers_selector.SelectSelectorMode.DROPDOWN = "dropdown"
    ha_helpers_selector.SelectOptionDict = dict
    ha_helpers_selector.EntitySelector = MockSelector
    ha_helpers_selector.EntitySelectorConfig = MockSelector
    ha_helpers_selector.BooleanSelector = MockSelector
    ha_helpers_selector.TextSelector = MockSelector

    # helpers.event
    def mock_track_state_change_event(hass: Any, entities: Any, callback: Any) -> Callable:
        return lambda: None

    def mock_track_time_change(hass: Any, callback: Any, hour: int = 0, minute: int = 0, second: int = 0) -> Callable:
        return lambda: None

    def mock_track_time_interval(hass: Any, callback: Any, interval: Any) -> Callable:
        return lambda: None

    ha_helpers_event.async_track_state_change_event = mock_track_state_change_event
    ha_helpers_event.async_track_time_change = mock_track_time_change
    ha_helpers_event.async_track_time_interval = mock_track_time_interval

    # util.dt
    ha_util_dt.now = lambda: datetime.now(timezone.utc)
    ha_util_dt.utcnow = lambda: datetime.now(timezone.utc)

    # components.diagnostics
    def async_redact_data(data: dict[str, Any], to_redact: list[str]) -> dict[str, Any]:
        return {k: v for k, v in data.items() if k not in to_redact}

    ha_components_diagnostics.async_redact_data = async_redact_data

    # Register in sys.modules
    sys.modules["homeassistant"] = ha
    sys.modules["homeassistant.const"] = ha_const
    sys.modules["homeassistant.core"] = ha_core
    sys.modules["homeassistant.config_entries"] = ha_config_entries
    sys.modules["homeassistant.helpers"] = ha_helpers
    sys.modules["homeassistant.helpers.typing"] = ha_helpers_typing
    sys.modules["homeassistant.helpers.config_validation"] = ha_helpers_cv
    sys.modules["homeassistant.helpers.selector"] = ha_helpers_selector
    sys.modules["homeassistant.helpers.event"] = ha_helpers_event
    sys.modules["homeassistant.helpers.entity"] = ha_helpers_entity
    sys.modules["homeassistant.helpers.restore_state"] = ha_helpers_restore_state
    sys.modules["homeassistant.helpers.update_coordinator"] = ha_helpers_update_coordinator
    sys.modules["homeassistant.components"] = ha_components
    sys.modules["homeassistant.components.frontend"] = ha_components_frontend
    sys.modules["homeassistant.components.http"] = ha_components_http
    sys.modules["homeassistant.components.diagnostics"] = ha_components_diagnostics
    sys.modules["homeassistant.components.sensor"] = ha_components_sensor
    sys.modules["homeassistant.components.binary_sensor"] = ha_components_binary_sensor
    sys.modules["homeassistant.components.button"] = ha_components_button
    sys.modules["homeassistant.components.number"] = ha_components_number
    sys.modules["homeassistant.components.select"] = ha_components_select
    sys.modules["homeassistant.util"] = ha_util
    sys.modules["homeassistant.util.dt"] = ha_util_dt
