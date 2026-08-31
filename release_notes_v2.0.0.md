# 🚀 Thermal Balance v2.0.0 — Major Architecture & Physics Release

A massive milestone update bringing full heat pump & heating mode support, astronomical Clear-Sky solar estimation, dynamic thermal mass filtering, interactive dashboard controls, a redesigned 3-step configuration wizard, compact Lovelace view, and a 40-test quality assurance suite!

---

## 🌟 What's New in v2.0.0

### ❄️🔥 1. Heat Pump & Heating Mode Support (Winter / Off-Season)
* Full support for heat pump heating mode ($P_{\text{net}} = P_{\text{gain}} + P_{\text{heating}}$).
* Dynamic thermodynamic COP & Carnot heat pump equations.
* Selectable operation mode: `Cooling`, `Heating`, or `Auto` (automatically tracks your `climate.*` thermostat or outdoor temperature delta).

### ☀️ 2. Astronomical Clear-Sky Solar Estimation & Geometry
* **No solar radiation sensor required!** Integrated **Haurwitz Clear-Sky Model** and **Kasten-Czeplak Cloud Cover Attenuation** using `sun.sun` elevation and optional `weather.*` cloud coverage.
* **Angle of Incidence (AOI)** geometry accounting for sun azimuth and window facing direction ($0^\circ \dots 360^\circ$).

### 🧱 3. Dynamic $dT/dt$ Thermal Mass $K$-Factor Calibration
* Linear regression temperature slope filtering ($P_{\text{steady}} = P_{\text{cooling}} - P_{\text{solar}} - C_{\text{total}} \cdot \frac{dT}{dt}$) prevents false building insulation spikes during rapid AC pulldowns.

### 🎛️ 4. Interactive Controls & Analytical Entities
* **`select.thermal_balance_hvac_mode`**: Switch between Cooling, Heating, and Auto.
* **`select.thermal_balance_curtain_type`**: On-the-fly shading selection (`roller_gaps`, `blackout`, `standard`, `blinds`, `external`).
* **`button.thermal_balance_reset_daily`**: Instant reset of daily kWh and cost accumulators.
* **`button.thermal_balance_reset_k_factor`**: Reset learned building insulation samples.
* **`number.thermal_balance_electricity_rate`**: Real-time electricity tariff adjustments (supports multi-tariff automations).
* **`sensor.thermal_balance_equilibrium_temperature`**: Passive equilibrium temperature.
* **`sensor.thermal_balance_required_ac_power`**: Required HVAC thermal power to hold 23°C.
* **`binary_sensor.thermal_balance_insufficient_cooling_capacity`**: Warning when thermal load exceeds HVAC capacity.

### ⚡ 5. Official Home Assistant Actions (Services)
* `thermal_balance.reset_accumulators`
* `thermal_balance.recalibrate_k_factor`
* `thermal_balance.calculate_cooling_needs` (returns `ServiceResponse` dictionary)

### 🧙‍♂️ 6. 3-Step Wizard Config Flow & Gold Quality Reconfiguration
* Replaced the cluttered 23-field single screen with a clean **3-step wizard**:
  * **Step 1:** Room Geometry & Insulation
  * **Step 2:** Climate Equipment, Shading & Tariffs
  * **Step 3:** Sensors & Meteorological Inputs
* Full **Gold Quality Scale `async_step_reconfigure`** support (reconfigure room parameters without losing history).

### 🎨 7. Dashboard Card v2 (i18n, Compact View & Seasonal Theming)
* **Automatic i18n:** English and Russian translation detection via `hass.locale.language`.
* **Mobile Compact Mode (`compact: true`):** Single-column layout optimized for mobile screens.
* **Seasonal Themes:** Cool cyan neon glow in summer vs warm ember glow in winter heating mode.

### 🧪 8. Test Suite, CI/CD & Icons Localization
* 40 unit tests passing with 100% success rate across Python 3.12 and 3.13.
* GitHub Actions CI/CD workflow with `hacs/action` validation.
* Quality Scale `icons.json` for MDI entity and service icons.

---

**Full Changelog**: https://github.com/ziffmafiya/thermal_balance/compare/v1.7.5...v2.0.0
