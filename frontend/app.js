/* SafeRoute Analytics - front end
   One page per section; data is fetched lazily and re-fetched when filters change. */
'use strict';

const API = location.protocol === 'file:' ? 'http://127.0.0.1:5050/api' : '/api';

const EXPECTED_API_VERSION = 2;
const SEVERITIES = ['Fatal', 'Serious', 'Minor', 'Property Damage Only'];
const SEV_COLOR = { 'Fatal': '#c94f43', 'Serious': '#d9822b', 'Minor': '#5d9568', 'Property Damage Only': '#4f8b9b' };
const SEV_WEIGHT = { 'Fatal': 1, 'Serious': 0.6, 'Minor': 0.35, 'Property Damage Only': 0.2 };
const PALETTE = ['#39785b', '#d49a42', '#c96d4b', '#4f8b9b', '#8a9b63', '#a87958', '#5d7892', '#b7a16a', '#6b9b78', '#6e8b80'];
const ACCENT = '#39785b';
const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
const FILTERED_PAGES = ['dashboard', 'map', 'charts', 'risk'];

const $ = (id) => document.getElementById(id);
const fmt = (n) => (typeof n === 'number' ? n.toLocaleString('en-IN') : n);
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const label = (s) => (s === 'Property Damage Only' ? 'Property damage' : s);

const state = { page: 'dashboard', version: 0, rendered: {}, filters: null, mapMode: 'heat', chartTab: 'distributions', tabRendered: {} };

/* ── helpers ─────────────────────────────────────────────────────────────── */

function toast(message, ms = 3500) {
  const el = $('toast');
  el.textContent = message;
  el.classList.add('show');
  clearTimeout(toast.t);
  toast.t = setTimeout(() => el.classList.remove('show'), ms);
}

function filterQuery() {
  const p = new URLSearchParams({ city: $('fCity').value, year: $('fYear').value, severity: $('fSeverity').value });
  return p.toString();
}

async function api(path, { filtered = true, options } = {}) {
  const url = API + path + (filtered ? (path.includes('?') ? '&' : '?') + filterQuery() : '');
  const res = await fetch(url, options);
  let body = null;
  try { body = await res.json(); } catch (_) { /* non-JSON error */ }
  if (!res.ok) throw new Error((body && body.error) || `Request failed (${res.status})`);
  return body;
}

function merge(base, extra) {
  const out = Object.assign({}, base);
  for (const [k, v] of Object.entries(extra || {})) {
    out[k] = v && typeof v === 'object' && !Array.isArray(v) && base[k] && typeof base[k] === 'object' ? merge(base[k], v) : v;
  }
  return out;
}

const AXIS = { gridcolor: '#e9ede7', zerolinecolor: '#e3e8e1', linecolor: '#e3e8e1', tickfont: { color: '#66726b', size: 11 }, title: { font: { size: 11, color: '#66726b' } }, automargin: true };
const LAYOUT = {
  paper_bgcolor: 'rgba(0,0,0,0)', plot_bgcolor: 'rgba(0,0,0,0)',
  font: { family: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif', size: 12, color: '#1f2a24' },
  margin: { l: 48, r: 16, t: 8, b: 40 }, colorway: PALETTE,
  xaxis: AXIS, yaxis: AXIS,
  legend: { orientation: 'h', y: -0.22, font: { size: 11, color: '#66726b' } },
  hoverlabel: { font: { size: 12 } },
};

function plot(id, traces, layout = {}) {
  const el = $(id);
  if (!el) return;
  // Plotly mutates the layout it receives, so every chart gets its own deep copy of the defaults.
  return Plotly.react(el, traces, merge(structuredClone(LAYOUT), layout), { displayModeBar: false, responsive: true });
}

function chartError(id, err) {
  const el = $(id);
  if (!el) return;
  try { Plotly.purge(el); } catch (_) { /* nothing plotted yet */ }
  el.innerHTML = `<div class="chart-error">Chart could not be loaded: ${esc(err.message || err)}</div>`;
}

/* A render function that fails shows an inline message instead of breaking the page. */
async function safe(ids, fn) {
  try { await fn(); } catch (err) {
    console.error(err);
    [].concat(ids).forEach((id) => chartError(id, err));
    toast(err.message || String(err));
  }
}

/* ── navigation and filters ──────────────────────────────────────────────── */

function showPage(page) {
  if (!$('page-' + page)) page = 'dashboard';
  state.page = page;
  document.querySelectorAll('.page').forEach((p) => p.classList.toggle('active', p.id === 'page-' + page));
  document.querySelectorAll('#nav button').forEach((b) => {
    const on = b.dataset.page === page;
    b.classList.toggle('active', on);
    on ? b.setAttribute('aria-current', 'page') : b.removeAttribute('aria-current');
  });
  $('filterBar').classList.toggle('hidden', !FILTERED_PAGES.includes(page));
  if (location.hash !== '#' + page) history.replaceState(null, '', '#' + page);
  renderPage(page);
}

function renderPage(page) {
  if (state.rendered[page] === state.version) {
    if (page === 'map' && map) map.invalidateSize();
    return;
  }
  state.rendered[page] = state.version;
  ({ dashboard: renderDashboard, map: renderMap, charts: renderCharts, risk: renderRisk, predict: renderPredictor, tools: renderTools })[page]();
}

function onFilterChange() {
  state.version += 1;
  state.tabRendered = {};
  updateFilterNote();
  renderPage(state.page);
}

async function updateFilterNote() {
  const note = $('filterNote');
  try {
    const k = await api('/kpis');
    const n = k.total_accidents || 0;
    note.textContent = n ? `${fmt(n)} ${n === 1 ? 'accident' : 'accidents'}` : 'No accidents match these filters';
    note.classList.toggle('warn', !n);
  } catch (err) { note.textContent = ''; }
}

async function loadFilters() {
  const f = await api('/filters', { filtered: false });
  state.filters = f;
  f.cities.forEach((c) => $('fCity').add(new Option(c, c)));
  f.years.forEach((y) => $('fYear').add(new Option(y, y)));
  f.severities.forEach((s) => $('fSeverity').add(new Option(s, s)));
  $('datasetMeta').textContent = `${fmt(f.total_records)} records · ${f.cities.length} cities · ${f.years[0]}–${f.years[f.years.length - 1]}`;
}

/* ── dashboard ───────────────────────────────────────────────────────────── */

function renderDashboard() {
  safe(['d-year', 'd-severity', 'd-city', 'd-hour'], async () => {
    const [k, t, s, cs] = await Promise.all([api('/kpis'), api('/charts/temporal'), api('/charts/summary'), api('/charts/city-severity')]);

    const kpis = k.empty ? [] : [
      ['Accidents', fmt(k.total_accidents), `${k.cities} cities`],
      ['Fatal accidents', fmt(k.fatal_count), `${k.fatal_pct}% of accidents`, 'fatal'],
      ['Fatalities', fmt(k.total_fatalities), ''],
      ['Injuries', fmt(k.total_injuries), ''],
      ['Peak hour', `${String(k.peak_hour).padStart(2, '0')}:00`, 'most accidents'],
      ['Most fatalities', k.top_city, 'city'],
    ];
    $('kpis').innerHTML = kpis.map(([l, v, sub, cls]) => `<div class="kpi ${cls || ''}"><div class="kpi-label">${esc(l)}</div><div class="kpi-value" title="${esc(v)}">${esc(v)}</div><div class="kpi-sub">${esc(sub)}</div></div>`).join('');
    $('insights').innerHTML = k.empty ? '' : [
      `<li>Most common cause: <b>${esc(k.top_cause)}</b></li>`,
      `<li>Busiest hour: <b>${String(k.peak_hour).padStart(2, '0')}:00–${String((k.peak_hour + 1) % 24).padStart(2, '0')}:00</b></li>`,
      `<li>Most fatalities: <b>${esc(k.top_city)}</b></li>`,
    ].join('');

    const years = t.yearly.map((d) => d.year);
    plot('d-year', [
      { x: years, y: t.yearly.map((d) => d.accidents), name: 'Accidents', mode: 'lines+markers', line: { color: ACCENT, width: 2.5 }, marker: { size: 6 } },
      { x: years, y: t.yearly.map((d) => d.fatalities), name: 'Fatalities', mode: 'lines+markers', line: { color: '#c96d4b', width: 2.5 }, marker: { size: 6 } },
    ], { xaxis: { dtick: 1, tickformat: 'd', tickangle: -45 }, yaxis: { rangemode: 'tozero' } });

    const sev = s.severity.filter((d) => d.count > 0);
    const total = sev.reduce((a, d) => a + d.count, 0);
    plot('d-severity', [{
      type: 'pie', hole: 0.62, sort: false, direction: 'clockwise',
      labels: sev.map((d) => label(d.label)), values: sev.map((d) => d.count),
      marker: { colors: sev.map((d) => SEV_COLOR[d.label]), line: { color: '#fff', width: 2 } },
      textinfo: 'none', hovertemplate: '<b>%{label}</b><br>%{value:,} (%{percent})<extra></extra>',
    }], { margin: { l: 8, r: 8, t: 8, b: 8 }, legend: { orientation: 'h', y: -0.05, x: 0.5, xanchor: 'center' },
          annotations: [{ text: `<b>${fmt(total)}</b><br><span style="font-size:11px;color:#66726b">accidents</span>`, showarrow: false, font: { size: 20 } }] });

    plot('d-city', SEVERITIES.map((sv) => ({
      type: 'bar', orientation: 'h', name: label(sv), y: cs.cities, x: cs.series[sv],
      marker: { color: SEV_COLOR[sv] }, hovertemplate: '%{y}<br>' + label(sv) + ': %{x:,}<extra></extra>',
    })), { barmode: 'stack', yaxis: { autorange: 'reversed' }, margin: { l: 90 }, xaxis: { title: { text: 'Accidents' } }, legend: { traceorder: 'normal' } });

    const peak = Math.max(...t.hourly.map((d) => d.accidents));
    plot('d-hour', [{
      type: 'bar', x: t.hourly.map((d) => d.hour), y: t.hourly.map((d) => d.accidents),
      marker: { color: t.hourly.map((d) => (d.accidents === peak && peak > 0 ? '#c96d4b' : ACCENT)) },
      hovertemplate: '%{x}:00 – %{y:,} accidents<extra></extra>',
    }], { xaxis: { dtick: 2, range: [-0.6, 23.6], title: { text: 'Hour of day' } }, yaxis: { title: { text: 'Accidents' } }, bargap: 0.2 });
  });
}

/* ── map ─────────────────────────────────────────────────────────────────── */

const INDIA_BOUNDS = [[6, 68], [36, 97.5]];
let map = null;
let mapLayer = null;
let mapData = null;

function ensureMap() {
  if (map) return;
  map = L.map('map', { minZoom: 4, preferCanvas: true, worldCopyJump: true });
  map.fitBounds(INDIA_BOUNDS);
  // OpenStreetMap tiles need no API key. (Carto's hosted basemaps now do.)
  const tiles = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors', maxZoom: 18,
  }).addTo(map);
  let tileWarned = false;
  tiles.on('tileerror', () => { if (!tileWarned) { tileWarned = true; toast('Map background could not be loaded. Check your internet connection.'); } });
}

function renderMap() {
  $('mapLegend').innerHTML = SEVERITIES.map((s) => `<span><i class="dot" style="background:${SEV_COLOR[s]}"></i>${esc(label(s))}</span>`).join('');
  ensureMap();
  map.invalidateSize();
  $('mapStat').textContent = 'Loading…';
  safe([], async () => {
    const [data, hot] = await Promise.all([api('/map-data'), api('/analytics/hotspots')]);
    mapData = data;
    drawMapLayer(true);
    drawHotspots(hot);
  }).then(() => { if (!mapData) $('mapStat').textContent = 'Map data unavailable'; });
}

function drawMapLayer(fit) {
  if (!map || !mapData) return;
  if (mapLayer) { map.removeLayer(mapLayer); mapLayer = null; }
  const pts = mapData.points;
  const stat = $('mapStat');

  if (fit) {
    if ($('fCity').value !== 'all' && pts.length) map.fitBounds(L.latLngBounds(pts.map((p) => [p.latitude, p.longitude])).pad(0.2), { maxZoom: 11 });
    else map.fitBounds(INDIA_BOUNDS);
  }
  if (!pts.length) { stat.textContent = 'No accidents match these filters'; return; }

  if (state.mapMode === 'heat') {
    const data = pts.map((p) => [p.latitude, p.longitude, SEV_WEIGHT[p.severity] || 0.3]);
    mapLayer = L.heatLayer(data, { radius: 20, blur: 24, minOpacity: 0.3, maxZoom: 9,
      gradient: { 0.2: '#d9e8d2', 0.45: '#e9c46a', 0.7: '#d9822b', 1: '#c94f43' } });
    stat.textContent = `${fmt(pts.length)} of ${fmt(mapData.total)} accidents shown`;
  } else if (state.mapMode === 'clusters') {
    const cl = mapData.clusters;
    const risks = cl.map((c) => c.risk).sort((a, b) => a - b);
    const q = (f) => risks[Math.floor((risks.length - 1) * f)] ?? 0;
    const lo = q(0.33), hi = q(0.66);
    mapLayer = L.layerGroup(cl.map((c) => {
      const color = c.risk >= hi ? SEV_COLOR.Fatal : c.risk >= lo ? SEV_COLOR.Serious : SEV_COLOR.Minor;
      return L.circleMarker([c.lat, c.lon], { radius: Math.min(26, 5 + Math.sqrt(c.count) * 1.6), color, weight: 1.5, fillColor: color, fillOpacity: 0.55 })
        .bindPopup(`<b>${esc(c.city)}</b><br>Accidents: ${fmt(c.count)}<br>Fatalities: ${fmt(c.fatalities)}<br>Injuries: ${fmt(c.injuries)}`);
    }));
    stat.textContent = `${cl.length} hotspot clusters (larger = more accidents, redder = higher severity)`;
  } else {
    mapLayer = L.layerGroup(pts.map((p) => L.circleMarker([p.latitude, p.longitude], { radius: 5, color: '#fff', weight: 1, fillColor: SEV_COLOR[p.severity] || '#888', fillOpacity: 0.9 })
      .bindPopup(`<b style="color:${SEV_COLOR[p.severity]}">${esc(p.severity)}</b><br>${esc(p.city)} · ${esc(p.date)}<br>${esc(p.road_type)} · ${esc(p.weather_condition)}<br>Cause: ${esc(p.cause)}<br>Fatalities ${fmt(p.fatalities)} · Injuries ${fmt(p.injuries)}`)));
    stat.textContent = `${fmt(pts.length)} of ${fmt(mapData.total)} accidents shown`;
  }
  mapLayer.addTo(map);
}

function drawHotspots(rows) {
  const max = Math.max(1, ...rows.map((r) => r.risk_score));
  $('hotspotTable').querySelector('tbody').innerHTML = rows.length ? rows.map((r, i) => `
    <tr><td>${i + 1}</td><td>${esc(r.city)}</td><td class="num">${fmt(r.total)}</td><td class="num">${fmt(r.fatalities)}</td><td class="num">${fmt(r.injuries)}</td>
    <td><span class="bar" style="width:${Math.round((r.risk_score / max) * 90)}px"></span>${fmt(r.risk_score)}</td></tr>`).join('')
    : '<tr><td colspan="6" class="muted">No data for these filters</td></tr>';
}

/* ── charts page ─────────────────────────────────────────────────────────── */

function loadImages(tab) {
  document.querySelectorAll(`#tab-${tab} img.viz`).forEach((img) => {
    img.classList.remove('loaded', 'failed');
    img.onload = () => img.classList.add('loaded');
    img.onerror = () => { img.classList.add('failed'); img.removeAttribute('src'); img.alt = 'This chart could not be loaded'; toast('A chart image failed to load. Check the server log.'); };
    img.src = `${API}/viz/${img.dataset.viz}.png?${filterQuery()}&v=${state.version}`;
  });
}

function renderCharts() { showChartTab(state.chartTab); }

function showChartTab(tab) {
  state.chartTab = tab;
  document.querySelectorAll('#chartTabs button').forEach((b) => b.classList.toggle('active', b.dataset.tab === tab));
  document.querySelectorAll('.tab-panel').forEach((p) => p.classList.toggle('active', p.id === 'tab-' + tab));
  if (state.tabRendered[tab] === state.version) return;
  state.tabRendered[tab] = state.version;
  loadImages(tab);
  ({ comparisons: chartsComparisons, proportions: chartsProportions, patterns: chartsPatterns })[tab]?.();
}

function donut(id, rows, name) {
  const total = rows.reduce((a, d) => a + d.count, 0);
  plot(id, [{
    type: 'pie', hole: 0.55, sort: true, domain: { x: [0, 0.78], y: [0, 1] }, labels: rows.map((d) => d.label), values: rows.map((d) => d.count),
    marker: { colors: PALETTE, line: { color: '#fff', width: 2 } }, textinfo: 'percent', textposition: 'inside',
    hovertemplate: '<b>%{label}</b><br>%{value:,} (%{percent})<extra></extra>',
  }], { margin: { l: 8, r: 8, t: 8, b: 8 }, legend: { orientation: 'v', y: 0.5, x: 0.86 },
        annotations: [{ text: `<b>${fmt(total)}</b><br><span style="font-size:11px;color:#66726b">${name}</span>`, showarrow: false, font: { size: 16 }, x: 0.39, y: 0.5, xref: 'paper', yref: 'paper' }] });
}

function chartsComparisons() {
  safe(['c-city', 'c-road'], async () => {
    const [cs, cas] = await Promise.all([api('/charts/city-severity'), api('/charts/casualties')]);
    plot('c-city', SEVERITIES.map((sv) => ({ type: 'bar', orientation: 'h', name: label(sv), y: cs.cities, x: cs.series[sv], marker: { color: SEV_COLOR[sv] } })),
      { barmode: 'stack', yaxis: { autorange: 'reversed' }, margin: { l: 90 }, legend: { traceorder: 'normal' } });
    const roads = cas.by_road;
    plot('c-road', [
      { type: 'bar', name: 'Fatalities', x: roads.map((r) => r.road_type), y: roads.map((r) => r.fatalities), marker: { color: '#c94f43' } },
      { type: 'bar', name: 'Injuries', x: roads.map((r) => r.road_type), y: roads.map((r) => r.injuries), marker: { color: '#d49a42' } },
    ], { barmode: 'group', yaxis: { title: { text: 'People' } } });
  });
}

function chartsProportions() {
  safe(['pr-weather', 'pr-road', 'pr-vehicle'], async () => {
    const s = await api('/charts/summary');
    donut('pr-weather', s.weather, 'accidents');
    donut('pr-road', s.road_types, 'accidents');
    donut('pr-vehicle', s.vehicles, 'accidents');
  });
}

function chartsPatterns() {
  safe(['a-scatter', 'a-cause'], async () => {
    const [pts, cas] = await Promise.all([api('/charts/scatter'), api('/charts/casualties')]);
    // Injuries are whole numbers, so jitter slightly (display only) to show overlapping points.
    const jitter = (v) => v + (Math.random() - 0.5) * 0.35;
    plot('a-scatter', SEVERITIES.map((sv) => {
      const rows = pts.filter((p) => p.severity === sv);
      return { type: 'scatter', mode: 'markers', name: label(sv), x: rows.map((p) => p.speed_kmh), y: rows.map((p) => jitter(p.injuries)),
        marker: { color: SEV_COLOR[sv], size: 5, opacity: 0.55 }, hovertemplate: 'Speed %{x} km/h<extra>' + label(sv) + '</extra>' };
    }), { xaxis: { title: { text: 'Speed (km/h)' } }, yaxis: { title: { text: 'Injuries (jittered)' } } });
    const causes = cas.by_cause;
    plot('a-cause', [
      { type: 'bar', name: 'Fatalities', x: causes.map((c) => c.cause), y: causes.map((c) => c.fatalities), marker: { color: '#c94f43' } },
      { type: 'bar', name: 'Injuries', x: causes.map((c) => c.cause), y: causes.map((c) => c.injuries), marker: { color: '#d49a42' } },
    ], { barmode: 'group', yaxis: { title: { text: 'People' } } });
  });
}

/* ── risk analysis ───────────────────────────────────────────────────────── */

function renderRisk() {
  safe(['r-hour', 'r-dow', 'r-month', 'r-road', 'r-cause'], async () => {
    const [t, cas] = await Promise.all([api('/charts/temporal'), api('/charts/casualties')]);
    const dual = (id, xs, accidents, fatalities, xaxis = {}) => plot(id, [
      { type: 'bar', name: 'Accidents', x: xs, y: accidents, marker: { color: ACCENT }, yaxis: 'y' },
      { type: 'scatter', mode: 'lines+markers', name: 'Fatalities', x: xs, y: fatalities, line: { color: '#c96d4b', width: 2.5 }, marker: { size: 5 }, yaxis: 'y2' },
    ], { xaxis, yaxis: { title: { text: 'Accidents' }, rangemode: 'tozero' },
         yaxis2: Object.assign({}, AXIS, { overlaying: 'y', side: 'right', showgrid: false, rangemode: 'tozero', title: { text: 'Fatalities', font: { size: 11, color: '#66726b' } } }), margin: { r: 48 } });
    dual('r-hour', t.hourly.map((d) => d.hour), t.hourly.map((d) => d.accidents), t.hourly.map((d) => d.fatalities), { dtick: 2, range: [-0.6, 23.6], title: { text: 'Hour of day' } });
    dual('r-dow', t.day_of_week.map((d) => d.day.slice(0, 3)), t.day_of_week.map((d) => d.accidents), t.day_of_week.map((d) => d.fatalities));
    dual('r-month', t.monthly.map((d) => d.month.slice(0, 3)), t.monthly.map((d) => d.accidents), t.monthly.map((d) => d.fatalities));

    const rate = (rows, key, id, color) => {
      const r = rows.map((x) => ({ k: x[key], v: Number.isFinite(x.fatality_rate) ? x.fatality_rate : x.fatalities / x.accidents }))
        .filter((x) => Number.isFinite(x.v)).sort((a, b) => b.v - a.v);
      if (!r.length || r.every((x) => x.v === 0)) return chartError(id, new Error('no fatality data for these filters'));
      plot(id, [{ type: 'bar', x: r.map((x) => x.k), y: r.map((x) => x.v), marker: { color }, hovertemplate: '%{x}<br>%{y:.2f} fatalities per accident<extra></extra>' }],
        { yaxis: { title: { text: 'Fatalities per accident' }, rangemode: 'tozero' } });
    };
    rate(cas.by_road, 'road_type', 'r-road', '#c96d4b');
    rate(cas.by_cause, 'cause', 'r-cause', '#c96d4b');
  });
}

/* ── predictor ───────────────────────────────────────────────────────────── */

function fillSelect(id, items, selected) {
  const el = $(id);
  el.innerHTML = '';
  items.forEach((v) => el.add(new Option(v, v)));
  if (selected && items.includes(selected)) el.value = selected;
}

function renderPredictor() {
  const f = state.filters;
  if (f && !$('p-road').options.length) {
    fillSelect('p-month', MONTHS.map((_, i) => i + 1));
    [...$('p-month').options].forEach((o, i) => { o.textContent = MONTHS[i]; });
    $('p-month').value = '6';
    fillSelect('p-road', f.road_types, 'Urban Road');
    fillSelect('p-weather', f.weather, 'Clear');
    fillSelect('p-light', f.light_conditions, 'Daylight');
    fillSelect('p-cause', f.causes, 'Over Speeding');
    fillSelect('p-vehicle', f.vehicle_types, 'Car');
    fillSelect('p-city', f.cities, 'New Delhi');
  }
  safe(['m-features', 'm-confusion'], async () => {
    let m;
    try { m = await api('/ml-metrics', { filtered: false }); } catch (err) {
      $('mlMetrics').innerHTML = `<div class="error-box">${esc(err.message)}</div>`;
      throw err;
    }
    const pct = (v) => (v * 100).toFixed(1) + '%';
    $('mlMeta').textContent = `${fmt(m.training_rows)} training / ${fmt(m.test_rows)} test records`;
    $('mlMetrics').innerHTML = [
      ['Accuracy', pct(m.accuracy)], ['Always-"Fatal" baseline', pct(m.majority_baseline)],
      ['Balanced accuracy', pct(m.balanced_accuracy)], ['Macro F1', m.macro_f1.toFixed(2)],
    ].map(([l, v]) => `<div class="metric"><b>${v}</b><span>${esc(l)}</span></div>`).join('');
    const fatalShare = (m.class_share || {}).Fatal;
    $('mlNote').textContent = `${fatalShare ? Math.round(fatalShare * 100) + '% of records are Fatal, ' : ''}so accuracy is close to what a model that always answers "Fatal" would score. Balanced accuracy of about 25% is chance level for four classes: with these inputs the model has little power to separate severities, so treat predictions as illustrative.`;

    const fi = m.feature_importance.slice(0, 10).reverse();
    plot('m-features', [{ type: 'bar', orientation: 'h', x: fi.map((d) => d.importance), y: fi.map((d) => d.feature.replace(/_/g, ' ')), marker: { color: ACCENT }, hovertemplate: '%{y}: %{x:.1%}<extra></extra>' }],
      { margin: { l: 120 }, xaxis: { tickformat: '.0%', title: { text: 'Share of importance' } } });

    const classes = m.target_classes;
    const names = classes.map(label);
    const cm = m.confusion_matrix;
    const rowTotals = cm.map((r) => r.reduce((a, b) => a + b, 0) || 1);
    plot('m-confusion', [{
      type: 'heatmap', z: cm.map((r, i) => r.map((v) => v / rowTotals[i])), x: names, y: names, text: cm.map((r) => r.map(String)),
      texttemplate: '%{text}', colorscale: [[0, '#f4f7f3'], [1, ACCENT]], showscale: false, zmin: 0, zmax: 1,
      hovertemplate: 'Actual %{y}<br>Predicted %{x}<br>%{text} records (%{z:.0%} of actual)<extra></extra>',
    }], { xaxis: { title: { text: 'Predicted' }, side: 'bottom' }, yaxis: { title: { text: 'Actual' }, autorange: 'reversed' }, margin: { l: 110 } });
  });
}

function renderPrediction(r) {
  const probs = SEVERITIES.filter((s) => s in r.probabilities).map((s) => [s, r.probabilities[s]]);
  $('result').innerHTML = `
    <header><h3>Prediction</h3></header>
    <div class="pred"><span class="pred-pill" style="background:${SEV_COLOR[r.prediction] || ACCENT}">${esc(label(r.prediction))}</span><span class="pred-conf">${r.confidence}% probability</span></div>
    ${probs.map(([s, p]) => `<div class="prob"><span>${esc(label(s))}</span><div class="prob-track"><div class="prob-fill" style="width:${p}%;background:${SEV_COLOR[s]}"></div></div><span class="prob-val">${p}%</span></div>`).join('')}
    <p class="caveat">Illustrative only. See Model quality below: this model performs at about chance level for separating severities.</p>`;
}

/* ── tools comparison ────────────────────────────────────────────────────── */

function renderTools() {
  safe(['t-radar'], async () => {
    const { tools } = await api('/analytics/comparison', { filtered: false });
    const criteria = [['usability', 'Ease of use'], ['flexibility', 'Flexibility'], ['visual_appeal', 'Visual appeal'], ['interactivity', 'Interactivity']];
    plot('t-radar', tools.map((t, i) => ({
      type: 'bar', name: t.tool, x: criteria.map((c) => c[1]), y: criteria.map((c) => t[c[0]]), marker: { color: PALETTE[i] },
      hovertemplate: t.tool + '<br>%{x}: %{y}/10<extra></extra>',
    })), { barmode: 'group', yaxis: { range: [0, 10.5], dtick: 2, title: { text: 'Score (out of 10)' } } });
    $('toolTable').querySelector('thead').innerHTML = '<tr><th>Tool</th><th>Best for</th></tr>';
    $('toolTable').querySelector('tbody').innerHTML = tools.map((t) => `<tr><td><b>${esc(t.tool)}</b></td><td style="white-space:normal">${esc(t.best_for)}</td></tr>`).join('');
  });
}

/* ── wiring ──────────────────────────────────────────────────────────────── */

function bind() {
  $('nav').addEventListener('click', (e) => { const b = e.target.closest('button[data-page]'); if (b) showPage(b.dataset.page); });
  ['fCity', 'fYear', 'fSeverity'].forEach((id) => $(id).addEventListener('change', onFilterChange));
  $('fReset').addEventListener('click', () => { ['fCity', 'fYear', 'fSeverity'].forEach((id) => { $(id).value = 'all'; }); onFilterChange(); });
  $('chartTabs').addEventListener('click', (e) => { const b = e.target.closest('button[data-tab]'); if (b) showChartTab(b.dataset.tab); });
  $('mapModes').addEventListener('click', (e) => {
    const b = e.target.closest('button[data-mode]');
    if (!b) return;
    state.mapMode = b.dataset.mode;
    document.querySelectorAll('#mapModes button').forEach((x) => x.classList.toggle('active', x === b));
    drawMapLayer(false);
  });
  $('p-hour').addEventListener('input', (e) => { $('oHour').textContent = e.target.value + ':00'; });
  $('p-speed').addEventListener('input', (e) => { $('oSpeed').textContent = e.target.value + ' km/h'; });
  $('predictForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = $('predictBtn');
    btn.disabled = true; btn.textContent = 'Predicting…';
    try {
      const body = {
        hour: +$('p-hour').value, month: +$('p-month').value, speed_kmh: +$('p-speed').value, vehicles_involved: +$('p-vehicles').value,
        road_type: $('p-road').value, weather_condition: $('p-weather').value, light_condition: $('p-light').value,
        cause: $('p-cause').value, vehicle_type: $('p-vehicle').value, city: $('p-city').value,
      };
      const r = await api('/predict', { filtered: false, options: { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) } });
      renderPrediction(r);
    } catch (err) {
      $('result').innerHTML = `<header><h3>Prediction</h3></header><div class="error-box">${esc(err.message)}</div>`;
    } finally {
      btn.disabled = false; btn.textContent = 'Predict severity';
    }
  });
  window.addEventListener('hashchange', () => showPage(location.hash.slice(1) || 'dashboard'));
}

async function checkBackend() {
  const banner = $('banner');
  const show = (html) => { banner.innerHTML = html; banner.hidden = false; };
  try {
    const h = await api('/health', { filtered: false });
    if ((h.api_version || 0) < EXPECTED_API_VERSION) {
      show('<b>Out-of-date server.</b> The backend answering on this port is an older version than this page. Stop every running copy (<code>Ctrl+C</code> in each terminal), then start this project again with <code>python app.py</code>.');
    } else if (!h.fatalities && !h.injuries) {
      show('<b>The dataset has no casualty numbers.</b> Casualty charts will be empty. Rebuild it with <code>python data_loader_india.py</code> and restart the server.');
    }
  } catch (err) {
    show('<b>Out-of-date or unreachable server.</b> This page needs the matching backend. Stop every running copy (<code>Ctrl+C</code>), then run <code>python app.py</code> from this project folder.');
  }
}

(async function init() {
  bind();
  checkBackend();
  try { await loadFilters(); } catch (err) {
    toast('Could not reach the server. Start it with: python app.py', 8000);
    console.error(err);
  }
  updateFilterNote();
  showPage(location.hash.slice(1) || 'dashboard');
})();
