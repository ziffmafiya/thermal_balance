# 🚀 Thermal Balance v2.1.0 — Clean Architecture, Quality Scale & Modern UI/UX Release

A comprehensive quality, security, and performance release bringing clean architectural separation (`engine.py`), continuous-time thermodynamic filtering, Lovelace memory leak elimination, single-pass persistent Shadow DOM scaffolding, Stored DOM XSS elimination, Home Assistant Silver Quality Scale compliance, responsive CSS Container Queries, and full accessibility (a11y/WCAG) support!

---

## 🌟 What's New in v2.1.0

### 📐 1. Thermodynamic Mathematics & Correctness
* **Monotonic Energy Accumulation**: In cooling mode, heat gain integration is bounded to non-negative values (`max(0.0, p_gain)`). Heat loss when outdoor temperature is below indoor ($P_{\text{trans}} < 0$) is tracked separately in `p_loss`, preventing accumulators (`total_heat_absorbed`, `daily_heat_absorbed`) from falsely decreasing.
* **Continuous-Time $\tau$-based EMA**: Replaced sample-rate dependent exponential smoothing with continuous-time filter $\alpha = 1 - e^{-\Delta t / \tau}$ ($\tau = 300\text{s} / 900\text{s}$, $\Delta t \ge 15\text{s}$). High-frequency sensor bursts no longer skew building insulation $K$-factor calibration.
* **Sensor Burst Gating for $dT/dt$**: The rolling linear regression buffer for indoor temperature rate of change gates updates ($\Delta t \ge 20\text{s}$ or $|\Delta T| \ge 0.02^\circ\text{C}$), preventing sensor noise from exhausting the 10-minute historical regression window.
* **Calendar-Date Aware State Restoration**: Daily counters in `sensor.py` verify that the restored timestamp matches today's calendar date, cleanly zeroing counters after an overnight reboot.

### 🏛️ 2. Clean Architecture & Module Deepening
* **Extracted Pure Domain Engine (`engine.py`)**:
  * `ThermalHistoryTracker`: Pure Python linear regression, time-window cutoff (10 min), and update gating.
  * `InsulationCalibrator`: Continuous-time EMA, insulation grading ("Excellent", "Good", "Average", "Poor").
  * `EnergyAccumulator`: Riemann integration step, daily midnight reset boundaries, tariff and savings calculations.
  * `ClimateAdvisor`: Rule-based recommendation engine for window opening, curtain shading, and HVAC capacity warnings.
  * `ThermalEngine`: Pure domain orchestrator coordinating a single-pass calculation cycle and formatting typed outputs.
  * Meteorological Adapters: `parse_cloud_coverage`, `normalize_wind_speed`, `resolve_is_heating`, `resolve_curtains_closed`.
* **Lightweight Coordinator (`coordinator.py`)**:
  * Decomposed from 890 lines of mixed concerns into a thin Home Assistant event glue layer (~480 lines).
  * Retains 100% backward-compatible property accessors for entities, `diagnostics.py`, and service handlers.

### ⚡ 3. Lovelace Card Performance & Memory Leak Fixes
* **Elimination of ECharts Memory Leaks**:
  * Implemented `disconnectedCallback()` to properly call `this._chart.dispose()`, disconnect `ResizeObserver`, and remove window event listeners when cards are unmounted, edited, or tab-switched.
* **Single-Pass Persistent Shadow DOM Scaffolding**:
  * Completely eliminated `this.shadowRoot.innerHTML = ...` reconstruction on every sensor tick.
  * Cards scaffold once (`_createScaffold()`) and cache element handles (`_cacheElements()`).
  * In-place targeted updates: `_render()` updates text nodes (`textContent`) and SVG arc offsets (`strokeDashoffset`) directly without tearing down or reconstructing DOM nodes.
  * SVG gauges animate smoothly via CSS transitions (`transition: stroke-dashoffset 0.8s ease`).
  * ECharts canvas is reused via `echarts.getInstanceByDom(...)` and updated via `setOption(...)`.

### 🛡️ 4. Security & Home Assistant Quality Scale (Silver)
* **Stored DOM XSS Vulnerability Elimination**:
  * Implemented `escapeHtml(str)` utility and applied it across all user configuration fields, entity labels, custom card titles, and advice banners.
  * Header title and metric text updates use secure `.textContent`.
* **Strict Service Action Exceptions (`action-exceptions`)**:
  * Integration actions (`reset_accumulators`, `recalibrate_k_factor`, `calculate_cooling_needs`) raise `homeassistant.exceptions.ServiceValidationError` when an invalid `entry_id` or missing integration instance is provided.
* **Bilingual Exception Translations (`exception-translations`)**:
  * Added exception strings for `entry_not_found` and `no_instances` in `strings.json`, `translations/en.json`, and `translations/ru.json`.
* Marked `"quality_scale": "silver"` in `manifest.json`.

### 🎨 5. Modern UI/UX, Container Queries & Accessibility (a11y)
* **Automatic Responsive Container Queries (`@container tb-card (max-width: 480px)`)**:
  * Card automatically adapts into a single-column compact layout when placed in narrow dashboard columns (sidebar, mobile, 3–4 column grids) without requiring manual `compact: true`.
  * Metrics bar automatically switches to a clean 2x2 grid (`repeat(2, 1fr)`).
  * Energy cards grid automatically adapts to 3 or 2 columns.
* **Accessibility & Screen Reader Compliance (a11y)**:
  * Added `role="group"` and `role="img"` with dynamic `aria-label`s to SVG gauges (e.g. `aria-label="Heat Gain: 927 W"`).
  * Added `role="region" aria-live="polite" aria-atomic="true"` to `#tb-advice-container` for seamless announcement of window/curtain advice.
  * Added `role="list"` and `role="listitem"` with descriptive `aria-label`s to metrics and energy cards.
* **WCAG AA Color Contrast Compliance ($\ge 4.5:1$)**:
  * Replaced low-contrast `#6B7280` (< 3.2:1) with `#9CA3AF` (5.9:1) and `#D1D5DB` (10.4:1) across all labels, captions, and ECharts axis text.
* **Home Assistant Theme Variables Binding**:
  * Bound background, borders, and typography to `var(--ha-card-background)`, `var(--ha-card-background-subcard)`, `var(--primary-text-color)`, `var(--secondary-text-color)`, and `var(--divider-color)` with fallbacks.

### 🧪 6. Test Suite Expansion
* Expanded automated test suite to **65 unit tests** running in **0.044s** across 6 test modules (`test_model.py`, `test_engine.py`, `test_coordinator.py`, `test_config_flow.py`, `test_diagnostics.py`, `test_services.py`).

---

**Full Changelog**: https://github.com/ziffmafiya/thermal_balance/compare/v2.0.0...v2.1.0
