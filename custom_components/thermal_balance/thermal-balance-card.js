/**
 * Thermal Balance Card — Premium Home Assistant Lovelace Card
 * Pure vanilla JS Custom Element with Visual UI Editor & Auto-Discovery
 *
 * Registered as: custom:thermal-balance-card
 * Editor registered as: thermal-balance-card-editor
 */

const SENSOR_MAP = {
  heat_gain: ['_instant_heat_gain', '_heat_gain', '_solar_heat_gain'],
  ac_cooling: ['_ac_heat_output', '_ac_cooling', '_heat_output'],
  net_balance: ['_instant_net_balance', '_net_balance'],
  ac_cop: ['_ac_carnot_cop', '_ac_cop', '_carnot_cop'],
  time_to_1c: ['_time_to_1deg', '_time_to_1_c', '_time_to_1'],
  daily_balance: ['_daily_thermal_balance', '_daily_balance'],
  total_balance: ['_net_thermal_balance', '_total_balance'],
  heat_absorbed: ['_total_heat_absorbed', '_heat_absorbed'],
  ac_energy: ['_ac_thermal_energy_total', '_ac_energy'],
  condensation_rate: ['_ac_condensation_rate', '_condensation_rate'],
  empirical_k_factor: ['_empirical_k_factor', '_empirical_room_k_factor', '_k_factor'],
};

function loadECharts() {
  if (window.echarts) return Promise.resolve(window.echarts);
  if (window._echartsLoadingPromise) return window._echartsLoadingPromise;

  window._echartsLoadingPromise = new Promise((resolve, reject) => {
    const script = document.createElement('script');
    script.src = '/thermal_balance/echarts.min.js';
    script.async = true;
    script.onload = () => resolve(window.echarts);
    script.onerror = () => {
      const script2 = document.createElement('script');
      script2.src = '/local/thermal_balance/echarts.min.js';
      script2.async = true;
      script2.onload = () => resolve(window.echarts);
      script2.onerror = (err) => reject(err);
      document.head.appendChild(script2);
    };
    document.head.appendChild(script);
  });
  return window._echartsLoadingPromise;
}

function autoDiscoverEntities(hass) {
  if (!hass || !hass.states) return {};
  const discovered = {};
  const allSensors = Object.keys(hass.states).filter(eid => eid.toLowerCase().startsWith('sensor.'));

  for (const [key, suffixes] of Object.entries(SENSOR_MAP)) {
    for (const eid of allSensors) {
      const lower = eid.toLowerCase();
      if (suffixes.some(suf => lower.endsWith(suf) || lower.includes(suf))) {
        discovered[key] = eid;
        break;
      }
    }
  }
  return discovered;
}

/* ─────────────────────────────────────────────────────────────
 * VISUAL UI EDITOR CLASS
 * ───────────────────────────────────────────────────────────── */

class ThermalBalanceCardEditor extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._config = {};
    this._hass = null;
  }

  setConfig(config) {
    this._config = { ...config };
    this.render();
  }

  set hass(hass) {
    this._hass = hass;
    this.render();
  }

  connectedCallback() {
    this.render();
  }

  _valueChanged(ev) {
    if (!this._config) return;
    const target = ev.target;
    const configKey = target.getAttribute('configValue');
    if (!configKey) return;

    const newValue = ev.detail ? ev.detail.value : target.value;
    if (this._config[configKey] === newValue) return;

    const newConfig = { ...this._config };
    if (newValue === '' || newValue === undefined) {
      delete newConfig[configKey];
    } else {
      newConfig[configKey] = newValue;
    }

    this._config = newConfig;
    const event = new CustomEvent('config-changed', {
      detail: { config: this._config },
      bubbles: true,
      composed: true,
    });
    this.dispatchEvent(event);
  }

  render() {
    const auto = autoDiscoverEntities(this._hass);
    const fields = [
      { key: 'heat_gain', label: 'Heat Gain Sensor' },
      { key: 'ac_cooling', label: 'AC Cooling Sensor' },
      { key: 'net_balance', label: 'Net Balance Sensor' },
      { key: 'ac_cop', label: 'AC COP Sensor' },
      { key: 'time_to_1c', label: 'Time to 1°C Sensor' },
      { key: 'daily_balance', label: 'Daily Balance Sensor' },
      { key: 'total_balance', label: 'Total Balance Sensor' },
      { key: 'heat_absorbed', label: 'Heat Absorbed Sensor' },
      { key: 'ac_energy', label: 'AC Energy Sensor' },
      { key: 'condensation_rate', label: 'Condensation Rate Sensor' },
    ];

    const sensorEntities = (this._hass && this._hass.states)
      ? Object.keys(this._hass.states)
          .filter(e => e.startsWith('sensor.'))
          .map(eid => {
            const stateObj = this._hass.states[eid];
            const fname = (stateObj && stateObj.attributes && stateObj.attributes.friendly_name);
            const name = fname ? `${fname} (${eid})` : eid;
            return { eid, name };
          })
          .sort((a, b) => a.name.localeCompare(b.name))
      : [];

    const getAutoLabel = (key) => {
      const eid = auto[key];
      if (!eid) return 'None';
      const stateObj = this._hass && this._hass.states && this._hass.states[eid];
      const fname = stateObj && stateObj.attributes && stateObj.attributes.friendly_name;
      return fname ? `${fname} (${eid})` : eid;
    };

    const fieldsHtml = fields.map(f => {
      const currentVal = this._config[f.key] || auto[f.key] || '';
      return `
        <div class="editor-row">
          <label class="editor-label">${f.label}</label>
          <select class="editor-select" configValue="${f.key}">
            <option value="">-- Auto-discovered: ${getAutoLabel(f.key)} --</option>
            ${sensorEntities.map(opt => `
              <option value="${opt.eid}" ${opt.eid === currentVal ? 'selected' : ''}>${opt.name}</option>
            `).join('')}
          </select>
        </div>
      `;
    }).join('');

    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          padding: 12px;
          color: var(--primary-text-color, #fff);
          font-family: inherit;
          box-sizing: border-box;
        }
        .editor-container {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }
        .editor-title {
          font-weight: 600;
          font-size: 14px;
          margin-bottom: 4px;
          color: var(--secondary-text-color, #aaa);
        }
        .editor-row {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }
        .editor-label {
          font-size: 12px;
          color: var(--secondary-text-color, #ccc);
        }
        .editor-select {
          background: var(--card-background-color, #1c2538);
          color: var(--primary-text-color, #fff);
          border: 1px solid var(--divider-color, rgba(255,255,255,0.1));
          border-radius: 6px;
          padding: 8px 10px;
          font-size: 13px;
          font-family: inherit;
          width: 100%;
        }
        .editor-select:focus {
          outline: none;
          border-color: var(--primary-color, #03a9f4);
        }
      </style>
      <div class="editor-container">
        <div class="editor-title">Thermal Balance Sensors Configuration</div>
        ${fieldsHtml}
      </div>
    `;

    const selects = this.shadowRoot.querySelectorAll('.editor-select');
    selects.forEach(s => {
      s.addEventListener('change', this._valueChanged.bind(this));
    });
  }
}

if (!customElements.get('thermal-balance-card-editor')) {
  customElements.define('thermal-balance-card-editor', ThermalBalanceCardEditor);
}

/* ─────────────────────────────────────────────────────────────
 * MAIN LOVELACE CARD CLASS
 * ───────────────────────────────────────────────────────────── */

class ThermalBalanceCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this._hass = null;
    this._config = {};
    this._lastHash = '';
  }

  static getConfigElement() {
    return document.createElement('thermal-balance-card-editor');
  }

  static getStubConfig(hass) {
    return autoDiscoverEntities(hass);
  }

  setConfig(config) {
    if (!config) throw new Error('Invalid configuration');
    this._config = { ...config };
    this._lastHash = '';
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  connectedCallback() {
    this._render();
  }

  getCardSize() {
    return 6;
  }

  /* ─── Helpers for Entity Resolution ─── */

  _resolveEntity(key) {
    if (this._config && this._config[key]) return this._config[key];
    if (!this._autoDiscovered && this._hass) {
      this._autoDiscovered = autoDiscoverEntities(this._hass);
    }
    return this._autoDiscovered ? this._autoDiscovered[key] : null;
  }

  _getState(key) {
    const eid = this._resolveEntity(key);
    if (!eid || !this._hass || !this._hass.states) return null;
    const s = this._hass.states[eid];
    if (!s || s.state === 'unavailable' || s.state === 'unknown') return null;
    return parseFloat(s.state);
  }

  _getAttr(key, attr) {
    const eid = this._resolveEntity(key);
    if (!eid || !this._hass || !this._hass.states) return null;
    const s = this._hass.states[eid];
    if (!s || !s.attributes) return null;
    const v = s.attributes[attr];
    return v === undefined ? null : v;
  }

  _fmt(v, decimals = 0) {
    if (v === null || v === undefined || isNaN(v)) return '—';
    return Number(v).toLocaleString(undefined, {
      minimumFractionDigits: decimals,
      maximumFractionDigits: decimals,
    });
  }

  _fmtTime(val, direction) {
    if (val === null || val === undefined) return '—';
    const m = Math.round(val);
    if (m === 0 && direction === 'equilibrium') return 'Stable';
    if (m >= 60) {
      const h = Math.floor(m / 60);
      const rm = m % 60;
      return rm > 0 ? `${h}h ${rm}m` : `${h}h`;
    }
    return `${m} min`;
  }

  _balanceColor(v) {
    if (v === null || v === undefined || isNaN(v)) return '#00C896';
    if (v > 50) return '#FF7A3C';
    if (v < -50) return '#4DA3FF';
    return '#00C896';
  }

  _balanceBg(v) {
    if (v === null || v === undefined || isNaN(v)) return 'rgba(0, 200, 150, 0.15)';
    if (v > 50) return 'rgba(255, 122, 60, 0.15)';
    if (v < -50) return 'rgba(77, 163, 255, 0.15)';
    return 'rgba(0, 200, 150, 0.15)';
  }

  _dirIcon(dir) {
    if (dir === 'heating') return { sym: '▲', color: '#FF7A3C' };
    if (dir === 'cooling') return { sym: '▼', color: '#4DA3FF' };
    return { sym: '⚖', color: '#00C896' };
  }

  /* ─── SVG Gauge ─── */

  _gauge(value, max, color1, color2, label, iconSvg) {
    const r = 55;
    const circumference = Math.PI * r;
    const pct = Math.min(1, Math.max(0, (value || 0) / max));
    const offset = circumference * (1 - pct);
    const display = value !== null ? this._fmt(value, 0) : '—';
    const gradId = `grad-${label.replace(/[^a-zA-Z0-9]/g, '')}`;

    return `
      <div class="gauge-card">
        <svg viewBox="0 0 140 85" class="gauge-svg">
          <defs>
            <linearGradient id="${gradId}" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stop-color="${color1}"/>
              <stop offset="100%" stop-color="${color2}"/>
            </linearGradient>
          </defs>
          <path d="M 15 72 A 55 55 0 0 1 125 72"
                fill="none" stroke="rgba(255,255,255,0.05)" stroke-width="8" stroke-linecap="round"/>
          <path d="M 15 72 A 55 55 0 0 1 125 72"
                fill="none" stroke="url(#${gradId})" stroke-width="8" stroke-linecap="round"
                stroke-dasharray="${circumference}" stroke-dashoffset="${offset}"
                style="transition: stroke-dashoffset 0.8s ease"/>
          <text x="70" y="58" text-anchor="middle" fill="#E5E7EB" font-size="22" font-weight="700" font-family="inherit">${display}</text>
          <text x="70" y="74" text-anchor="middle" fill="#6B7280" font-size="11" font-family="inherit">W</text>
        </svg>
        <div class="gauge-label">
          <span class="gauge-icon">${iconSvg}</span>
          <span>${label}</span>
        </div>
      </div>`;
  }

  get _icons() {
    return {
      sun: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#FF7A3C" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>`,
      snowflake: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#4DA3FF" stroke-width="2" stroke-linecap="round"><line x1="12" y1="2" x2="12" y2="22"/><line x1="2" y1="12" x2="22" y2="12"/><line x1="5.5" y1="5.5" x2="18.5" y2="18.5"/><line x1="18.5" y1="5.5" x2="5.5" y2="18.5"/><polyline points="8,2 12,6 16,2"/><polyline points="8,22 12,18 16,22"/><polyline points="2,8 6,12 2,16"/><polyline points="22,8 18,12 22,16"/></svg>`,
      snowflakeLg: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#4DA3FF" stroke-width="2" stroke-linecap="round"><line x1="12" y1="2" x2="12" y2="22"/><line x1="2" y1="12" x2="22" y2="12"/><line x1="5.5" y1="5.5" x2="18.5" y2="18.5"/><line x1="18.5" y1="5.5" x2="5.5" y2="18.5"/><polyline points="8,2 12,6 16,2"/><polyline points="8,22 12,18 16,22"/><polyline points="2,8 6,12 2,16"/><polyline points="22,8 18,12 22,16"/></svg>`,
      thermo: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#E5E7EB" stroke-width="2" stroke-linecap="round"><path d="M14 14.76V3.5a2.5 2.5 0 0 0-5 0v11.26a4.5 4.5 0 1 0 5 0z"/></svg>`,
      bolt: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#FACC15" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>`,
      trend: `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#FF7A3C" stroke-width="2" stroke-linecap="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>`,
    };
  }

  /* ─── 24h History Trend Sparkline ─── */

  _fetchHistory() {
    if (!this._hass || this._fetchingHistory) return;
    const now = Date.now();
    if (this._lastHistoryFetch && (now - this._lastHistoryFetch < 300000)) return;
    this._fetchingHistory = true;
    this._lastHistoryFetch = now;

    const heatEid = this._resolveEntity('heat_gain');
    const coolEid = this._resolveEntity('ac_cooling');
    const netEid = this._resolveEntity('net_balance');
    if (!heatEid && !coolEid && !netEid) {
      this._fetchingHistory = false;
      return;
    }

    const entityIds = [heatEid, coolEid, netEid].filter(Boolean);
    const startTime = new Date(now - 24 * 3600 * 1000).toISOString();

    this._hass.callWS({
      type: 'history/history_during_period',
      start_time: startTime,
      entity_ids: entityIds,
      no_attributes: true,
      minimal_response: true,
    }).then(res => {
      this._fetchingHistory = false;
      this._historyData = res || {};
      this._render();
    }).catch(() => {
      this._fetchingHistory = false;
    });
  }

  _sampleHistory(key, liveVal, numPoints = 288) {
    const eid = this._resolveEntity(key);
    if (!eid || !this._historyData || !this._historyData[eid]) {
      return null;
    }

    const items = this._historyData[eid];
    if (!Array.isArray(items) || items.length === 0) {
      return null;
    }

    const result = new Array(numPoints).fill(0);
    const now = Date.now() / 1000;
    const start = now - 86400;
    const interval = 86400 / (numPoints - 1);

    let currentVal = parseFloat(items[0].s);
    if (isNaN(currentVal)) currentVal = 0;
    let itemIdx = 0;

    for (let i = 0; i < numPoints; i++) {
      const targetTime = start + (i * interval);

      while (itemIdx < items.length) {
        const item = items[itemIdx];
        const itemTime = item.lu > 1e11 ? item.lu / 1000 : item.lu;
        if (itemTime <= targetTime) {
          const parsed = parseFloat(item.s);
          if (!isNaN(parsed)) currentVal = parsed;
          itemIdx++;
        } else {
          break;
        }
      }
      result[i] = currentVal;
    }

    if (liveVal !== null && liveVal !== undefined && !isNaN(liveVal)) {
      result[numPoints - 1] = liveVal;
    }

    return result;
  }

  _smoothPoints(pts) {
    if (!pts || pts.length < 3) return pts;
    const len = pts.length;
    const smoothed = new Array(len);
    smoothed[0] = pts[0];
    for (let i = 1; i < len - 1; i++) {
      smoothed[i] = 0.20 * pts[i - 1] + 0.60 * pts[i] + 0.20 * pts[i + 1];
    }
    smoothed[len - 1] = pts[len - 1];
    return smoothed;
  }

  _getTrendPoints(key, liveVal, numPoints = 288) {
    const raw = this._sampleHistory(key, liveVal, numPoints);
    if (!raw) return null;
    return this._smoothPoints(raw);
  }

  _pointsToPath(points, width, height, maxVal) {
    if (!points || points.length === 0) return '';
    const step = width / Math.max(1, points.length - 1);
    const maxY = maxVal > 0 ? maxVal : 100;

    const coords = points.map((val, idx) => {
      const x = idx * step;
      const y = height - (Math.min(maxY, Math.max(0, val)) / maxY) * (height - 8) - 4;
      return { x, y };
    });

    if (coords.length === 1) return `M 0 ${coords[0].y} L ${width} ${coords[0].y}`;

    let d = `M ${coords[0].x.toFixed(1)} ${coords[0].y.toFixed(1)}`;
    for (let i = 0; i < coords.length - 1; i++) {
      const p0 = coords[i];
      const p1 = coords[i + 1];
      const cp1x = (p0.x + (p1.x - p0.x) / 2).toFixed(1);
      const cp1y = p0.y.toFixed(1);
      const cp2x = cp1x;
      const cp2y = p1.y.toFixed(1);
      d += ` C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${p1.x.toFixed(1)} ${p1.y.toFixed(1)}`;
    }
    return d;
  }

  _pointsToArea(points, width, height, maxVal) {
    const linePath = this._pointsToPath(points, width, height, maxVal);
    if (!linePath) return '';
    return `${linePath} L ${width} ${height} L 0 ${height} Z`;
  }

  _renderTrendSvg(heatPoints, coolPoints) {
    if (!heatPoints && !coolPoints) return '';
    const width = 300;
    const height = 65;
    const all = [...(heatPoints || []), ...(coolPoints || [])];
    const maxVal = Math.max(500, ...all);

    const heatLine = this._pointsToPath(heatPoints, width, height, maxVal);
    const heatArea = this._pointsToArea(heatPoints, width, height, maxVal);

    const coolLine = this._pointsToPath(coolPoints, width, height, maxVal);
    const coolArea = this._pointsToArea(coolPoints, width, height, maxVal);

    return `
      <svg viewBox="0 0 ${width} ${height}" class="trend-svg" preserveAspectRatio="none">
        <defs>
          <linearGradient id="heatTrendGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#FF7A3C" stop-opacity="0.35"/>
            <stop offset="100%" stop-color="#FF7A3C" stop-opacity="0.0"/>
          </linearGradient>
          <linearGradient id="coolTrendGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#4DA3FF" stop-opacity="0.35"/>
            <stop offset="100%" stop-color="#4DA3FF" stop-opacity="0.0"/>
          </linearGradient>
        </defs>
        <!-- Grid lines -->
        <line x1="0" y1="15" x2="${width}" y2="15" stroke="#1C2538" stroke-dasharray="3 3"/>
        <line x1="0" y1="45" x2="${width}" y2="45" stroke="#1C2538" stroke-dasharray="3 3"/>

        ${heatArea ? `<path d="${heatArea}" fill="url(#heatTrendGrad)"/>` : ''}
        ${coolArea ? `<path d="${coolArea}" fill="url(#coolTrendGrad)"/>` : ''}
        ${heatLine ? `<path d="${heatLine}" fill="none" stroke="#FF7A3C" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>` : ''}
        ${coolLine ? `<path d="${coolLine}" fill="none" stroke="#4DA3FF" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>` : ''}
      </svg>
    `;
  }

  _initEChart() {
    const container = this.shadowRoot ? this.shadowRoot.querySelector('#echart-container') : null;
    if (!container) return;

    loadECharts().then(echarts => {
      if (!this.shadowRoot || !this.shadowRoot.querySelector('#echart-container')) return;
      if (this._chart && !this._chart.isDisposed()) {
        try { this._chart.dispose(); } catch(e){}
      }

      const numPoints = 288;
      const heatPoints = this._getTrendPoints('heat_gain', this._getState('heat_gain'), numPoints);
      const coolPoints = this._getTrendPoints('ac_cooling', this._getState('ac_cooling'), numPoints);
      const netPoints = this._getTrendPoints('net_balance', this._getState('net_balance'), numPoints);

      if (!heatPoints && !coolPoints && !netPoints) {
        return;
      }

      this._chart = echarts.init(container, null, { renderer: 'canvas' });

      const numPoints = 288;
      const heatPoints = this._getTrendPoints('heat_gain', this._getState('heat_gain'), numPoints);
      const coolPoints = this._getTrendPoints('ac_cooling', this._getState('ac_cooling'), numPoints);
      const netPoints = this._getTrendPoints('net_balance', this._getState('net_balance'), numPoints);

      const nowMs = Date.now();
      const startMs = nowMs - 86400000;
      const intervalMs = 86400000 / (numPoints - 1);

      const timeLabels = Array.from({ length: numPoints }, (_, i) => {
        const ptTime = new Date(startMs + i * intervalMs);
        const hh = ptTime.getHours().toString().padStart(2, '0');
        const mm = ptTime.getMinutes().toString().padStart(2, '0');
        return `${hh}:${mm}`;
      });

      const option = {
        backgroundColor: 'transparent',
        legend: {
          show: true,
          top: 0,
          right: 10,
          textStyle: { color: '#9CA3AF', fontSize: 10 },
          itemWidth: 10,
          itemHeight: 6,
          data: ['Heat', 'Cooling', 'Net']
        },
        tooltip: {
          trigger: 'axis',
          backgroundColor: '#121A2B',
          borderColor: '#233045',
          borderWidth: 1,
          padding: [8, 12],
          textStyle: { color: '#E5E7EB', fontSize: 11 },
          formatter: (params) => {
            let res = `<div style="font-weight:600;margin-bottom:4px;color:#9CA3AF">${params[0].name}</div>`;
            params.forEach(p => {
              const sign = p.value > 0 ? '+' : '';
              res += `<div style="display:flex;align-items:center;gap:6px;margin-top:2px">
                        <span style="width:8px;height:8px;border-radius:50%;background:${p.color}"></span>
                        <span>${p.seriesName}: <b style="color:#FFF">${sign}${Math.round(p.value)} W</b></span>
                      </div>`;
            });
            return res;
          }
        },
        grid: {
          top: 25,
          right: 10,
          bottom: 22,
          left: 45,
        },
        xAxis: {
          type: 'category',
          boundaryGap: false,
          data: timeLabels,
          axisLine: { lineStyle: { color: '#233045' } },
          axisLabel: { color: '#6B7280', fontSize: 10, interval: 35 },
          splitLine: { show: false }
        },
        yAxis: {
          type: 'value',
          axisLine: { show: false },
          axisLabel: { color: '#6B7280', fontSize: 10, formatter: '{value} W' },
          splitLine: { lineStyle: { color: '#1C2538' } }
        },
        series: [
          {
            name: 'Heat',
            type: 'line',
            smooth: 0.3,
            smoothMonotone: 'x',
            sampling: 'lttb',
            showSymbol: false,
            symbol: 'circle',
            symbolSize: 6,
            itemStyle: { color: '#FF7A3C' },
            lineStyle: { width: 2.0, color: '#FF7A3C' },
            areaStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: 'rgba(255, 122, 60, 0.25)' },
                { offset: 1, color: 'rgba(255, 122, 60, 0.0)' }
              ])
            },
            data: heatPoints.map(v => Math.round(v))
          },
          {
            name: 'Cooling',
            type: 'line',
            smooth: 0.3,
            smoothMonotone: 'x',
            sampling: 'lttb',
            showSymbol: false,
            symbol: 'circle',
            symbolSize: 6,
            itemStyle: { color: '#4DA3FF' },
            lineStyle: { width: 2.0, color: '#4DA3FF' },
            areaStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: 'rgba(77, 163, 255, 0.25)' },
                { offset: 1, color: 'rgba(77, 163, 255, 0.0)' }
              ])
            },
            data: coolPoints.map(v => Math.round(v))
          },
          {
            name: 'Net',
            type: 'line',
            smooth: 0.3,
            smoothMonotone: 'x',
            sampling: 'lttb',
            showSymbol: false,
            symbol: 'circle',
            symbolSize: 6,
            itemStyle: { color: '#00C896' },
            lineStyle: { width: 2.2, color: '#00C896', type: 'dashed' },
            areaStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: 'rgba(0, 200, 150, 0.15)' },
                { offset: 1, color: 'rgba(0, 200, 150, 0.0)' }
              ])
            },
            data: netPoints.map(v => Math.round(v))
          }
        ]
      };

      this._chart.setOption(option);
      setTimeout(() => this._chart && this._chart.resize(), 50);
    }).catch(() => {});
  }

  /* ─── Render ─── */

  _render() {
    try {
      if (!this._hass || !this._hass.states) {
        this._renderPreview();
        return;
      }

      this._autoDiscovered = autoDiscoverEntities(this._hass);

      const keys = Object.keys(SENSOR_MAP);
      const parts = keys.map(k => {
        const eid = this._resolveEntity(k);
        if (!eid) return '';
        const s = this._hass.states[eid];
        if (!s) return '';
        return `${eid}=${s.state}|${JSON.stringify(s.attributes)}`;
      });
      const hash = parts.join(';;');
      if (hash === this._lastHash && this.shadowRoot && this.shadowRoot.innerHTML !== '') return;
      this._lastHash = hash;

      // Read values
      const heatGain = this._getState('heat_gain');
      const acCooling = this._getState('ac_cooling');
      const netBalance = this._getState('net_balance');
      const cop = this._getState('ac_cop');
      const time1c = this._getState('time_to_1c');
      const dailyBal = this._getState('daily_balance');
      const totalBal = this._getState('total_balance');
      const heatAbsorbed = this._getState('heat_absorbed');
      const acEnergy = this._getState('ac_energy');
      const condensation = this._getState('condensation_rate');

      // AC cooling attributes
      const deltaT = this._getAttr('ac_cooling', 'delta_t_ac_c');
      const exitTemp = this._getAttr('ac_cooling', 'ac_exit_temperature_c');
      const calcExitTemp = this._getAttr('ac_cooling', 'ac_calc_exit_temperature_c');
      const hasMeasured = this._getAttr('ac_cooling', 'has_measured_exit_sensor');
      const sensible = this._getAttr('ac_cooling', 'sensible_cooling_w');
      const latent = this._getAttr('ac_cooling', 'latent_cooling_w');
      const shr = this._getAttr('ac_cooling', 'shr_percent');
      const enthalpy = this._getAttr('ac_cooling', 'air_enthalpy_in_kj_kg');
      const airflow = this._getAttr('ac_cooling', 'ac_airflow_m3h');
      const dewIn = this._getAttr('ac_cooling', 'indoor_dew_point_c');
      const dewOut = this._getAttr('ac_cooling', 'outdoor_dew_point_c');

      // Ventilation & Thermal sources attributes
      const pVent = this._getAttr('heat_gain', 'p_vent_w') ?? this._getAttr('net_balance', 'p_vent_w');
      const pSolar = this._getAttr('heat_gain', 'p_solar_w');
      const pWall = this._getAttr('heat_gain', 'p_wall_w');
      const windowOpen = this._getAttr('heat_gain', 'window_is_open') ?? this._getAttr('net_balance', 'window_is_open');

      // Empirical K-Factor attributes
      const empiricalK = this._getState('empirical_k_factor') ?? this._getAttr('heat_gain', 'hlc_w_k');
      const empiricalKDev = this._getAttr('empirical_k_factor', 'deviation_percent');
      const empiricalKGrade = this._getAttr('empirical_k_factor', 'insulation_grade');
      const empiricalKAuto = this._getAttr('empirical_k_factor', 'auto_calibrated');

      // Curtains & Shading attributes
      const curtainsClosed = this._getAttr('heat_gain', 'curtains_closed');
      const curtainsState = this._getAttr('heat_gain', 'curtains_state');
      const illuminanceLux = this._getAttr('heat_gain', 'illuminance_lux');

      // time_to_1c attributes
      const direction = this._getAttr('time_to_1c', 'direction') || 'equilibrium';
      const dirInfo = this._dirIcon(direction);

      // Colors & formatting
      const balColor = this._balanceColor(netBalance);
      const balBg = this._balanceBg(netBalance);
      const dailyColor = this._balanceColor(dailyBal);
      const timeDisplay = this._fmtTime(time1c, direction);

      const ventColor = windowOpen ? (pVent > 20 ? '#FF7A3C' : (pVent < -20 ? '#4DA3FF' : '#00C896')) : '#6B7280';
      const ventValText = !windowOpen ? 'Закрыто (0 W)' : (pVent !== null && pVent !== undefined ? (pVent > 0 ? '+' : '') + this._fmt(pVent, 0) + ' W' : '—');

      const copText = cop !== null ? `COP ${this._fmt(cop, 2)}` : '';
      const shrText = shr !== null ? `SHR ${this._fmt(shr, 0)}%` : '';
      const ventHeaderBadge = windowOpen ? (pVent !== null ? (pVent >= 0 ? `🪟 +${Math.round(pVent)}W` : `🪟 ${Math.round(pVent)}W`) : '🪟 Открыто') : '🪟 Закрыто';
      const subtitle = [copText, shrText, ventHeaderBadge].filter(Boolean).join(' · ');

      const acRows = [
        { label: 'ΔT AC', value: deltaT, unit: '°C', dec: 1, color: '#374151' },
        { label: hasMeasured ? 'Exit Temp (Meas)' : 'Exit Temp', value: exitTemp, unit: '°C', dec: 1, color: hasMeasured ? '#4DA3FF' : '#374151' },
        ...(hasMeasured ? [{ label: 'Exit Temp (Calc)', value: calcExitTemp, unit: '°C', dec: 1, color: '#FACC15' }] : []),
        { label: 'Sensible', value: sensible, unit: 'W', dec: 0, color: '#374151' },
        { label: 'Latent', value: latent, unit: 'W', dec: 0, color: '#374151' },
        { label: 'SHR', value: shr, unit: '%', dec: 1, color: '#374151' },
        { label: 'Enthalpy', value: enthalpy, unit: 'kJ/kg', dec: 1, color: '#374151' },
        { label: 'Airflow', value: airflow, unit: 'm³/h', dec: 0, color: '#00C896' },
        { label: 'Dew Pt In', value: dewIn, unit: '°C', dec: 1, color: '#4DA3FF' },
        { label: 'Dew Pt Out', value: dewOut, unit: '°C', dec: 1, color: '#4DA3FF' },
      ];

      // Fetch history asynchronously
      this._fetchHistory();

      const heatPoints = this._getTrendPoints('heat_gain', heatGain);
      const coolPoints = this._getTrendPoints('ac_cooling', acCooling);
      const trendSvg = this._renderTrendSvg(heatPoints, coolPoints);

      const acRowsHtml = acRows.map(r => `
        <div class="ac-row">
          <span class="ac-dot" style="background:${r.color}"></span>
          <span class="ac-label">${r.label}</span>
          <span class="ac-val">${r.value !== null && r.value !== undefined ? this._fmt(r.value, r.dec) : '—'} <span class="ac-unit">${r.value !== null && r.value !== undefined ? r.unit : ''}</span></span>
        </div>`).join('');

      this.shadowRoot.innerHTML = `
        <style>${this._css()}</style>
        <ha-card>
          <div class="tb-card">
            <div class="card-layout">

              <!-- COLUMN 1: Thermal Balance, Gauges, Metrics, Ventilation & AC Performance -->
              <div class="card-col col-left">
                <!-- HEADER -->
                <div class="header">
                  <div class="header-left">
                    <div class="header-icon">${this._icons.thermo}</div>
                    <div class="header-text">
                      <div class="header-title">Thermal Balance</div>
                      ${subtitle ? `<div class="header-sub">${subtitle}</div>` : ''}
                    </div>
                  </div>
                  <div class="header-badge" style="background:rgba(139, 92, 246, 0.15); color:#8B5CF6; border:1px solid rgba(139, 92, 246, 0.3)">
                    ${netBalance !== null ? (netBalance > 0 ? '+' : '') + this._fmt(netBalance, 0) : '—'} W
                  </div>
                </div>

                <!-- GAUGES -->
                <div class="gauges-row">
                  ${this._gauge(heatGain, 3500, '#FF7A3C', '#FFB199', 'Heat Gain', this._icons.sun)}
                  ${this._gauge(acCooling, 3500, '#4DA3FF', '#93C5FD', 'AC Cooling', this._icons.snowflake)}
                </div>

                <!-- METRICS BAR -->
                <div class="metrics-bar">
                  <div class="metric-block">
                    <div class="metric-icon" style="color:#8B5CF6">⚡</div>
                    <div class="metric-val" style="color:#8B5CF6">${netBalance !== null ? (netBalance > 0 ? '+' : '') + this._fmt(netBalance, 0) : '—'} <span class="metric-unit">W</span></div>
                    <div class="metric-label">Net Balance</div>
                  </div>
                  <div class="metric-block">
                    <div class="metric-icon" style="color:${ventColor}">🪟</div>
                    <div class="metric-val" style="color:${ventColor}">${pVent !== null && pVent !== undefined && windowOpen ? (pVent > 0 ? '+' : '') + this._fmt(pVent, 0) : (windowOpen ? '0' : 'Off')} <span class="metric-unit">${windowOpen ? 'W' : ''}</span></div>
                    <div class="metric-label">Ventilation</div>
                  </div>
                  <div class="metric-block">
                    <div class="metric-icon" style="color:#FACC15">${dirInfo.sym}</div>
                    <div class="metric-val" style="color:#FACC15">${timeDisplay}</div>
                    <div class="metric-label">To 1°C</div>
                  </div>
                  <div class="metric-block">
                    <div class="metric-icon" style="color:#93C5FD">💧</div>
                    <div class="metric-val" style="color:#93C5FD">${condensation !== null ? this._fmt(condensation, 2) : '—'} <span class="metric-unit">L/h</span></div>
                    <div class="metric-label">Condensation</div>
                  </div>
                </div>

                <!-- VENTILATION & THERMAL SOURCES -->
                <div class="section">
                  <div class="section-title">🪟 <span>Ventilation & Heat Exchange</span></div>
                  <div class="ac-grid">
                    <div class="ac-row">
                      <span class="ac-dot" style="background:${windowOpen ? '#FF7A3C' : '#6B7280'}"></span>
                      <span class="ac-label">Окно (Window)</span>
                      <span class="ac-val" style="color:${windowOpen ? '#FF7A3C' : '#00C896'}">${windowOpen ? 'Открыто (Open)' : 'Закрыто (Closed)'}</span>
                    </div>
                    <div class="ac-row">
                      <span class="ac-dot" style="background:${ventColor}"></span>
                      <span class="ac-label">Проветривание (Vent)</span>
                      <span class="ac-val" style="color:${ventColor}">${ventValText}</span>
                    </div>
                    ${curtainsState !== null && curtainsState !== undefined ? `
                    <div class="ac-row">
                      <span class="ac-dot" style="background:${curtainsClosed ? '#8B5CF6' : '#FF7A3C'}"></span>
                      <span class="ac-label">Шторы (Curtains)</span>
                      <span class="ac-val" style="color:${curtainsClosed ? '#8B5CF6' : '#FF7A3C'}">${curtainsClosed ? 'Зашторены (-70%)' : 'Открыты'} ${illuminanceLux !== null && illuminanceLux !== undefined ? '<span class="ac-unit">(' + Math.round(illuminanceLux) + ' lx)</span>' : ''}</span>
                    </div>
                    ` : ''}
                    <div class="ac-row">
                      <span class="ac-dot" style="background:#FACC15"></span>
                      <span class="ac-label">Солнце (Solar)</span>
                      <span class="ac-val">${pSolar !== null && pSolar !== undefined ? '+' + this._fmt(pSolar, 0) + ' W' : '—'}</span>
                    </div>
                    <div class="ac-row">
                      <span class="ac-dot" style="background:#8B5CF6"></span>
                      <span class="ac-label">Стены/Окна (Walls)</span>
                      <span class="ac-val">${pWall !== null && pWall !== undefined ? (pWall > 0 ? '+' : '') + this._fmt(pWall, 0) + ' W' : '—'}</span>
                    </div>
                    <div class="ac-row">
                      <span class="ac-dot" style="background:#00C896"></span>
                      <span class="ac-label">K-Фактор (Факт)</span>
                      <span class="ac-val" style="color:#00C896">${empiricalK !== null ? this._fmt(empiricalK, 1) + ' W/K' : '—'} <span class="ac-unit">${empiricalKDev !== null ? '(' + (empiricalKDev > 0 ? '+' : '') + this._fmt(empiricalKDev, 0) + '%)' : ''}</span></span>
                    </div>
                    <div class="ac-row">
                      <span class="ac-dot" style="background:#3B82F6"></span>
                      <span class="ac-label">Изоляция</span>
                      <span class="ac-val" style="font-size: 0.85em; color: #9CA3AF;">${empiricalKGrade || 'Расчётная'}</span>
                    </div>
                  </div>
                </div>

                <!-- AC PERFORMANCE -->
                <div class="section">
                  <div class="section-title">${this._icons.snowflakeLg} <span>AC Performance</span></div>
                  <div class="ac-grid">${acRowsHtml}</div>
                </div>
              </div>

              <!-- COLUMN 2: 24h Trend Chart & Energy Accumulators -->
              <div class="card-col col-right">
                <!-- 24H ECHARTS TREND -->
                <div class="section">
                  <div class="section-title">
                    ${this._icons.trend}
                    <span>24h Thermal Trend</span>
                    <div class="trend-legend">
                      <span class="legend-item"><span class="legend-dot" style="background:#FF7A3C"></span>Heat</span>
                      <span class="legend-item"><span class="legend-dot" style="background:#4DA3FF"></span>Cooling</span>
                    </div>
                  </div>
                  <div id="echart-container" style="width: 100%; height: 200px; margin-top: 4px;">${trendSvg}</div>
                </div>

                <!-- ENERGY -->
                <div class="section">
                  <div class="section-title">${this._icons.bolt} <span>Energy</span></div>
                  <div class="energy-grid">
                    <div class="energy-card">
                      <div class="energy-icon" style="color:${dailyColor}">📅</div>
                      <div class="energy-val" style="color:${dailyColor}">${dailyBal !== null ? this._fmt(dailyBal, 1) : '—'}</div>
                      <div class="energy-unit">kWh</div>
                      <div class="energy-label">Daily Balance</div>
                    </div>
                    <div class="energy-card">
                      <div class="energy-icon" style="color:#8B5CF6">Σ</div>
                      <div class="energy-val" style="color:#8B5CF6">${totalBal !== null ? this._fmt(totalBal, 1) : '—'}</div>
                      <div class="energy-unit">kWh</div>
                      <div class="energy-label">Total Balance</div>
                    </div>
                    <div class="energy-card">
                      <div class="energy-icon" style="color:#FF7A3C">🔥</div>
                      <div class="energy-val" style="color:#FF7A3C">${heatAbsorbed !== null ? this._fmt(heatAbsorbed, 1) : '—'}</div>
                      <div class="energy-unit">kWh</div>
                      <div class="energy-label">Heat Absorbed</div>
                    </div>
                    <div class="energy-card">
                      <div class="energy-icon" style="color:#4DA3FF">❄</div>
                      <div class="energy-val" style="color:#4DA3FF">${acEnergy !== null ? this._fmt(acEnergy, 1) : '—'}</div>
                      <div class="energy-unit">kWh</div>
                      <div class="energy-label">AC Energy</div>
                    </div>
                  </div>
                </div>
              </div>

            </div>
          </div>
        </ha-card>`;

      this._initEChart();
    } catch (err) {
      console.error('ThermalBalanceCard render error:', err);
    }
  }

  _renderPreview() {
    this.shadowRoot.innerHTML = `
      <style>${this._css()}</style>
      <ha-card>
        <div class="tb-card">
          <div class="header">
            <div class="header-left">
              <div class="header-icon">${this._icons.thermo}</div>
              <div class="header-text">
                <div class="header-title">Thermal Balance</div>
                <div class="header-sub">COP 3.33 · SHR 85%</div>
              </div>
            </div>
            <div class="header-badge" style="background:rgba(139, 92, 246, 0.15); color:#8B5CF6; border:1px solid rgba(139, 92, 246, 0.3)">
              -504 W
            </div>
          </div>
          <div class="gauges-row">
            ${this._gauge(927, 3500, '#FF7A3C', '#FFB199', 'Heat Gain', this._icons.sun)}
            ${this._gauge(1431, 3500, '#4DA3FF', '#93C5FD', 'AC Cooling', this._icons.snowflake)}
          </div>
        </div>
      </ha-card>`;
  }

  /* ─── Styles ─── */

  _css() {
    return `
      :host {
        --tb-primary: #E5E7EB;
        --tb-secondary: #9CA3AF;
        --tb-label: #6B7280;
        --tb-heat: #FF7A3C;
        --tb-cool: #4DA3FF;
        --tb-cop: #8B5CF6;
        --tb-pos: #FF7A3C;
        --tb-neg: #4DA3FF;
        --tb-eq: #00C896;
        --tb-warn: #FACC15;
        font-family: inherit;
        display: block;
        width: 100%;
        box-sizing: border-box;
      }
      ha-card {
        background: #0B1220;
        border-radius: 16px;
        box-shadow: 0 8px 32px rgba(0,0,0,0.5), 0 0 20px rgba(77,163,255,0.25);
        border: 1px solid rgba(77,163,255,0.2);
        overflow: hidden;
        color: var(--tb-primary);
        padding: 0;
      }
      .tb-card {
        padding: 20px;
        container-type: inline-size;
        container-name: tb-card;
      }
      .card-layout {
        display: grid;
        grid-template-columns: 1fr;
        gap: 16px;
      }
      @container tb-card (min-width: 680px) {
        .card-layout {
          grid-template-columns: 1fr 1fr;
          align-items: start;
        }
      }
      .card-col {
        display: flex;
        flex-direction: column;
        gap: 16px;
      }
      .header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
      }
      .header-left {
        display: flex;
        align-items: center;
        gap: 10px;
      }
      .header-icon {
        width: 36px; height: 36px;
        display: flex; align-items: center; justify-content: center;
        background: rgba(100,180,255,0.08);
        border-radius: 10px;
      }
      .header-icon svg { width: 20px; height: 20px; }
      .header-title {
        font-size: 16px;
        font-weight: 700;
        letter-spacing: 0.3px;
      }
      .header-sub {
        font-size: 11px;
        color: var(--tb-secondary);
        margin-top: 1px;
        letter-spacing: 0.2px;
      }
      .header-badge {
        font-size: 13px;
        font-weight: 700;
        padding: 5px 12px;
        border-radius: 20px;
        white-space: nowrap;
        transition: color 0.3s ease, background 0.3s ease;
      }
      .gauges-row {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 12px;
      }
      .gauge-card {
        background: #162032;
        border-radius: 12px;
        border: 1px solid #233045;
        padding: 14px 8px 10px;
        display: flex;
        flex-direction: column;
        align-items: center;
        transition: border-color 0.3s ease;
      }
      .gauge-card:hover {
        border-color: rgba(255,255,255,0.15);
      }
      .gauge-svg {
        width: 100%;
        max-width: 180px;
      }
      .gauge-label {
        display: flex;
        align-items: center;
        gap: 5px;
        font-size: 12px;
        color: var(--tb-secondary);
        margin-top: 4px;
      }
      .gauge-icon { display: flex; align-items: center; }
      .metrics-bar {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 8px;
      }
      .metric-block {
        background: #162032;
        border: 1px solid #233045;
        border-radius: 10px;
        padding: 10px 6px;
        text-align: center;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 3px;
        transition: border-color 0.3s ease;
      }
      .metric-block:hover {
        border-color: rgba(255,255,255,0.15);
      }
      .metric-icon { font-size: 14px; line-height: 1; }
      .metric-val {
        font-size: 14px;
        font-weight: 700;
        transition: color 0.3s ease;
        white-space: nowrap;
      }
      .metric-unit { font-size: 10px; opacity: 0.6; font-weight: 400; }
      .metric-label {
        font-size: 10px;
        color: var(--tb-secondary);
        letter-spacing: 0.2px;
      }
      .section {
        background: #162032;
        border: 1px solid #233045;
        border-radius: 12px;
        padding: 14px;
        transition: border-color 0.3s ease;
      }
      .section:hover {
        border-color: rgba(255,255,255,0.15);
      }
      .section-title {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 13px;
        font-weight: 600;
        color: var(--tb-primary);
        margin-bottom: 12px;
        letter-spacing: 0.3px;
      }
      .section-title svg { flex-shrink: 0; }
      .ac-grid {
        display: grid;
        grid-template-columns: 1fr;
        gap: 0;
      }
      @container tb-card (min-width: 500px) {
        .ac-grid {
          grid-template-columns: 1fr 1fr;
        }
      }
      .ac-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 8px;
        padding: 7px 6px;
        border-bottom: 1px solid #233045;
        font-size: 12px;
        min-width: 0;
      }
      .ac-row:last-child { border-bottom: none; }
      @container tb-card (min-width: 500px) {
        .ac-row:nth-last-child(-n+2) { border-bottom: none; }
      }
      .ac-dot {
        width: 5px; height: 5px;
        border-radius: 50%;
        flex-shrink: 0;
      }
      .ac-label {
        color: var(--tb-secondary);
        flex: 1;
        min-width: 0;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
      .ac-val {
        font-weight: 600;
        color: var(--tb-primary);
        white-space: nowrap;
        flex-shrink: 0;
        text-align: right;
      }
      .ac-unit {
        font-weight: 400;
        font-size: 10px;
        opacity: 0.5;
      }
      .energy-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 8px;
      }
      .energy-card {
        background: #0B1220;
        border: 1px solid #233045;
        border-radius: 10px;
        padding: 12px 10px;
        text-align: center;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 2px;
        transition: border-color 0.3s ease;
      }
      .energy-card:hover {
        border-color: rgba(255,255,255,0.15);
      }
      .energy-icon { font-size: 16px; margin-bottom: 2px; }
      .energy-val {
        font-size: 20px;
        font-weight: 700;
        transition: color 0.3s ease;
        line-height: 1.2;
      }
      .energy-unit {
        font-size: 10px;
        color: var(--tb-secondary);
        opacity: 0.7;
      }
      .energy-label {
        font-size: 10px;
        color: var(--tb-secondary);
        margin-top: 2px;
        letter-spacing: 0.2px;
      }
      .trend-legend {
        margin-left: auto;
        display: flex;
        align-items: center;
        gap: 12px;
        font-size: 11px;
        color: var(--tb-secondary);
      }
      .legend-item {
        display: flex;
        align-items: center;
        gap: 4px;
      }
      .legend-dot {
        width: 7px;
        height: 7px;
        border-radius: 50%;
      }
      .trend-chart-container {
        width: 100%;
        margin-top: 6px;
      }
      .trend-svg {
        width: 100%;
        height: 60px;
        overflow: visible;
      }
      @media (max-width: 360px) {
        .metrics-bar { grid-template-columns: repeat(2, 1fr); }
        .metric-val { font-size: 12px; }
      }
    `;
  }
}

/* ─── Register Custom Elements ─── */
if (!customElements.get('thermal-balance-card')) {
  customElements.define('thermal-balance-card', ThermalBalanceCard);
}

window.customCards = window.customCards || [];
window.customCards.push({
  type: 'thermal-balance-card',
  name: 'Thermal Balance',
  description: 'Thermal balance monitoring card with live metrics and energy tracking.',
  icon: 'mdi:home-thermometer',
  preview: false,
});
