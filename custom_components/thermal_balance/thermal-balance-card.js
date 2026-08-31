/**
 * Thermal Balance Card — Premium Home Assistant Lovelace Card
 * Pure vanilla JS Custom Element with Visual UI Editor & Auto-Discovery
 *
 * Registered as: custom:thermal-balance-card
 * Editor registered as: thermal-balance-card-editor
 */

const TRANSLATIONS = {
  en: {
    title: 'Thermal Balance',
    editor_title: 'Thermal Balance Configuration',
    compact_view: 'Compact Mode (Mobile)',
    card_title_label: 'Custom Card Title (Optional)',
    heat_gain_sensor: 'Heat Gain Sensor',
    ac_cooling_sensor: 'AC Cooling / Heating Sensor',
    net_balance_sensor: 'Net Balance Sensor',
    ac_cop_sensor: 'AC COP Sensor',
    time_to_1c_sensor: 'Time to 1°C Sensor',
    daily_balance_sensor: 'Daily Balance Sensor',
    total_balance_sensor: 'Total Balance Sensor',
    heat_absorbed_sensor: 'Heat Absorbed Sensor',
    ac_energy_sensor: 'AC Thermal Energy Sensor',
    condensation_rate_sensor: 'Condensation Rate Sensor',
    heat_mode: 'Heat Mode',
    cool_mode: 'Cool Mode',
    stable: 'Stable',
    heat_gain: 'Heat Gain',
    heat_loss: 'Heat Loss',
    ac_cooling: 'AC Cooling',
    ac_heating: 'AC Heating',
    net_balance: 'Net Balance',
    ventilation: 'Ventilation',
    to_1c: 'To 1°C',
    condensation: 'Condensation',
    vent_heat_exchange: 'Ventilation & Heat Exchange',
    window: 'Window',
    window_open: 'Open',
    window_closed: 'Closed',
    wind: 'Wind',
    air_change: 'Air Change (ACH)',
    curtains: 'Curtains',
    curtains_closed: 'Closed',
    curtains_open: 'Open',
    solar: 'Solar',
    walls: 'Walls',
    k_factor_actual: 'K-Factor (Actual)',
    insulation: 'Insulation',
    estimated: 'Estimated',
    window_open_k_note: 'Window is open — K-factor is unreliable',
    ac_cooling_perf: 'AC Cooling Performance',
    heating_perf: 'Heating Performance (Heat Pump)',
    trend_24h: '24h Thermal Trend',
    heat: 'Heat',
    cooling: 'Cooling',
    heating: 'Heating',
    net: 'Net',
    energy_cost_intel: 'Energy & Cost Intelligence',
    daily_balance: 'Daily Balance',
    total_balance: 'Total Balance',
    heat_absorbed: 'Heat Absorbed',
    ac_energy: 'AC Energy',
    ac_cost: 'AC Cost',
    shading_savings: 'Shading Savings',
    open_win_rec: 'Open Window Recommended! Outdoor air is cooler than indoor. Open window for free cooling!',
    close_cur_rec: 'Close Curtains Recommended! High solar radiation. Close curtains to reduce heat gain & save energy.',
  },
  ru: {
    title: 'Thermal Balance',
    editor_title: 'Настройки Thermal Balance',
    compact_view: 'Компактный режим (для смартфонов)',
    card_title_label: 'Свой заголовок карточки (опционально)',
    heat_gain_sensor: 'Сенсор притока тепла (Heat Gain)',
    ac_cooling_sensor: 'Сенсор отдачи AC (Cooling/Heating)',
    net_balance_sensor: 'Сенсор чистого баланса (Net Balance)',
    ac_cop_sensor: 'Сенсор эффективности AC (COP)',
    time_to_1c_sensor: 'Сенсор времени до ±1°C',
    daily_balance_sensor: 'Сенсор суточного баланса',
    total_balance_sensor: 'Сенсор общего баланса',
    heat_absorbed_sensor: 'Сенсор поглощенного тепла',
    ac_energy_sensor: 'Сенсор тепловой энергии AC',
    condensation_rate_sensor: 'Сенсор конденсата AC',
    heat_mode: 'Режим Обогрева',
    cool_mode: 'Режим Охлаждения',
    stable: 'Баланс',
    heat_gain: 'Приток тепла',
    heat_loss: 'Теплопотери',
    ac_cooling: 'Охлаждение AC',
    ac_heating: 'Теплоотдача AC',
    net_balance: 'Чистый баланс',
    ventilation: 'Проветривание',
    to_1c: 'До ±1°C',
    condensation: 'Конденсат',
    vent_heat_exchange: 'Вентиляция и теплообмен',
    window: 'Окно',
    window_open: 'Открыто',
    window_closed: 'Закрыто',
    wind: 'Ветер',
    air_change: 'Кратность (ACH)',
    curtains: 'Шторы',
    curtains_closed: 'Закрыты',
    curtains_open: 'Открыты',
    solar: 'Солнце',
    walls: 'Стены',
    k_factor_actual: 'K-фактор (факт)',
    insulation: 'Изоляция',
    estimated: 'Расчетный',
    window_open_k_note: 'Окно открыто — K-фактор недостоверен',
    ac_cooling_perf: 'Характеристики охлаждения AC',
    heating_perf: 'Характеристики обогрева (ТН)',
    trend_24h: 'Суточный тренд баланса',
    heat: 'Приток',
    cooling: 'Холод',
    heating: 'Нагрев',
    net: 'Баланс',
    energy_cost_intel: 'Энергетические и финансовые счетчики',
    daily_balance: 'Суточный баланс',
    total_balance: 'Общий баланс',
    heat_absorbed: 'Поглощено тепла',
    ac_energy: 'Тепловая энергия AC',
    ac_cost: 'Затраты за день',
    shading_savings: 'Экономия от штор',
    open_win_rec: 'Рекомендуется открыть окно! На улице прохладнее, чем в комнате — используйте бесплатное охлаждение.',
    close_cur_rec: 'Рекомендуется закрыть шторы! Высокая солнечная радиация — зашторьте окна для экономии энергии.',
  }
};

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
  ac_cost: ['_ac_energy_cost', '_energy_cost'],
  daily_savings: ['_shading_daily_savings', '_daily_savings'],
  rec_open_window: ['_recommend_open_window'],
  rec_close_curtains: ['_recommend_close_curtains'],
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

  _t(key, defaultText = '') {
    const lang = (this._hass && (this._hass.locale?.language || this._hass.language)) || 'en';
    const langCode = lang.toLowerCase().startsWith('ru') ? 'ru' : 'en';
    return (TRANSLATIONS[langCode] && TRANSLATIONS[langCode][key]) || (TRANSLATIONS.en && TRANSLATIONS.en[key]) || defaultText || key;
  }

  _valueChanged(ev) {
    if (!this._config) return;
    const target = ev.target;
    const configKey = target.getAttribute('configValue');
    if (!configKey) return;

    let newValue = ev.detail ? ev.detail.value : (target.type === 'checkbox' ? target.checked : target.value);
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
      { key: 'heat_gain', label: this._t('heat_gain_sensor') },
      { key: 'ac_cooling', label: this._t('ac_cooling_sensor') },
      { key: 'net_balance', label: this._t('net_balance_sensor') },
      { key: 'ac_cop', label: this._t('ac_cop_sensor') },
      { key: 'time_to_1c', label: this._t('time_to_1c_sensor') },
      { key: 'daily_balance', label: this._t('daily_balance_sensor') },
      { key: 'total_balance', label: this._t('total_balance_sensor') },
      { key: 'heat_absorbed', label: this._t('heat_absorbed_sensor') },
      { key: 'ac_energy', label: this._t('ac_energy_sensor') },
      { key: 'condensation_rate', label: this._t('condensation_rate_sensor') },
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

    const isCompact = Boolean(this._config.compact || this._config.compact_view);

    const fieldsHtml = fields.map(f => {
      const currentVal = this._config[f.key] || '';
      const autoLabel = getAutoLabel(f.key);

      const options = [
        `<option value="" ${currentVal === '' ? 'selected' : ''}>Auto (${autoLabel})</option>`,
        ...sensorEntities.map(e =>
          `<option value="${e.eid}" ${currentVal === e.eid ? 'selected' : ''}>${e.name}</option>`
        )
      ].join('');

      return `
        <div class="editor-row">
          <label class="editor-label">${f.label}</label>
          <select class="editor-select" configValue="${f.key}">
            ${options}
          </select>
        </div>
      `;
    }).join('');

    this.shadowRoot.innerHTML = `
      <style>
        .editor-container {
          display: flex;
          flex-direction: column;
          gap: 12px;
          padding: 8px 0;
          font-family: inherit;
        }
        .editor-title {
          font-size: 15px;
          font-weight: 700;
          color: var(--primary-text-color, #FFF);
          margin-bottom: 4px;
        }
        .editor-row {
          display: flex;
          flex-direction: column;
          gap: 4px;
        }
        .editor-row-inline {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 6px 0;
          border-bottom: 1px solid var(--divider-color, #233045);
        }
        .editor-label {
          font-size: 12.5px;
          font-weight: 500;
          color: var(--secondary-text-color, #9CA3AF);
        }
        .editor-select, .editor-input {
          background: var(--card-background-color, #162032);
          color: var(--primary-text-color, #FFF);
          border: 1px solid var(--divider-color, #233045);
          border-radius: 6px;
          padding: 8px 10px;
          font-size: 13px;
          font-family: inherit;
          width: 100%;
          box-sizing: border-box;
        }
        .editor-select:focus, .editor-input:focus {
          outline: none;
          border-color: var(--primary-color, #03a9f4);
        }
        .editor-checkbox {
          width: 18px;
          height: 18px;
          cursor: pointer;
        }
      </style>
      <div class="editor-container">
        <div class="editor-title">${this._t('editor_title')}</div>
        
        <div class="editor-row-inline">
          <label class="editor-label" style="font-weight: 600; color: var(--primary-text-color, #FFF);">${this._t('compact_view')}</label>
          <input type="checkbox" class="editor-checkbox" configValue="compact" ${isCompact ? 'checked' : ''}/>
        </div>

        <div class="editor-row">
          <label class="editor-label">${this._t('card_title_label')}</label>
          <input type="text" class="editor-input" configValue="title" value="${this._config.title || ''}" placeholder="Thermal Balance"/>
        </div>

        ${fieldsHtml}
      </div>
    `;

    const selects = this.shadowRoot.querySelectorAll('.editor-select, .editor-input, .editor-checkbox');
    selects.forEach(s => {
      s.addEventListener('change', this._valueChanged.bind(this));
      if (s.tagName === 'INPUT' && s.type === 'text') {
        s.addEventListener('input', this._valueChanged.bind(this));
      }
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
    return (this._config && (this._config.compact || this._config.compact_view)) ? 4 : 6;
  }

  _t(key, defaultText = '') {
    const lang = (this._hass && (this._hass.locale?.language || this._hass.language)) || 'en';
    const langCode = lang.toLowerCase().startsWith('ru') ? 'ru' : 'en';
    return (TRANSLATIONS[langCode] && TRANSLATIONS[langCode][key]) || (TRANSLATIONS.en && TRANSLATIONS.en[key]) || defaultText || key;
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
    if (m === 0 && direction === 'equilibrium') return this._t('stable');
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
    const pct = Math.min(1, Math.max(0, Math.abs(value || 0) / max));
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
      fire: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#FF7A3C" stroke-width="2" stroke-linecap="round"><path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z"/></svg>`,
      fireLg: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#FF7A3C" stroke-width="2" stroke-linecap="round"><path d="M8.5 14.5A2.5 2.5 0 0 0 11 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 1 1-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 0 0 2.5 2.5z"/></svg>`,
      snowflake: `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#4DA3FF" stroke-width="2" stroke-linecap="round"><line x1="12" y1="2" x2="12" y2="22"/><line x1="2" y1="12" x2="22" y2="12"/><line x1="5.5" y1="5.5" x2="18.5" y2="18.5"/><line x1="18.5" y1="5.5" x2="5.5" y2="18.5"/><polyline points="8,2 12,6 16,2"/><polyline points="8,22 12,18 16,22"/><polyline points="2,8 6,12 2,16"/><polyline points="22,8 18,12 22,16"/></svg>`,
      snowflakeLg: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#4DA3FF" stroke-width="2" stroke-linecap="round"><line x1="12" y1="2" x2="12" y2="22"/><line x1="2" y1="12" x2="22" y2="12"/><line x1="5.5" y1="5.5" x2="18.5" y2="18.5"/><line x1="18.5" y1="5.5" x2="5.5" y2="18.5"/><polyline points="8,2 12,6 16,2"/><polyline points="8,22 12,18 16,22"/><polyline points="2,8 6,12 2,16"/><polyline points="22,8 18,12 22,16"/></svg>`,
      thermo: `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M14 14.76V3.5a2.5 2.5 0 0 0-5 0v11.26a4.5 4.5 0 1 0 5 0z"/></svg>`,
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
    const result = new Array(numPoints).fill(0);

    if (!eid || !this._historyData || !this._historyData[eid]) {
      if (liveVal !== null && liveVal !== undefined && !isNaN(liveVal)) {
        result[numPoints - 1] = liveVal;
      }
      return result;
    }

    const items = this._historyData[eid];
    if (!Array.isArray(items) || items.length === 0) {
      if (liveVal !== null && liveVal !== undefined && !isNaN(liveVal)) {
        result[numPoints - 1] = liveVal;
      }
      return result;
    }

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

  _renderTrendSvg(heatPoints, coolPoints, isHeating = false) {
    const width = 300;
    const height = 65;
    const all = [...(heatPoints || []), ...(coolPoints || [])];
    const maxVal = Math.max(500, ...all);

    const heatLine = this._pointsToPath(heatPoints, width, height, maxVal);
    const heatArea = this._pointsToArea(heatPoints, width, height, maxVal);

    const coolLine = this._pointsToPath(coolPoints, width, height, maxVal);
    const coolArea = this._pointsToArea(coolPoints, width, height, maxVal);

    const hvacColor = isHeating ? '#FF7A3C' : '#4DA3FF';

    return `
      <svg viewBox="0 0 ${width} ${height}" class="trend-svg" preserveAspectRatio="none">
        <defs>
          <linearGradient id="heatTrendGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="#FF7A3C" stop-opacity="0.35"/>
            <stop offset="100%" stop-color="#FF7A3C" stop-opacity="0.0"/>
          </linearGradient>
          <linearGradient id="coolTrendGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stop-color="${hvacColor}" stop-opacity="0.35"/>
            <stop offset="100%" stop-color="${hvacColor}" stop-opacity="0.0"/>
          </linearGradient>
        </defs>
        <!-- Grid lines -->
        <line x1="0" y1="15" x2="${width}" y2="15" stroke="#1C2538" stroke-dasharray="3 3"/>
        <line x1="0" y1="45" x2="${width}" y2="45" stroke="#1C2538" stroke-dasharray="3 3"/>

        ${heatArea ? `<path d="${heatArea}" fill="url(#heatTrendGrad)"/>` : ''}
        ${coolArea ? `<path d="${coolArea}" fill="url(#coolTrendGrad)"/>` : ''}
        ${heatLine ? `<path d="${heatLine}" fill="none" stroke="#FF7A3C" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>` : ''}
        ${coolLine ? `<path d="${coolLine}" fill="none" stroke="${hvacColor}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>` : ''}
      </svg>
    `;
  }

  _initEChart(isHeating = false) {
    const container = this.shadowRoot ? this.shadowRoot.querySelector('#echart-container') : null;
    if (!container) return;

    loadECharts().then(echarts => {
      if (!this.shadowRoot || !this.shadowRoot.querySelector('#echart-container')) return;
      if (this._chart && !this._chart.isDisposed()) {
        try { this._chart.dispose(); } catch(e){}
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

      const hvacSeriesName = isHeating ? this._t('heating') : this._t('cooling');
      const hvacColor = isHeating ? '#FF7A3C' : '#4DA3FF';
      const hvacGradAlpha = isHeating ? 'rgba(255, 122, 60, 0.25)' : 'rgba(77, 163, 255, 0.25)';

      const option = {
        backgroundColor: 'transparent',
        legend: {
          show: true,
          top: 0,
          right: 10,
          textStyle: { color: '#9CA3AF', fontSize: 10 },
          itemWidth: 10,
          itemHeight: 6,
          data: [this._t('heat'), hvacSeriesName, this._t('net')]
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
            name: this._t('heat'),
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
            name: hvacSeriesName,
            type: 'line',
            smooth: 0.3,
            smoothMonotone: 'x',
            sampling: 'lttb',
            showSymbol: false,
            symbol: 'circle',
            symbolSize: 6,
            itemStyle: { color: hvacColor },
            lineStyle: { width: 2.0, color: hvacColor },
            areaStyle: {
              color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                { offset: 0, color: hvacGradAlpha },
                { offset: 1, color: 'rgba(0, 0, 0, 0.0)' }
              ])
            },
            data: coolPoints.map(v => Math.round(v))
          },
          {
            name: this._t('net'),
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
      const hash = parts.join(';;') + `;compact=${Boolean(this._config.compact || this._config.compact_view)}`;
      if (hash === this._lastHash && this.shadowRoot && this.shadowRoot.innerHTML !== '') return;
      this._lastHash = hash;

      const isCompact = Boolean(this._config.compact || this._config.compact_view);
      const cardTitle = this._config.title || this._t('title');

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

      // AC cooling & heating attributes
      const isHeating = Boolean(this._getAttr('ac_cooling', 'is_heating') || this._getAttr('net_balance', 'is_heating'));
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
      const windSpeed = this._getAttr('heat_gain', 'wind_speed_ms');
      const windDir = this._getAttr('heat_gain', 'wind_dir_deg');
      const windACH = this._getAttr('heat_gain', 'ventilation_ach');

      // Empirical K-Factor attributes
      const empiricalK = this._getState('empirical_k_factor') ?? this._getAttr('heat_gain', 'hlc_w_k');
      const empiricalKDev = this._getAttr('empirical_k_factor', 'deviation_percent');
      const empiricalKGrade = this._getAttr('empirical_k_factor', 'insulation_grade');

      // Cost, Savings & Recommendation states
      const acCost = this._getState('ac_cost');
      const dailySavings = this._getState('daily_savings');
      const recOpenWin = this._getState('rec_open_window') === 1 || this._getAttr('rec_open_window', 'state') === 'on' || Boolean(this._getAttr('heat_gain', 'recommend_open_window'));
      const recCloseCur = this._getState('rec_close_curtains') === 1 || this._getAttr('rec_close_curtains', 'state') === 'on' || Boolean(this._getAttr('heat_gain', 'recommend_close_curtains'));
      const currencySymbol = this._getAttr('ac_cost', 'unit_of_measurement') || '₴';

      // Curtains & Shading attributes
      const curtainsClosed = this._getAttr('heat_gain', 'curtains_closed');
      const curtainsState = this._getAttr('heat_gain', 'curtains_state');
      const illuminanceLux = this._getAttr('heat_gain', 'illuminance_lux');
      const curtainsNote = this._getAttr('heat_gain', 'curtains_note');
      const curtainReducePct = this._getAttr('heat_gain', 'curtain_glass_reduce_percent') || 74;

      // time_to_1c attributes
      const direction = this._getAttr('time_to_1c', 'direction') || 'equilibrium';
      const dirInfo = this._dirIcon(direction);

      // Colors & formatting
      const balColor = this._balanceColor(netBalance);
      const balBg = this._balanceBg(netBalance);
      const dailyColor = this._balanceColor(dailyBal);
      const timeDisplay = this._fmtTime(time1c, direction);

      const ventColor = windowOpen ? (pVent > 20 ? '#FF7A3C' : (pVent < -20 ? '#4DA3FF' : '#00C896')) : '#6B7280';
      const ventValText = !windowOpen ? `${this._t('window_closed')} (0 W)` : (pVent !== null && pVent !== undefined ? (pVent > 0 ? '+' : '') + this._fmt(pVent, 0) + ' W' : '—');

      const modeBadge = isHeating ? `🔥 ${this._t('heat_mode')}` : `❄️ ${this._t('cool_mode')}`;
      const copText = cop !== null ? `COP ${this._fmt(cop, 2)}` : '';
      const shrText = (!isHeating && shr !== null) ? `SHR ${this._fmt(shr, 0)}%` : '';
      const ventHeaderBadge = windowOpen ? (pVent !== null ? (pVent >= 0 ? `🪟 +${Math.round(pVent)}W` : `🪟 ${Math.round(pVent)}W`) : `🪟 ${this._t('window_open')}`) : `🪟 ${this._t('window_closed')}`;
      const subtitle = [modeBadge, copText, shrText, ventHeaderBadge].filter(Boolean).join(' · ');

      const acGaugeTitle = isHeating ? this._t('ac_heating') : this._t('ac_cooling');
      const acGaugeColor = isHeating ? '#FF7A3C' : '#4DA3FF';
      const acGaugeSubColor = isHeating ? '#FFB199' : '#93C5FD';
      const acGaugeIcon = isHeating ? this._icons.fire : this._icons.snowflake;
      const acSectionTitle = isHeating ? this._t('heating_perf') : this._t('ac_cooling_perf');
      const acSectionIcon = isHeating ? this._icons.fireLg : this._icons.snowflakeLg;

      const acRows = [
        { label: 'ΔT AC', value: deltaT, unit: '°C', dec: 1, color: '#374151' },
        { label: hasMeasured ? 'Exit Temp (Meas)' : 'Exit Temp', value: exitTemp, unit: '°C', dec: 1, color: hasMeasured ? (isHeating ? '#FF7A3C' : '#4DA3FF') : '#374151' },
        ...(hasMeasured ? [{ label: 'Exit Temp (Calc)', value: calcExitTemp, unit: '°C', dec: 1, color: '#FACC15' }] : []),
        { label: 'Sensible', value: sensible, unit: 'W', dec: 0, color: '#374151' },
        ...(!isHeating ? [{ label: 'Latent', value: latent, unit: 'W', dec: 0, color: '#374151' }] : []),
        ...(!isHeating ? [{ label: 'SHR', value: shr, unit: '%', dec: 1, color: '#374151' }] : []),
        { label: 'Enthalpy', value: enthalpy, unit: 'kJ/kg', dec: 1, color: '#374151' },
        { label: 'Airflow', value: airflow, unit: 'm³/h', dec: 0, color: '#00C896' },
        { label: 'Dew Pt In', value: dewIn, unit: '°C', dec: 1, color: '#4DA3FF' },
        { label: 'Dew Pt Out', value: dewOut, unit: '°C', dec: 1, color: '#4DA3FF' },
      ];

      // Fetch history asynchronously
      this._fetchHistory();

      const heatPoints = this._getTrendPoints('heat_gain', heatGain);
      const coolPoints = this._getTrendPoints('ac_cooling', acCooling);
      const trendSvg = this._renderTrendSvg(heatPoints, coolPoints, isHeating);

      const acRowsHtml = acRows.map(r => `
        <div class="ac-row">
          <span class="ac-dot" style="background:${r.color}"></span>
          <span class="ac-label">${r.label}</span>
          <span class="ac-val">${r.value !== null && r.value !== undefined ? this._fmt(r.value, r.dec) : '—'} <span class="ac-unit">${r.value !== null && r.value !== undefined ? r.unit : ''}</span></span>
        </div>`).join('');

      this.shadowRoot.innerHTML = `
        <style>${this._css()}</style>
        <ha-card class="${isHeating ? 'heating-theme' : 'cooling-theme'} ${isCompact ? 'compact-mode' : ''}">
          <div class="tb-card">

            <!-- SMART ADVICE BANNERS -->
            ${recOpenWin ? `
              <div class="advice-banner advice-window">
                <span>🍃 <b>${this._t('open_win_rec')}</b></span>
              </div>` : ''}
            ${recCloseCur ? `
              <div class="advice-banner advice-curtains">
                <span>☀️ <b>${this._t('close_cur_rec')}</b></span>
              </div>` : ''}

            <div class="card-layout">

              <!-- COLUMN 1: Thermal Balance, Gauges, Metrics, Ventilation & AC Performance -->
              <div class="card-col col-left">
                <!-- HEADER -->
                <div class="header">
                  <div class="header-left">
                    <div class="header-icon">${this._icons.thermo}</div>
                    <div class="header-text">
                      <div class="header-title">${cardTitle}</div>
                      ${subtitle ? `<div class="header-sub">${subtitle}</div>` : ''}
                    </div>
                  </div>
                  <div class="header-badge" style="background:var(--tb-theme-badge-bg); color:var(--tb-theme-accent); border:1px solid var(--tb-theme-border);">
                    ${netBalance !== null ? (netBalance > 0 ? '+' : '') + this._fmt(netBalance, 0) : '—'} W
                  </div>
                </div>

                <!-- GAUGES -->
                <div class="gauges-row">
                  ${heatGain !== null && heatGain < 0
                    ? this._gauge(heatGain, 3500, '#4DA3FF', '#93C5FD', this._t('heat_loss'), this._icons.snowflake)
                    : this._gauge(heatGain, 3500, '#FF7A3C', '#FFB199', this._t('heat_gain'), this._icons.sun)}
                  ${this._gauge(acCooling, 3500, acGaugeColor, acGaugeSubColor, acGaugeTitle, acGaugeIcon)}
                </div>

                <!-- METRICS BAR -->
                <div class="metrics-bar">
                  <div class="metric-block">
                    <div class="metric-icon" style="color:var(--tb-theme-accent)">⚡</div>
                    <div class="metric-val" style="color:var(--tb-theme-accent)">${netBalance !== null ? (netBalance > 0 ? '+' : '') + this._fmt(netBalance, 0) : '—'} <span class="metric-unit">W</span></div>
                    <div class="metric-label">${this._t('net_balance')}</div>
                  </div>
                  <div class="metric-block">
                    <div class="metric-icon" style="color:${ventColor}">🪟</div>
                    <div class="metric-val" style="color:${ventColor}">${pVent !== null && pVent !== undefined && windowOpen ? (pVent > 0 ? '+' : '') + this._fmt(pVent, 0) : (windowOpen ? '0' : 'Off')} <span class="metric-unit">${windowOpen ? 'W' : ''}</span></div>
                    <div class="metric-label">${this._t('ventilation')}</div>
                  </div>
                  <div class="metric-block">
                    <div class="metric-icon" style="color:#FACC15">${dirInfo.sym}</div>
                    <div class="metric-val" style="color:#FACC15">${timeDisplay}</div>
                    <div class="metric-label">${this._t('to_1c')}</div>
                  </div>
                  <div class="metric-block">
                    <div class="metric-icon" style="color:#93C5FD">💧</div>
                    <div class="metric-val" style="color:#93C5FD">${condensation !== null ? this._fmt(condensation, 2) : '—'} <span class="metric-unit">L/h</span></div>
                    <div class="metric-label">${this._t('condensation')}</div>
                  </div>
                </div>

                <!-- VENTILATION & THERMAL SOURCES -->
                <div class="section">
                  <div class="section-title">🪟 <span>${this._t('vent_heat_exchange')}</span></div>
                  <div class="ac-grid">
                    <div class="ac-row">
                      <span class="ac-dot" style="background:${windowOpen ? '#FF7A3C' : '#6B7280'}"></span>
                      <span class="ac-label">${this._t('window')}</span>
                      <span class="ac-val" style="color:${windowOpen ? '#FF7A3C' : '#00C896'}">${windowOpen ? this._t('window_open') : this._t('window_closed')}</span>
                    </div>
                    <div class="ac-row">
                      <span class="ac-dot" style="background:${ventColor}"></span>
                      <span class="ac-label">${this._t('ventilation')}</span>
                      <span class="ac-val" style="color:${ventColor}">${ventValText}</span>
                    </div>
                    ${windSpeed !== null && windSpeed !== undefined ? `
                    <div class="ac-row">
                      <span class="ac-dot" style="background:#60A5FA"></span>
                      <span class="ac-label">${this._t('wind')}</span>
                      <span class="ac-val" style="color:#60A5FA">${this._fmt(windSpeed, 1)} m/s <span class="ac-unit">(${this._fmt(windDir, 0)}°)</span></span>
                    </div>
                    ` : ''}
                    ${windACH !== null && windACH !== undefined && windowOpen ? `
                    <div class="ac-row">
                      <span class="ac-dot" style="background:#34D399"></span>
                      <span class="ac-label">${this._t('air_change')}</span>
                      <span class="ac-val" style="color:#34D399">${this._fmt(windACH, 1)} <span class="ac-unit">/ h</span></span>
                    </div>
                    ` : ''}
                    ${curtainsState !== null && curtainsState !== undefined ? `
                    <div class="ac-row">
                      <span class="ac-dot" style="background:${curtainsClosed ? '#8B5CF6' : '#FF7A3C'}"></span>
                      <span class="ac-label">${this._t('curtains')}</span>
                      <span class="ac-val" style="color:${curtainsClosed ? '#8B5CF6' : '#FF7A3C'}">${curtainsClosed ? `${this._t('curtains_closed')} (-${curtainReducePct}%)` : this._t('curtains_open')} ${illuminanceLux !== null && illuminanceLux !== undefined ? '<span class="ac-unit">(' + Math.round(illuminanceLux) + ' lx)</span>' : ''}</span>
                    </div>
                    ${curtainsNote ? `<div class="curtains-note">🌙 ${curtainsNote}</div>` : ''}
                    ` : ''}
                    <div class="ac-row">
                      <span class="ac-dot" style="background:#FACC15"></span>
                      <span class="ac-label">${this._t('solar')}</span>
                      <span class="ac-val">${pSolar !== null && pSolar !== undefined ? '+' + this._fmt(pSolar, 0) + ' W' : '—'}</span>
                    </div>
                    <div class="ac-row">
                      <span class="ac-dot" style="background:#8B5CF6"></span>
                      <span class="ac-label">${this._t('walls')}</span>
                      <span class="ac-val">${pWall !== null && pWall !== undefined ? (pWall > 0 ? '+' : '') + this._fmt(pWall, 0) + ' W' : '—'}</span>
                    </div>
                    <div class="ac-row">
                      <span class="ac-dot" style="background:#00C896"></span>
                      <span class="ac-label">${this._t('k_factor_actual')}</span>
                      <span class="ac-val" style="color:#00C896">${empiricalK !== null ? this._fmt(empiricalK, 1) + ' W/K' : '—'} <span class="ac-unit">${empiricalKDev !== null ? '(' + (empiricalKDev > 0 ? '+' : '') + this._fmt(empiricalKDev, 0) + '%)' : ''}</span></span>
                    </div>
                    <div class="ac-row">
                      <span class="ac-dot" style="background:#3B82F6"></span>
                      <span class="ac-label">${this._t('insulation')}</span>
                      <span class="ac-val" style="font-size: 0.85em; color: #9CA3AF;">${empiricalKGrade || this._t('estimated')}</span>
                    </div>
                    ${windowOpen ? `<div class="curtains-note">🪟 ${this._t('window_open_k_note')}</div>` : ''}
                  </div>
                </div>

                <!-- AC PERFORMANCE -->
                <div class="section">
                  <div class="section-title">${acSectionIcon} <span>${acSectionTitle}</span></div>
                  <div class="ac-grid">${acRowsHtml}</div>
                </div>
              </div>

              <!-- COLUMN 2: 24h Trend Chart & Energy Accumulators -->
              <div class="card-col col-right">
                <!-- 24H ECHARTS TREND -->
                <div class="section" style="flex: 1; display: flex; flex-direction: column;">
                  <div class="section-title">
                    ${this._icons.trend}
                    <span>${this._t('trend_24h')}</span>
                    <div class="trend-legend">
                      <span class="legend-item"><span class="legend-dot" style="background:#FF7A3C"></span>${this._t('heat')}</span>
                      <span class="legend-item"><span class="legend-dot" style="background:${acGaugeColor}"></span>${isHeating ? this._t('heating') : this._t('cooling')}</span>
                    </div>
                  </div>
                  <div id="echart-container" style="width: 100%; flex: 1; min-height: 150px; margin-top: 4px;">${trendSvg}</div>
                </div>

                <!-- ENERGY & COSTS -->
                <div class="section">
                  <div class="section-title">${this._icons.bolt} <span>${this._t('energy_cost_intel')}</span></div>
                  <div class="energy-grid">
                    <div class="energy-card">
                      <div class="energy-icon" style="color:${dailyColor}">📅</div>
                      <div class="energy-val" style="color:${dailyColor}">${dailyBal !== null ? this._fmt(dailyBal, 1) : '—'}</div>
                      <div class="energy-unit">kWh</div>
                      <div class="energy-label">${this._t('daily_balance')}</div>
                    </div>
                    <div class="energy-card">
                      <div class="energy-icon" style="color:#8B5CF6">Σ</div>
                      <div class="energy-val" style="color:#8B5CF6">${totalBal !== null ? this._fmt(totalBal, 1) : '—'}</div>
                      <div class="energy-unit">kWh</div>
                      <div class="energy-label">${this._t('total_balance')}</div>
                    </div>
                    <div class="energy-card">
                      <div class="energy-icon" style="color:#FF7A3C">🔥</div>
                      <div class="energy-val" style="color:#FF7A3C">${heatAbsorbed !== null ? this._fmt(heatAbsorbed, 1) : '—'}</div>
                      <div class="energy-unit">kWh</div>
                      <div class="energy-label">${this._t('heat_absorbed')}</div>
                    </div>
                    <div class="energy-card">
                      <div class="energy-icon" style="color:${acGaugeColor}">${isHeating ? '🔥' : '❄'}</div>
                      <div class="energy-val" style="color:${acGaugeColor}">${acEnergy !== null ? this._fmt(acEnergy, 1) : '—'}</div>
                      <div class="energy-unit">kWh</div>
                      <div class="energy-label">${this._t('ac_energy')}</div>
                    </div>
                    <div class="energy-card">
                      <div class="energy-icon" style="color:#FACC15">💰</div>
                      <div class="energy-val" style="color:#FACC15">${acCost !== null ? this._fmt(acCost, 2) : '—'}</div>
                      <div class="energy-unit">${currencySymbol}</div>
                      <div class="energy-label">${this._t('ac_cost')}</div>
                    </div>
                    <div class="energy-card">
                      <div class="energy-icon" style="color:#00C896">🌱</div>
                      <div class="energy-val" style="color:#00C896">${dailySavings !== null ? this._fmt(dailySavings, 2) : '—'}</div>
                      <div class="energy-unit">${currencySymbol}/day</div>
                      <div class="energy-label">${this._t('shading_savings')}</div>
                    </div>
                  </div>
                </div>
              </div>

            </div>
          </div>
        </ha-card>`;

      this._initEChart(isHeating);
    } catch (err) {
      console.error('ThermalBalanceCard render error:', err);
    }
  }

  _renderPreview() {
    this.shadowRoot.innerHTML = `
      <style>${this._css()}</style>
      <ha-card class="cooling-theme">
        <div class="tb-card">
          <div class="header">
            <div class="header-left">
              <div class="header-icon">${this._icons.thermo}</div>
              <div class="header-text">
                <div class="header-title">${this._t('title')}</div>
                <div class="header-sub">COP 3.33 · SHR 85%</div>
              </div>
            </div>
            <div class="header-badge" style="background:var(--tb-theme-badge-bg); color:var(--tb-theme-accent); border:1px solid var(--tb-theme-border)">
              -504 W
            </div>
          </div>
          <div class="gauges-row">
            ${this._gauge(927, 3500, '#FF7A3C', '#FFB199', this._t('heat_gain'), this._icons.sun)}
            ${this._gauge(1431, 3500, '#4DA3FF', '#93C5FD', this._t('ac_cooling'), this._icons.snowflake)}
          </div>
        </div>
      </ha-card>`;
  }

  /* ─── Styles ─── */

  _css() {
    return `
      :host {
        --tb-primary: #FFFFFF;
        --tb-secondary: #D1D5DB;
        --tb-label: #9CA3AF;
        --tb-heat: #FF7A3C;
        --tb-cool: #4DA3FF;
        --tb-cop: #8B5CF6;
        --tb-pos: #FF7A3C;
        --tb-neg: #4DA3FF;
        --tb-eq: #00C896;
        --tb-warn: #FACC15;
        font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        display: block;
        width: 100%;
        box-sizing: border-box;
      }
      ha-card {
        background: #0B1220;
        border-radius: 18px;
        box-shadow: 0 10px 36px rgba(0,0,0,0.55), 0 0 25px var(--tb-theme-glow);
        border: 1px solid var(--tb-theme-border);
        overflow: hidden;
        color: var(--tb-primary);
        padding: 0;
        transition: border-color 0.4s ease, box-shadow 0.4s ease;
      }
      ha-card.cooling-theme {
        --tb-theme-accent: #4DA3FF;
        --tb-theme-glow: rgba(77, 163, 255, 0.22);
        --tb-theme-border: rgba(77, 163, 255, 0.25);
        --tb-theme-badge-bg: rgba(77, 163, 255, 0.15);
      }
      ha-card.heating-theme {
        --tb-theme-accent: #FF7A3C;
        --tb-theme-glow: rgba(255, 122, 60, 0.25);
        --tb-theme-border: rgba(255, 122, 60, 0.35);
        --tb-theme-badge-bg: rgba(255, 122, 60, 0.18);
      }
      .tb-card {
        padding: 16px;
        container-type: inline-size;
        container-name: tb-card;
      }
      .advice-banner {
        padding: 10px 14px;
        border-radius: 12px;
        font-size: 13.5px;
        line-height: 1.4;
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 12px;
        font-weight: 600;
      }
      .advice-window {
        background: rgba(0, 200, 150, 0.15);
        border: 1px solid rgba(0, 200, 150, 0.4);
        color: #00E6AB;
      }
      .advice-curtains {
        background: rgba(255, 122, 60, 0.15);
        border: 1px solid rgba(255, 122, 60, 0.4);
        color: #FF8F56;
      }
      .card-layout {
        display: grid;
        grid-template-columns: 1fr;
        gap: 12px;
        align-items: stretch;
      }
      @container tb-card (min-width: 580px) {
        .card-layout {
          grid-template-columns: repeat(2, minmax(0, 1fr));
          align-items: stretch;
        }
      }
      .card-col {
        display: flex;
        flex-direction: column;
        gap: 12px;
        min-width: 0;
        height: 100%;
      }
      .header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 10px;
      }
      .header-left {
        display: flex;
        align-items: center;
        gap: 10px;
      }
      .header-icon {
        width: 36px; height: 36px;
        display: flex; align-items: center; justify-content: center;
        background: var(--tb-theme-badge-bg);
        color: var(--tb-theme-accent);
        border-radius: 10px;
      }
      .header-icon svg { width: 20px; height: 20px; }
      .header-title {
        font-size: 17px;
        font-weight: 800;
        letter-spacing: 0.3px;
        color: #FFFFFF;
      }
      .header-sub {
        font-size: 12px;
        color: var(--tb-secondary);
        margin-top: 1px;
        letter-spacing: 0.2px;
        font-weight: 500;
      }
      .header-badge {
        font-size: 14px;
        font-weight: 800;
        padding: 5px 12px;
        border-radius: 20px;
        white-space: nowrap;
        transition: color 0.3s ease, background 0.3s ease, border-color 0.3s ease;
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
        padding: 10px 8px 10px;
        display: flex;
        flex-direction: column;
        align-items: center;
        transition: border-color 0.3s ease;
      }
      .gauge-card:hover {
        border-color: rgba(255,255,255,0.2);
      }
      .gauge-svg {
        width: 100%;
        max-width: 200px;
      }
      .gauge-label {
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 13.5px;
        font-weight: 600;
        color: var(--tb-secondary);
        margin-top: 6px;
      }
      .gauge-icon { display: flex; align-items: center; }
      .metrics-bar {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 10px;
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
        border-color: rgba(255,255,255,0.2);
      }
      .metric-icon { font-size: 15px; line-height: 1; }
      .metric-val {
        font-size: 15px;
        font-weight: 800;
        transition: color 0.3s ease;
        white-space: nowrap;
      }
      .metric-unit { font-size: 11px; opacity: 0.85; font-weight: 500; }
      .metric-label {
        font-size: 11px;
        font-weight: 500;
        color: var(--tb-secondary);
        letter-spacing: 0.1px;
      }
      .section {
        background: #162032;
        border: 1px solid #233045;
        border-radius: 12px;
        padding: 12px 14px;
        transition: border-color 0.3s ease;
      }
      .section:hover {
        border-color: rgba(255,255,255,0.2);
      }
      .section-title {
        display: flex;
        align-items: center;
        gap: 8px;
        font-size: 13.5px;
        font-weight: 700;
        color: #FFFFFF;
        margin-bottom: 10px;
        letter-spacing: 0.2px;
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
        font-size: 12.5px;
        min-width: 0;
      }
      .ac-row:last-child { border-bottom: none; }
      @container tb-card (min-width: 500px) {
        .ac-row:nth-last-child(-n+2) { border-bottom: none; }
      }
      .ac-dot {
        width: 6px; height: 6px;
        border-radius: 50%;
        flex-shrink: 0;
      }
      .ac-label {
        color: var(--tb-secondary);
        font-weight: 500;
        flex: 1;
        min-width: 0;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
      .ac-val {
        font-weight: 700;
        color: #FFFFFF;
        white-space: nowrap;
        flex-shrink: 0;
        text-align: right;
      }
      .ac-unit {
        font-weight: 400;
        font-size: 10.5px;
        opacity: 0.75;
      }
      .curtains-note {
        grid-column: 1 / -1;
        font-size: 12.5px;
        color: var(--tb-secondary);
        padding: 3px 6px 6px 20px;
        line-height: 1.4;
        text-align: left;
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
        padding: 10px 10px;
        text-align: center;
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 2px;
        transition: border-color 0.3s ease;
      }
      .energy-card:hover {
        border-color: rgba(255,255,255,0.2);
      }
      .energy-icon { font-size: 18px; margin-bottom: 2px; }
      .energy-val {
        font-size: 17px;
        font-weight: 800;
        transition: color 0.3s ease;
        line-height: 1.2;
      }
      .energy-unit {
        font-size: 11px;
        color: var(--tb-secondary);
        font-weight: 500;
      }
      .energy-label {
        font-size: 11px;
        font-weight: 500;
        color: var(--tb-secondary);
        margin-top: 2px;
        letter-spacing: 0.2px;
      }
      .trend-legend {
        margin-left: auto;
        display: flex;
        align-items: center;
        gap: 14px;
        font-size: 12px;
        font-weight: 600;
        color: var(--tb-secondary);
      }
      .legend-item {
        display: flex;
        align-items: center;
        gap: 5px;
      }
      .legend-dot {
        width: 8px;
        height: 8px;
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

      /* ─── Compact Mode ─── */
      ha-card.compact-mode .tb-card {
        padding: 12px;
      }
      ha-card.compact-mode .card-layout {
        grid-template-columns: 1fr !important;
        gap: 10px;
      }
      ha-card.compact-mode .gauges-row {
        gap: 8px;
      }
      ha-card.compact-mode .gauge-card {
        padding: 6px 4px 6px;
      }
      ha-card.compact-mode .gauge-svg {
        max-width: 130px;
      }
      ha-card.compact-mode .gauge-label {
        font-size: 12px;
        margin-top: 2px;
      }
      ha-card.compact-mode .metrics-bar {
        grid-template-columns: repeat(2, 1fr);
        gap: 6px;
      }
      ha-card.compact-mode .metric-block {
        padding: 6px 4px;
      }
      ha-card.compact-mode .energy-grid {
        grid-template-columns: repeat(3, 1fr);
        gap: 6px;
      }
      ha-card.compact-mode .energy-card {
        padding: 6px 4px;
      }
      ha-card.compact-mode .energy-val {
        font-size: 15px;
      }
      ha-card.compact-mode #echart-container {
        min-height: 110px !important;
      }

      @media (max-width: 360px) {
        .metrics-bar { grid-template-columns: repeat(2, 1fr); }
        .metric-val { font-size: 14px; }
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
