"""Thermal Balance Integration for Home Assistant."""
import logging
import os

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import ThermalBalanceCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]

# Track whether the frontend card has been registered (once per HA session)
_FRONTEND_REGISTERED = False


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Thermal Balance from a config entry."""
    global _FRONTEND_REGISTERED  # noqa: PLW0603

    hass.data.setdefault(DOMAIN, {})

    # Register the built-in Lovelace card (only once per HA startup)
    if not _FRONTEND_REGISTERED:
        card_path = os.path.join(os.path.dirname(__file__), "thermal-balance-card.js")
        echarts_path = os.path.join(os.path.dirname(__file__), "echarts.min.js")
        url_path = f"/{DOMAIN}/thermal-balance-card.js"
        url_echarts = f"/{DOMAIN}/echarts.min.js"

        # HA 2024.7+ uses async_register_static_paths with StaticPathConfig
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

        # Copy files to www directory for native /local/ path support
        try:
            www_dir = hass.config.path("www", DOMAIN)
            os.makedirs(www_dir, exist_ok=True)
            import shutil
            shutil.copy2(card_path, os.path.join(www_dir, "thermal-balance-card.js"))
            shutil.copy2(echarts_path, os.path.join(www_dir, "echarts.min.js"))
            _LOGGER.info("Copied card assets to %s", www_dir)
        except Exception as err:
            _LOGGER.debug("Could not copy card assets to www: %s", err)

        # Auto-register in Lovelace Dashboard resources (Storage Mode)
        try:
            lovelace = hass.data.get("lovelace")
            if lovelace:
                resources = getattr(lovelace, "resources", None)
                if resources:
                    if hasattr(resources, "loaded") and not resources.loaded:
                        await resources.async_load()
                    if hasattr(resources, "async_items") and hasattr(resources, "async_create_item"):
                        existing_urls = [item.get("url") for item in resources.async_items()]
                        for res_url in (f"/local/{DOMAIN}/thermal-balance-card.js", f"/{DOMAIN}/thermal-balance-card.js"):
                            if res_url not in existing_urls:
                                await resources.async_create_item({"res_type": "module", "url": res_url})
                                _LOGGER.info("Auto-registered Lovelace resource: %s", res_url)
        except Exception as err:
            _LOGGER.debug("Lovelace resource auto-registration skipped: %s", err)

    coordinator = ThermalBalanceCoordinator(hass, entry)
    await coordinator.async_start()

    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Listen for options updates
    entry.async_on_unload(entry.add_update_listener(async_update_options))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    coordinator: ThermalBalanceCoordinator = hass.data[DOMAIN].get(entry.entry_id)
    if coordinator:
        await coordinator.async_stop()

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)

    return unload_ok


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(entry.entry_id)
