"""Thermal Balance Integration for Home Assistant."""
from __future__ import annotations

import logging
import os

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import ThermalBalanceCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]

# Track whether the frontend card has been registered (once per HA session)
_FRONTEND_REGISTERED = False


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Thermal Balance from a config entry."""
    global _FRONTEND_REGISTERED  # noqa: PLW0603

    # Register the built-in Lovelace card (only once per HA startup)
    if not _FRONTEND_REGISTERED:
        card_path = os.path.join(os.path.dirname(__file__), "thermal-balance-card.js")
        echarts_path = os.path.join(os.path.dirname(__file__), "echarts.min.js")
        url_path = f"/{DOMAIN}/thermal-balance-card.js"
        url_echarts = f"/{DOMAIN}/echarts.min.js"

        if os.path.exists(card_path) and os.path.exists(echarts_path):
            if hasattr(hass.http, "async_register_static_paths"):
                from homeassistant.components.http import StaticPathConfig
                await hass.http.async_register_static_paths([
                    StaticPathConfig(url_path, card_path, False),
                    StaticPathConfig(url_echarts, echarts_path, False),
                ])
            else:
                hass.http.register_static_path(url_path, card_path, cache_headers=False)
                hass.http.register_static_path(url_echarts, echarts_path, cache_headers=False)

            add_extra_js_url(hass, url_path)
            _FRONTEND_REGISTERED = True
            _LOGGER.info("Thermal Balance Lovelace card registered at %s", url_path)

    coordinator = ThermalBalanceCoordinator(hass, entry)
    await coordinator.async_start()

    # Store coordinator directly in runtime_data (HA 2024.4+ standard)
    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Listen for options updates
    entry.async_on_unload(entry.add_update_listener(async_update_options))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    coordinator: ThermalBalanceCoordinator = entry.runtime_data
    if coordinator:
        await coordinator.async_stop()

    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)
