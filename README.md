# 🌡️ Thermal Balance — Home Assistant Custom Component & Premium Card

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/default)
[![version](https://img.shields.io/badge/version-v1.2.5-blue.svg)](https://github.com/ziffmafiya/thermal_balance/releases/latest)
[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?repository=https%3A%2F%2Fgithub.com%2Fziffmafiya%2Fthermal_balance&category=Integration)

**Thermal Balance** is a physics-based custom integration and Lovelace dashboard card for Home Assistant. It models room thermodynamics as an open system, calculating real-time heat gain, solar radiation, air conditioner cooling output, sensible/latent heat split, ventilation heat exchange, smart curtain shading, empirical $K$-factor auto-calibration, net energy balance, and temperature shift forecasts.

---

## 🌟 Key Features

* **☀️ Heat Gain ($P_{\text{gain}}$)**: Calculates solar radiation influx through windows and wall/glass thermal transmission ($P_{\text{wall}}$).
* **🪟 Smart Curtain Shading & Lux Sensor Integration**: Auto-detects open vs closed curtains via an indoor illuminance sensor (Lux). When curtains are closed, solar heat gain is automatically cut by 70% ($g_{\text{shading}} = 0.20$ vs $0.70$).
* **🌌 Dual Astronomical Daylight Integration**: Integrates Home Assistant's built-in `sun.sun` entity (state & elevation angle $>0^\circ$) and solar irradiance to distinguish daytime solar shading from nighttime indoor artificial lighting.
* **❄️ AC Cooling Output ($P_{\text{cooling}}$)**: Computes real-time cooling capacity (Watts), Carnot COP, Sensible Heat Ratio (SHR), exit air temperature at AC louvers, and condensation rate (L/h).
* **🧮 Empirical K-Factor Auto-Calibration ($HLC_{\text{empirical}}$)**: Exponential Moving Average (EMA) estimation of real-world room heat loss ($W/K$), deviation percentage from architectural specs, and insulation quality rating ("Отличная", "Хорошая", "Средняя", "Низкая"). Includes physical bounds ($0.5\times \dots 2.0\times HLC_{\text{theoretical}}$) and AC startup transient boost filtering.
* **🪟 Natural Ventilation Heat Exchange ($P_{\text{vent}}$)**: Tracks heat influx or natural cooling loss when windows are opened for ventilation. Automatically infers open window state when AC is off if no binary sensor is configured.
* **⚡ Net Power Balance ($P_{\text{net}}$)**: Instantaneous thermodynamic power balance ($P_{\text{env}} - P_{\text{cooling}}$).
* **⏱️ Temperature Forecast (Time to 1°C)**: Physics-based calculation of room thermal inertia predicting time to heat up (+1°C) or cool down (-1°C).
* **📊 Energy Accumulators**: Tracks daily net balance (resets at 00:00) and continuous lifetime energy balance ($E_{\text{total}}$).
* **📱 2-Column Responsive Lovelace Card**: Premium custom UI card (`custom:thermal-balance-card`) with CSS Container Queries (`@container`), live gauges, performance breakdown, and 24h interactive ECharts trend graphs.

---

## 📖 Complete Documentation

For detailed physics equations, configuration guide, card layout breakdown, and FAQ, read our [📖 GUIDE.md Documentation](GUIDE.md).

---

## 📁 Repository Structure

```
custom_components/thermal_balance/
├── __init__.py                # Integration setup & Lovelace resource registration
├── config_flow.py             # UI Configuration & Options Flow
├── const.py                   # Constants & sensor definitions
├── coordinator.py             # Thermodynamic calculations & state coordinator
├── sensor.py                  # Sensor entity definitions & state restoration
├── thermal-balance-card.js    # Premium 2-column Lovelace dashboard card
├── echarts.min.js             # Built-in ECharts graphing library
├── manifest.json              # Integration manifest
├── hacs.json                  # HACS configuration
├── strings.json               # UI Translation strings (En/Ru)
├── translations/
│   ├── en.json                # English UI translations
│   └── ru.json                # Russian UI translations
└── brand/                     # HACS Brand icons & logos
```

---

## 🚀 Installation

### Option 1: HACS (Recommended)

1. Open **HACS** $\rightarrow$ **Integrations** $\rightarrow$ **3 dots (top right)** $\rightarrow$ **Custom Repositories**.
2. Add Repository URL: `https://github.com/ziffmafiya/thermal_balance`
3. Category: **Integration**.
4. Click **Install**.
5. Restart Home Assistant.

### Option 2: Manual Installation

1. Copy the `custom_components/thermal_balance` directory into your Home Assistant `<config>/custom_components/` folder.
2. Restart Home Assistant.

---

## ⚙️ Setup & Configuration

1. In Home Assistant, go to **Settings** $\rightarrow$ **Devices & Services** $\rightarrow$ **Add Integration**.
2. Search for **Thermal Balance**.
3. Fill in room parameters (area $m^2$, ceiling height $m$, window area $m^2$, wall/window $U$-values).
4. Select your sensors:
   * **Required**: Indoor Temp, Outdoor Temp, Solar Radiation, AC Power.
   * **Optional**: Indoor Humidity, Outdoor Humidity, AC Outlet Temp, Window Contact, **Indoor Illuminance (Lux) Sensor** (for auto-shading).
5. Click **Submit**.

---

## 🎨 Lovelace Dashboard Card

Add the custom card to your dashboard:

```yaml
type: custom:thermal-balance-card
```

The card automatically discovers your Thermal Balance sensors and renders an interactive 2-column layout on desktop and tablet devices.

---

## 📄 License

MIT License © [ziffmafiya](https://github.com/ziffmafiya)
