"""Unit tests for Thermal Balance services and ServiceValidationError exceptions."""
import asyncio
import os
import sys
import unittest

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from mock_ha import MockConfigEntry, MockHomeAssistant, setup_mock_homeassistant

setup_mock_homeassistant()

from homeassistant.exceptions import ServiceValidationError
from custom_components.thermal_balance import async_setup
from custom_components.thermal_balance.const import (
    CONF_AC_MAX_COOLING,
    CONF_ROOM_AREA,
    DOMAIN,
    SERVICE_CALCULATE_COOLING_NEEDS,
    SERVICE_RECALIBRATE_K_FACTOR,
    SERVICE_RESET_ACCUMULATORS,
)
from custom_components.thermal_balance.coordinator import ThermalBalanceCoordinator


class TestThermalBalanceServices(unittest.TestCase):
    """Test suite for integration services and Quality Scale exception handling."""

    def setUp(self) -> None:
        """Set up test environment."""
        self.hass = MockHomeAssistant()
        asyncio.run(async_setup(self.hass, {}))

        self.entry = MockConfigEntry(
            entry_id="living_room_entry",
            data={CONF_ROOM_AREA: 20.0, CONF_AC_MAX_COOLING: 3350.0},
        )
        self.coordinator = ThermalBalanceCoordinator(self.hass, self.entry)
        self.entry.runtime_data = self.coordinator
        self.hass.config_entries.add(self.entry)

    def test_services_registered(self) -> None:
        """Test that all three integration services are registered."""
        self.assertIn(DOMAIN, self.hass.services.services)
        services = self.hass.services.services[DOMAIN]
        self.assertIn(SERVICE_RESET_ACCUMULATORS, services)
        self.assertIn(SERVICE_RECALIBRATE_K_FACTOR, services)
        self.assertIn(SERVICE_CALCULATE_COOLING_NEEDS, services)

    def test_invalid_entry_id_raises_service_validation_error(self) -> None:
        """Test that passing an invalid or non-existent entry_id raises ServiceValidationError across all services."""
        for service in [
            SERVICE_RESET_ACCUMULATORS,
            SERVICE_RECALIBRATE_K_FACTOR,
            SERVICE_CALCULATE_COOLING_NEEDS,
        ]:
            with self.subTest(service=service):
                with self.assertRaises(ServiceValidationError) as ctx:
                    asyncio.run(
                        self.hass.services.async_call(
                            DOMAIN,
                            service,
                            {"entry_id": "non_existent_entry"},
                        )
                    )
                self.assertEqual(ctx.exception.translation_domain, DOMAIN)
                self.assertEqual(ctx.exception.translation_key, "entry_not_found")
                self.assertEqual(ctx.exception.translation_placeholders, {"entry_id": "non_existent_entry"})

    def test_services_no_instances_raises_error(self) -> None:
        """Test that calling any service with no active instances raises ServiceValidationError."""
        empty_hass = MockHomeAssistant()
        asyncio.run(async_setup(empty_hass, {}))

        for service in [
            SERVICE_RESET_ACCUMULATORS,
            SERVICE_RECALIBRATE_K_FACTOR,
            SERVICE_CALCULATE_COOLING_NEEDS,
        ]:
            with self.subTest(service=service):
                with self.assertRaises(ServiceValidationError) as ctx:
                    asyncio.run(
                        empty_hass.services.async_call(
                            DOMAIN,
                            service,
                            {},
                        )
                    )
                self.assertEqual(ctx.exception.translation_domain, DOMAIN)
                self.assertEqual(ctx.exception.translation_key, "no_instances")

    def test_calculate_cooling_needs_success(self) -> None:
        """Test calculate_cooling_needs execution with realistic values."""
        response = asyncio.run(
            self.hass.services.async_call(
                DOMAIN,
                SERVICE_CALCULATE_COOLING_NEEDS,
                {
                    "entry_id": "living_room_entry",
                    "target_temperature": 24.0,
                    "outdoor_temperature": 34.0,
                    "solar_irradiance": 500.0,
                    "curtains_closed": False,
                },
            )
        )

        self.assertIsInstance(response, dict)
        self.assertIn("required_power_w", response)
        self.assertIn("equilibrium_temperature_c", response)
        self.assertIn("cooling_load_fraction", response)
        self.assertIn("estimated_cop", response)
        self.assertIn("estimated_elec_power_w", response)
        self.assertGreater(response["required_power_w"], 0.0)
        self.assertGreater(response["equilibrium_temperature_c"], 34.0)

    def test_reset_accumulators_service(self) -> None:
        """Test reset_accumulators service calls coordinator reset."""
        self.coordinator.total_heat_absorbed = 15.0
        self.coordinator.daily_heat_absorbed = 8.0

        asyncio.run(
            self.hass.services.async_call(
                DOMAIN,
                SERVICE_RESET_ACCUMULATORS,
                {"entry_id": "living_room_entry"},
            )
        )

        self.assertEqual(self.coordinator.total_heat_absorbed, 0.0)
        self.assertEqual(self.coordinator.daily_heat_absorbed, 0.0)

    def test_recalibrate_k_factor_service(self) -> None:
        """Test recalibrate_k_factor service resets empirical samples."""
        self.coordinator._k_samples_count = 25

        asyncio.run(
            self.hass.services.async_call(
                DOMAIN,
                SERVICE_RECALIBRATE_K_FACTOR,
                {"entry_id": "living_room_entry"},
            )
        )

        self.assertEqual(self.coordinator._k_samples_count, 0)


if __name__ == "__main__":
    unittest.main()
