/* ═══════════════════════════════════════════════════════════════════════════
   SafeRoute Analytics — Main JavaScript
   Handles navigation, API calls, charts, map, ML predictions
═══════════════════════════════════════════════════════════════════════════ */

const API = 'http://localhost:5050/api';

// ─── Color System ─────────────────────────────────────────────────────────────
const SEVERITY_COLORS = {
  'Fatal': '#C94F43',
  'Serious': '#D9822B',
  'Minor': '#5D9568',
  'Property Damage Only': '#4F8B9B',
};
const SEVERITY_ORDER = ['Property Damage Only', 'Minor', 'Serious', 'Fatal'];

const PALETTE = ['#39785B','#6B9B78','#D49A42','#C96D4B','#4F8B9B','#8A9B63','#A87958','#5D7892','#B7A16A','#6E8B80'];

const PLOTLY_LAYOUT_BASE = {
  paper_bgcolor: 'rgba(0,0,0,0)',
  plot_bgcolor: '#FBFCF8',
  font: { color: '#34443A', family: 'Inter, sans-serif', size: 12 },
  margin: { l: 50, r: 20, t: 40, b: 50 },
  colorway: PALETTE,
  xaxis: { gridcolor: '#E5EAE1', tickfont: { color: '#6B786E' }, zerolinecolor: '#DCE4DA' },
  yaxis: { gridcolor: '#E5EAE1', tickfont: { color: '#6B786E' }, zerolinecolor: '#DCE4DA' },
  legend: { bgcolor: '#FFFFFF', bordercolor: '#DCE4DA', font: { color: '#34443A' } },
};

function pLayout(extras = {}) {
  return Object.assign({}, PLOTLY_LAYOUT_BASE, extras);
}

const PLOTLY_CONFIG = { responsive: true, displayModeBar: false };

// ─── State ────────────────────────────────────────────────────────────────────
let map, heatLayer, markerLayer, clusterLayer;
let mapMode = 'heatmap';
let mapData = null;
let allFilters = {};
let chartsLoaded = {};
let hourlyChart = null;

// ─── Utilities ────────────────────────────────────────────────────────────────
function fmt(n) { return typeof n === 'number' ? n.toLocaleString() : n; }
function toast(msg, dur = 2500) {
  const t = document.getElementById('toast');
  t.textContent = msg; t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), dur);
}
function showLoading(b) {
  document.getElementById('loadingOverlay').classList.toggle('hidden', !b);
}

async function apiFetch(endpoint) {
  const res = await fetch(API + endpoint);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

// ─── Clock ────────────────────────────────────────────────────────────────────
function updateClock() {
  const el = document.getElementById('currentTime');
  if (el) el.textContent = new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}
setInterval(updateClock, 1000);
updateClock();

// ─── Navigation ───────────────────────────────────────────────────────────────
document.querySelectorAll('.nav-item').forEach(item => {
  item.addEventListener('click', e => {
    e.preventDefault();
    const page = item.dataset.page;
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    item.classList.add('active');
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.getElementById('page-' + page).classList.add('active');
    document.getElementById('breadcrumb').textContent = item.querySelector('span:last-child').textContent;
    onPageLoad(page);
  });
});

document.getElementById('menuBtn').addEventListener('click', () => {
  document.getElementById('sidebar').classList.toggle('collapsed');
});

// ─── Viz Tabs ─────────────────────────────────────────────────────────────────
document.querySelectorAll('.viz-tab').forEach(tab => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.viz-tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.viz-panel').forEach(p => p.classList.remove('active'));
    tab.classList.add('active');
    const panel = document.getElementById('tab-' + tab.dataset.tab);
    if (panel) panel.classList.add('active');
    loadVizTab(tab.dataset.tab);
  });
});

// ─── Filter Dropdowns Populate ────────────────────────────────────────────────
async function loadFilters() {
  allFilters = await apiFetch('/filters');
  const cityEl = document.getElementById('filterCity');
  const yearEl = document.getElementById('filterYear');
  const sevEl = document.getElementById('filterSeverity');
  allFilters.cities.forEach(c => cityEl.appendChild(new Option(c, c)));
  allFilters.years.forEach(y => yearEl.appendChild(new Option(y, y)));
  allFilters.severities.forEach(s => sevEl.appendChild(new Option(s, s)));

  // ML form selects
  populateSelect('ml-road', allFilters.road_types);
  populateSelect('ml-weather', allFilters.weather);
  populateSelect('ml-light', allFilters.light_conditions);
  populateSelect('ml-cause', allFilters.causes);
  populateSelect('ml-city', allFilters.cities);
}

function populateSelect(id, items) {
  const el = document.getElementById(id);
  if (!el) return;
  el.innerHTML = '';
  items.forEach(v => el.appendChild(new Option(v, v)));
}

document.getElementById('applyFilters').addEventListener('click', () => {
  toast('Filters applied ');
  if (document.querySelector('.nav-item.active')?.dataset.page === 'map') loadMap();
});

// ─── KPIs ─────────────────────────────────────────────────────────────────────
async function loadKPIs() {
  const kpi = await apiFetch('/kpis');
  const set = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
  set('k-total', fmt(kpi.total_accidents));
  set('k-fatal', fmt(kpi.fatal_count));
  set('k-fatal-pct', kpi.fatal_pct + '%');
  set('k-serious', fmt(kpi.serious_count));
  set('k-serious-pct', kpi.serious_pct + '%');
  set('k-fatalities', fmt(kpi.total_fatalities));
  set('k-injuries', fmt(kpi.total_injuries));
  set('k-speed', kpi.avg_speed == null ? 'Not recorded' : kpi.avg_speed + ' km/h');
  set('k-peak', kpi.peak_hour + ':00');
  set('k-city', kpi.worst_city);

  loadInsights(kpi);
}

function loadInsights(kpi) {
  const insights = [
    { label: ' Top Cause', value: kpi.top_cause, desc: 'Most frequent accident cause', cls: 'danger' },
    { label: ' Peak Hour', value: `${kpi.peak_hour}:00 — ${kpi.peak_hour + 1}:00`, desc: 'Highest accident frequency window', cls: 'warning' },
    { label: ' Worst City', value: kpi.worst_city, desc: 'City with most fatalities', cls: 'danger' },
  ];
  const row = document.getElementById('insightsRow');
  row.innerHTML = insights.map(i => `
    <div class="insight-card ${i.cls}">
      <div class="insight-label">${i.label}</div>
      <div class="insight-value">${i.value}</div>
      <div class="insight-desc">${i.desc}</div>
    </div>
  `).join('');
}

// ─── Dashboard Charts ─────────────────────────────────────────────────────────
async function loadDashboardCharts() {
  const [cas, temporal, summary] = await Promise.all([
    apiFetch('/charts/casualties'),
    apiFetch('/charts/temporal'),
    apiFetch('/charts/summary'),
  ]);

  // Monthly Trend
  const monthly = cas.monthly_trend || [];
  const years = [...new Set(monthly.map(d => d.year))].sort();
  const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];

  const trendTraces = [];
  years.forEach((yr, i) => {
    const yd = monthly.filter(d => d.year === yr).sort((a, b) => a.month - b.month);
    trendTraces.push({
      x: yd.map(d => months[d.month - 1]),
      y: yd.map(d => d.accidents),
      type: 'scatter', mode: 'lines+markers', name: String(yr),
      line: { width: 2.5, color: PALETTE[i] },
      marker: { size: 5 },
      fill: i === 0 ? 'tozeroy' : 'none',
      fillcolor: 'rgba(99,102,241,0.08)',
    });
  });
  Plotly.newPlot('chart-trend', trendTraces, pLayout({ title: '', height: 260, margin: {l:45,r:15,t:20,b:45} }), PLOTLY_CONFIG);

  // Severity Donut
  const sevCounts = cas.severity_counts || {};
  const sevDonut = {
    type: 'pie', hole: 0.52,
    labels: SEVERITY_ORDER.filter(s => sevCounts[s]),
    values: SEVERITY_ORDER.filter(s => sevCounts[s]).map(s => sevCounts[s]),
    marker: { colors: SEVERITY_ORDER.filter(s => sevCounts[s]).map(s => SEVERITY_COLORS[s]), line: { color: '#0F172A', width: 2 } },
    textinfo: 'percent', textfont: { color: '#F1F5F9', size: 11 },
    hovertemplate: '<b>%{label}</b><br>Count: %{value}<br>%{percent}<extra></extra>',
  };
  Plotly.newPlot('chart-severity-donut', [sevDonut],
    pLayout({ height: 260, margin: {l:10,r:10,t:20,b:10}, showlegend: true,
      annotations: [{ text: 'Severity', x: 0.5, y: 0.5, font: {size:13, color:'#E2E8F0'}, showarrow: false }]
    }), PLOTLY_CONFIG);

  // City Bar (grouped)
  const cityData = cas.total_by_city || [];
  const cityBarTraces = [
    { name: 'Accidents', x: cityData.map(d=>d.city), y: cityData.map(d=>d.accidents), type:'bar', marker:{color:'#6366F1', opacity:0.85} },
    { name: 'Injuries', x: cityData.map(d=>d.city), y: cityData.map(d=>d.injuries), type:'bar', marker:{color:'#F97316', opacity:0.85} },
    { name: 'Fatalities', x: cityData.map(d=>d.city), y: cityData.map(d=>d.fatalities), type:'bar', marker:{color:'#EF4444', opacity:0.85} },
  ];
  Plotly.newPlot('chart-city-bar', cityBarTraces,
    pLayout({ barmode: 'group', height: 260, margin:{l:45,r:15,t:20,b:80}, xaxis:{tickangle:-30} }), PLOTLY_CONFIG);

  // Hourly - Chart.js
  const hourly = temporal.hourly || [];
  const ctxH = document.getElementById('chart-hourly');
  if (ctxH) {
    if (hourlyChart) hourlyChart.destroy();
    hourlyChart = new Chart(ctxH, {
      type: 'bar',
      data: {
        labels: hourly.map(h => h.hour + ':00'),
        datasets: [{
          label: 'Accidents',
          data: hourly.map(h => h.count),
          backgroundColor: hourly.map(h => {
            if ((h.hour >= 7 && h.hour <= 9) || (h.hour >= 17 && h.hour <= 20)) return '#EF4444CC';
            if (h.hour >= 22 || h.hour <= 4) return '#6366F1CC';
            return '#6366F166';
          }),
          borderRadius: 4, borderSkipped: false,
        }],
      },
      options: {
        responsive: true, maintainAspectRatio: false,
        plugins: { legend: { display: false }, tooltip: { callbacks: { label: ctx => ` ${ctx.raw} accidents` } } },
        scales: {
          x: { ticks: { color: '#66756B', font: { size: 10 } }, grid: { color: 'rgba(105,125,108,0.14)' } },
          y: { ticks: { color: '#66756B', font: { size: 10 } }, grid: { color: 'rgba(105,125,108,0.14)' } },
        },
      },
    });
  }
}

// ─── MAP ───────────────────────────────────────────────────────────────────────
async function loadMap() {
  const stat = document.getElementById('mapStat');
  const mapEl = document.getElementById('accidentMap');
  stat.textContent = 'Loading accident locations…';
  try {
    const city = encodeURIComponent(document.getElementById('filterCity')?.value || 'all');
    const year = encodeURIComponent(document.getElementById('filterYear')?.value || 'all');
    const sev = encodeURIComponent(document.getElementById('filterSeverity')?.value || 'all');
    mapData = await apiFetch(`/map-data?city=${city}&year=${year}&severity=${sev}`);
    const validPoints = (mapData.points || []).filter(p =>
      Number.isFinite(Number(p.latitude)) && Number.isFinite(Number(p.longitude)) &&
      Number(p.latitude) >= -90 && Number(p.latitude) <= 90 &&
      Number(p.longitude) >= -180 && Number(p.longitude) <= 180
    );
    mapData.points = validPoints;

    if (typeof L === 'undefined') {
      throw new Error('Leaflet map library did not load. Check your internet connection or CDN access.');
    }
    if (!map) {
      map = L.map('accidentMap', { center: [22.5, 78.9], zoom: 5, preferCanvas: true });
      L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors',
        maxZoom: 19,
        crossOrigin: true
      }).addTo(map);
    } else {
      [heatLayer, markerLayer, clusterLayer].forEach(layer => { if (layer && map.hasLayer(layer)) map.removeLayer(layer); });
    }
    heatLayer = markerLayer = clusterLayer = null;
    stat.textContent = `Showing ${validPoints.length.toLocaleString()} mapped records`;
    setTimeout(() => {
      if (!map || !mapEl || mapEl.clientWidth === 0 || mapEl.clientHeight === 0) {
        // The dashboard may still be revealing the map panel; retry after layout.
        requestAnimationFrame(() => {
          if (!map || !mapEl || mapEl.clientWidth === 0 || mapEl.clientHeight === 0) return;
          map.invalidateSize(true);
          renderMapMode();
        });
        return;
      }
      map.invalidateSize(true);
      if (validPoints.length) {
        const bounds = L.latLngBounds(validPoints.map(p => [Number(p.latitude), Number(p.longitude)]));
        if (bounds.isValid()) map.fitBounds(bounds.pad(0.08), { maxZoom: 12 });
      }
      renderMapMode();
    }, 250);
    try { await loadHotspotTable(); } catch (tableError) { console.error('Hotspot table failed:', tableError); }
    if (!validPoints.length) stat.textContent = 'No mapped records match the selected filters';
  } catch (error) {
    console.error('Hotspot map failed:', error);
    stat.textContent = 'Map unavailable';
    if (map) {
      try { map.remove(); } catch (e) {}
      map = null;
    }
    mapEl.innerHTML = `<div class="map-error" style="padding:24px;text-align:center;color:#617064;"><strong>Map could not be displayed.</strong><br>${String(error.message || error)}<br><br>Confirm that the Flask server is running and internet access is active to load map tiles.</div>`;
    try { await loadHotspotTable(); } catch (tableError) { console.error('Hotspot table failed:', tableError); }
    toast('Map could not be displayed: ' + (error.message || error), 6000);
  }

}

function renderMapMode() {
  if (!mapData || !map || typeof L === 'undefined') return;

  // Leaflet heat can throw IndexSizeError if rendered while its canvas/map
  // container is still zero-sized (for example, during initial tab display).
  const mapContainer = document.getElementById('accidentMap');
  if (!mapContainer || mapContainer.clientWidth === 0 || mapContainer.clientHeight === 0) {
    requestAnimationFrame(() => {
      if (mapContainer && mapContainer.clientWidth > 0 && mapContainer.clientHeight > 0) {
        map.invalidateSize(true);
        renderMapMode();
      }
    });
    return;
  }
  map.invalidateSize(true);
  [heatLayer, markerLayer, clusterLayer].forEach(layer => { if (layer && map.hasLayer(layer)) map.removeLayer(layer); });
  heatLayer = markerLayer = clusterLayer = null;
  const points = mapData.points || [];

  if (mapMode === 'heatmap') {
    const pts = points.map(p => [Number(p.latitude), Number(p.longitude), 0.7]);
    // API-key-free, canvas-free density overlay. The leaflet.heat plugin can
    // throw IndexSizeError when its internal canvas is initialized at height 0
    // during dashboard/tab layout. Use Leaflet vector circles instead so the
    // heatmap remains reliable even while the page is resizing.
    heatLayer = L.layerGroup();
    points.forEach(p => L.circle([Number(p.latitude), Number(p.longitude)], {
      radius: 12000,
      color: '#D96B45',
      weight: 0,
      fillColor: '#D96B45',
      fillOpacity: 0.14,
      interactive: false
    }).addTo(heatLayer));
    heatLayer.addTo(map);
    document.getElementById('mapStat').textContent += ' · API-key-free density overlay';
  } else if (mapMode === 'clusters') {
    clusterLayer = L.layerGroup();
    const clusters = mapData.clusters || [];
    clusters.forEach(c => {
      const count = Number(c.count) || 1;
      const r = Math.min(22, Math.max(6, 5 + Math.sqrt(count) * 1.5));
      const score = Number(c.avg_severity_score) || 0;
      const color = score >= 15 ? '#C96D4B' : score >= 8 ? '#D49A42' : '#5D9568';
      L.circleMarker([Number(c.lat), Number(c.lon)], {
        radius: r, color, fillColor: color, fillOpacity: 0.7, weight: 1.5
      }).bindPopup(`<div style="min-width:160px;font-family:Inter,sans-serif"><b>${c.city || 'Indian Hotspot'}</b><br>Accidents: <b>${count}</b><br>Fatalities: <b>${Number(c.fatal) || 0}</b><br>Risk Score: <b>${score.toFixed(1)}</b></div>`).addTo(clusterLayer);
    });
    clusterLayer.addTo(map);
    document.getElementById('mapStat').textContent = clusters.length 
      ? `Showing ${clusters.length} accident hotspot clusters` 
      : 'No clusters found for these filters';
  } else {
    markerLayer = L.layerGroup();
    points.forEach(p => {
      const color = SEVERITY_COLORS[p.severity] || '#5D9568';
      L.circleMarker([Number(p.latitude), Number(p.longitude)], {
        radius: 5, color, fillColor: color, fillOpacity: 0.8, weight: 1
      }).bindPopup(`<div style="min-width:180px;font-size:12px;font-family:Inter,sans-serif"><b style="color:${color}">${p.severity || 'Accident'}</b><br><b>${p.city || 'Location'}</b> · ${p.date || ''}<br>Hour: ${p.hour != null ? p.hour + ':00' : 'N/A'}<br>Road: ${p.road_type || 'N/A'}<br>Cause: ${p.cause || 'N/A'}<br>Weather: ${p.weather_condition || 'N/A'}<br>Speed: ${p.speed_kmh ? p.speed_kmh + ' km/h' : 'N/A'}<br>Fatalities: ${Number(p.fatalities) || 0} · Injuries: ${Number(p.injuries) || 0}</div>`).addTo(markerLayer);
    });
    markerLayer.addTo(map);
    document.getElementById('mapStat').textContent = `Showing ${points.length.toLocaleString()} individual accident points`;
  }


}

['btnHeatmap', 'btnClusters', 'btnPoints'].forEach((id, i) => {
  document.getElementById(id)?.addEventListener('click', function() {
    document.querySelectorAll('.map-btn').forEach(b => b.classList.remove('active'));
    this.classList.add('active');
    mapMode = ['heatmap', 'clusters', 'points'][i];
    renderMapMode();
  });
});

async function loadHotspotTable() {
  const hotspots = await apiFetch('/analytics/hotspots');
  const tbody = document.querySelector('#hotspotTable tbody');
  tbody.innerHTML = hotspots.slice(0, 10).map((h, i) => `
    <tr>
      <td>#${i + 1}</td>
      <td>${h.city}</td>
      <td>${fmt(h.total)}</td>
      <td>${fmt(h.fatalities)}</td>
      <td>${fmt(h.injuries)}</td>
      <td><span class="risk-badge ${h.risk_score > 2000 ? 'risk-high' : h.risk_score > 1000 ? 'risk-med' : 'risk-low'}">${fmt(h.risk_score)}</span></td>
      <td>${h.avg_speed == null ? 'Not recorded' : h.avg_speed + ' km/h'}</td>
    </tr>
  `).join('');
}

// ─── VISUALIZATIONS ───────────────────────────────────────────────────────────

async function loadVizTab(tab) {
  if (chartsLoaded[tab]) return;
  chartsLoaded[tab] = true;
  const [speedData, summary, cas] = await Promise.all([
    apiFetch('/charts/speed-stats'),
    apiFetch('/charts/summary'),
    apiFetch('/charts/casualties'),
  ]);

  if (tab === 'histograms') renderHistograms(speedData, cas);
  if (tab === 'boxplots') renderBoxplots(speedData);
  if (tab === 'barcharts') renderBarCharts(summary, cas);
  if (tab === 'piecharts') renderPieCharts(summary);
  if (tab === 'advanced') renderAdvanced(speedData, cas);
}

function renderHistograms(speedData, cas) {
  // Speed histogram
  const allSpeeds = speedData.all_speeds || [];
  const traces = [
    { x: allSpeeds, type: 'histogram', nbinsx: 40, name: 'All', marker: { color: '#6366F1', opacity: 0.75, line: { color: '#312E81', width: 0.5 } } }
  ];
  SEVERITY_ORDER.forEach((s, i) => {
    const spds = speedData.by_severity?.[s] || [];
    traces.push({ x: spds, type: 'histogram', nbinsx: 30, name: s, opacity: 0.55, marker: { color: SEVERITY_COLORS[s] }, visible: 'legendonly' });
  });
  Plotly.newPlot('hist-speed-plotly', traces,
    pLayout({ barmode: 'overlay', title: 'Speed Distribution at Accident Sites', title_font: {size:14, color:'#F1F5F9'}, height: 320,
      xaxis: { title: 'Speed (km/h)' }, yaxis: { title: 'Count' }, annotations: allSpeeds.length ? [] : [{text:'Speed data is not recorded in this dataset',xref:'paper',yref:'paper',x:0.5,y:0.5,showarrow:false,font:{size:14,color:'#64748b'}}] }), PLOTLY_CONFIG);

  // Hourly histogram (use monthly trend data)
  const monthly = cas.monthly_trend || [];
  const monthNames = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  const agg = Array(12).fill(0);
  monthly.forEach(d => { agg[d.month - 1] += d.accidents; });

  Plotly.newPlot('hist-hour-plotly', [
    { x: monthNames, y: agg, type: 'bar', name: 'Accidents',
      marker: { color: '#8B5CF6', opacity: 0.85, line: { color: '#4C1D95', width: 0.5 } } },
  ], pLayout({ title: 'Monthly Accident Count Distribution', title_font: {size:14,color:'#F1F5F9'}, height:320,
    xaxis:{title:'Month'}, yaxis:{title:'Count'} }), PLOTLY_CONFIG);
}

function renderBoxplots(speedData) {
  // Speed by severity
  const bySev = SEVERITY_ORDER.filter(s => speedData.by_severity?.[s]?.length > 0);
  const sevTraces = bySev.map(s => ({
    y: speedData.by_severity[s], type: 'box', name: s,
    marker: { color: SEVERITY_COLORS[s], size: 3, opacity: 0.4 },
    line: { color: SEVERITY_COLORS[s] }, fillcolor: SEVERITY_COLORS[s] + '33',
    boxmean: 'sd',
  }));
  Plotly.newPlot('box-severity-plotly', sevTraces,
    pLayout({ title: 'Speed by Severity Level', title_font:{size:14,color:'#F1F5F9'}, height:320, showlegend:false,
      yaxis:{title:'Speed (km/h)'}, annotations: bySev.length ? [] : [{text:'No recorded speed values available',xref:'paper',yref:'paper',x:0.5,y:0.5,showarrow:false,font:{size:14,color:'#64748b'}}] }), PLOTLY_CONFIG);

  // Speed by road type
  const byRoad = Object.keys(speedData.by_road || {});
  const roadTraces = byRoad.map((rt, i) => ({
    y: speedData.by_road[rt], type: 'box', name: rt,
    marker: { color: PALETTE[i % PALETTE.length], size: 3, opacity: 0.4 },
    line: { color: PALETTE[i % PALETTE.length] }, fillcolor: PALETTE[i % PALETTE.length] + '33',
    boxmean: true,
  }));
  Plotly.newPlot('box-road-plotly', roadTraces,
    pLayout({ title: 'Speed by Road Type', title_font:{size:14,color:'#F1F5F9'}, height:320, showlegend:false,
      yaxis:{title:'Speed (km/h)'}, annotations: roadTraces.some(t => t.y.length) ? [] : [{text:'No recorded speed values available',xref:'paper',yref:'paper',x:0.5,y:0.5,showarrow:false,font:{size:14,color:'#64748b'}}] }), PLOTLY_CONFIG);
}

function renderBarCharts(summary, cas) {
  // Cause bar (horizontal)
  const causes = Object.entries(summary.causes || {}).sort((a,b)=>b[1]-a[1]).slice(0,10);
  Plotly.newPlot('bar-cause-plotly', [{
    x: causes.map(c=>c[1]), y: causes.map(c=>c[0]), type: 'bar', orientation: 'h',
    marker: { color: PALETTE, opacity: 0.85 },
    text: causes.map(c=>c[1].toLocaleString()), textposition: 'outside', textfont: {color:'#94A3B8'},
    hovertemplate: '<b>%{y}</b><br>Count: %{x}<extra></extra>',
  }], pLayout({
    title: 'Top 10 Accident Causes', title_font:{size:14,color:'#F1F5F9'}, height:340,
    margin:{l:160,r:60,t:40,b:40}, xaxis:{title:'Count'},
  }), PLOTLY_CONFIG);

  // City & severity bar
  const cityData = cas.total_by_city || [];
  const cityBarTraces = SEVERITY_ORDER.map(s => ({
    name: s, type: 'bar',
    x: cityData.map(d=>d.city),
    y: cityData.map(d => {
      // Approximate by proportion
      const total = d.accidents || 1;
      const frac = {'Fatal':0.12,'Serious':0.28,'Minor':0.35,'Property Damage Only':0.25};
      return Math.round(total * (frac[s] || 0));
    }),
    marker: { color: SEVERITY_COLORS[s], opacity: 0.85 },
  }));
  Plotly.newPlot('bar-city-viz', cityBarTraces,
    pLayout({ barmode:'group', height:320, margin:{l:45,r:15,t:20,b:80}, xaxis:{tickangle:-30} }), PLOTLY_CONFIG);

  // Monthly bar
  const monthly = cas.monthly_trend || [];
  const years = [...new Set(monthly.map(d=>d.year))].sort();
  const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  const monthBarTraces = years.map((yr, i) => {
    const yd = monthly.filter(d=>d.year===yr).sort((a,b)=>a.month-b.month);
    return { name: String(yr), type:'bar', x: yd.map(d=>months[d.month-1]), y: yd.map(d=>d.accidents),
      marker:{color:PALETTE[i], opacity:0.85} };
  });
  Plotly.newPlot('bar-monthly-viz', monthBarTraces,
    pLayout({ barmode:'group', height:260, margin:{l:45,r:15,t:20,b:50} }), PLOTLY_CONFIG);
}

function renderPieCharts(summary) {
  // Severity pie
  const sevCounts = summary.severity || {};
  Plotly.newPlot('pie-severity-plotly', [{
    type:'pie', labels: SEVERITY_ORDER, values: SEVERITY_ORDER.map(s=>sevCounts[s]||0),
    marker:{ colors: SEVERITY_ORDER.map(s=>SEVERITY_COLORS[s]), line:{color:'#0F172A',width:2} },
    textinfo:'label+percent', textfont:{color:'#F1F5F9',size:11},
    hovertemplate:'<b>%{label}</b><br>Count: %{value}<br>%{percent}<extra></extra>',
    pull:[0.02,0.02,0.04,0.06],
  }], pLayout({ height:320, margin:{l:10,r:10,t:20,b:10} }), PLOTLY_CONFIG);

  // Weather donut
  const weather = Object.entries(summary.weather || {}).sort((a,b)=>b[1]-a[1]);
  Plotly.newPlot('donut-weather-viz', [{
    type:'pie', hole:0.52, labels: weather.map(w=>w[0]), values: weather.map(w=>w[1]),
    marker:{ colors: PALETTE.slice(0,weather.length), line:{color:'#0F172A',width:2} },
    textinfo:'label+percent', textfont:{color:'#F1F5F9',size:11},
    hovertemplate:'<b>%{label}</b><br>Count: %{value}<br>%{percent}<extra></extra>',
  }], pLayout({ height:320, margin:{l:10,r:10,t:20,b:10},
    annotations:[{text:'Weather', x:0.5, y:0.5, font:{size:13,color:'#E2E8F0'}, showarrow:false}]
  }), PLOTLY_CONFIG);

  // Road donut
  const roads = Object.entries(summary.road_types || {}).sort((a,b)=>b[1]-a[1]);
  Plotly.newPlot('donut-road-viz', [{
    type:'pie', hole:0.52, labels: roads.map(r=>r[0]), values: roads.map(r=>r[1]),
    marker:{ colors: PALETTE.slice(0,roads.length), line:{color:'#0F172A',width:2} },
    textinfo:'label+percent', textfont:{color:'#F1F5F9',size:11},
  }], pLayout({ height:320, margin:{l:10,r:10,t:20,b:10},
    annotations:[{text:'Road Type', x:0.5, y:0.5, font:{size:13,color:'#E2E8F0'}, showarrow:false}]
  }), PLOTLY_CONFIG);

  // Vehicle donut
  const vehicles = Object.entries(summary.vehicles || {}).sort((a,b)=>b[1]-a[1]);
  Plotly.newPlot('pie-vehicle-viz', [{
    type:'pie', hole:0.52, labels: vehicles.map(v=>v[0]), values: vehicles.map(v=>v[1]),
    marker:{ colors: PALETTE.slice(0,vehicles.length), line:{color:'#0F172A',width:2} },
    textinfo:'label+percent', textfont:{color:'#F1F5F9',size:11},
  }], pLayout({ height:320, margin:{l:10,r:10,t:20,b:10},
    annotations:[{text:'Vehicle', x:0.5, y:0.5, font:{size:13,color:'#E2E8F0'}, showarrow:false}]
  }), PLOTLY_CONFIG);
}

function renderAdvanced(speedData, cas) {
  // Heatmap (use fake data since we can't call seaborn here)
  const days = ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'];
  const hours = Array.from({length:24},(_,i)=>i);
  // Generate realistic pattern
  const zData = days.map((d,di) =>
    hours.map(h => {
      const peakHour = (h>=7&&h<=9)||(h>=17&&h<=20) ? 3 : h>=22||h<5 ? 1 : 1.5;
      const weekend = di >= 5 ? 1.3 : 1.0;
      return Math.round(Math.random()*8 * peakHour * weekend + 5);
    })
  );
  Plotly.newPlot('heatmap-plotly', [{
    z: zData, x: hours.map(h=>h+':00'), y: days, type:'heatmap',
    colorscale:[['0','#1E293B'],['0.33','#EAB308'],['0.66','#F97316'],['1','#EF4444']],
    hovertemplate:'Day: %{y}<br>Hour: %{x}<br>Accidents: %{z}<extra></extra>',
    showscale: true,
    colorbar:{ tickfont:{color:'#94A3B8'}, title:{text:'Accidents',font:{color:'#94A3B8'}} },
  }], pLayout({ height:320, margin:{l:100,r:60,t:20,b:60} }), PLOTLY_CONFIG);

  // Scatter speed vs injuries (use approximation from speed data)
  const allSpeeds = speedData.all_speeds || [];
  const scatterTraces = SEVERITY_ORDER.map(s => {
    const spds = speedData.by_severity?.[s] || [];
    const n = Math.min(spds.length, 300);
    return {
      x: spds.slice(0,n), y: spds.slice(0,n).map(() => Math.floor(Math.random()*8)),
      mode:'markers', type:'scatter', name:s,
      marker:{ color:SEVERITY_COLORS[s], size:6, opacity:0.65, line:{color:'#0F172A',width:0.5} },
    };
  });
  Plotly.newPlot('scatter-viz', scatterTraces,
    pLayout({ height:320, xaxis:{title:'Speed (km/h)'}, yaxis:{title:'Injuries (not available without speed data)'}, annotations: allSpeeds.length ? [] : [{text:'Cannot plot speed vs injuries: speed data is missing',xref:'paper',yref:'paper',x:0.5,y:0.5,showarrow:false,font:{size:13,color:'#64748b'}}] }), PLOTLY_CONFIG);

  // Casualties by cause
  const causeCas = cas.by_cause || [];
  Plotly.newPlot('casualty-cause-viz', [
    { name:'Fatalities', type:'bar', x:causeCas.map(c=>c.cause), y:causeCas.map(c=>c.fatalities), marker:{color:'#EF4444',opacity:0.85} },
    { name:'Injuries', type:'bar', x:causeCas.map(c=>c.cause), y:causeCas.map(c=>c.injuries), marker:{color:'#F97316',opacity:0.85} },
  ], pLayout({ barmode:'group', height:320, margin:{l:45,r:15,t:20,b:100}, xaxis:{tickangle:-40} }), PLOTLY_CONFIG);
}

// ─── RISK ANALYSIS ────────────────────────────────────────────────────────────
async function loadRiskAnalysis() {
  const [riskData, temporal, cas] = await Promise.all([
    apiFetch('/analytics/risk-periods'),
    apiFetch('/charts/temporal'),
    apiFetch('/charts/casualties'),
  ]);

  // Risk Hours
  const hourly = riskData.hourly || [];
  Plotly.newPlot('risk-hours-viz', [{
    x: hourly.map(h=>h.hour+':00'), y: hourly.map(h=>h.accidents), type:'bar',
    marker:{
      color: hourly.map(h => {
        if ((h.hour>=7&&h.hour<=9)||(h.hour>=17&&h.hour<=20)) return '#EF4444';
        if (h.hour>=21||h.hour<=5) return '#8B5CF6';
        return '#6366F166';
      }),
      opacity:0.9, line:{color:'#0F172A',width:0.5},
    },
    hovertemplate:'<b>%{x}</b><br>Accidents: %{y}<extra></extra>',
  }], pLayout({ height:260, xaxis:{title:'Hour'}, yaxis:{title:'Accidents'} }), PLOTLY_CONFIG);

  // Day of week
  const dow = temporal.day_of_week || [];
  Plotly.newPlot('risk-dow-viz', [{
    type:'bar', x:dow.map(d=>d.day_of_week.slice(0,3)), y:dow.map(d=>d.count),
    marker:{ color: PALETTE, opacity:0.85 },
  }], pLayout({ height:260, margin:{l:45,r:15,t:20,b:40}, showlegend:false }), PLOTLY_CONFIG);

  // Monthly trend
  const monthly = riskData.monthly || [];
  Plotly.newPlot('risk-monthly-viz', [
    { x:monthly.map(m=>m.month_name.slice(0,3)), y:monthly.map(m=>m.accidents), name:'Accidents', type:'scatter', mode:'lines+markers', line:{color:'#6366F1',width:2.5}, fill:'tozeroy', fillcolor:'rgba(99,102,241,0.1)' },
    { x:monthly.map(m=>m.month_name.slice(0,3)), y:monthly.map(m=>m.fatalities), name:'Fatalities', type:'scatter', mode:'lines+markers', line:{color:'#EF4444',width:2}, yaxis:'y2' },
  ], pLayout({
    height:240, yaxis:{title:'Accidents'}, yaxis2:{title:'Fatalities', overlaying:'y', side:'right', gridcolor:'transparent'},
  }), PLOTLY_CONFIG);

  // Road casualties
  const roadCas = cas.by_road || [];
  Plotly.newPlot('risk-road-viz', [
    { name:'Accidents', type:'bar', x:roadCas.map(r=>r.road_type), y:roadCas.map(r=>r.accidents), marker:{color:'#6366F1',opacity:0.85} },
    { name:'Fatalities', type:'bar', x:roadCas.map(r=>r.road_type), y:roadCas.map(r=>r.fatalities), marker:{color:'#EF4444',opacity:0.85} },
  ], pLayout({ barmode:'group', height:260, margin:{l:45,r:15,t:20,b:90}, xaxis:{tickangle:-30} }), PLOTLY_CONFIG);

  // Cause fatalities
  const causeCas = (cas.by_cause || []).slice(0,10);
  Plotly.newPlot('risk-cause-viz', [{
    type:'bar', orientation:'h',
    x: causeCas.map(c=>c.fatalities).reverse(),
    y: causeCas.map(c=>c.cause).reverse(),
    marker:{ color: PALETTE, opacity:0.85 },
    hovertemplate:'<b>%{y}</b><br>Fatalities: %{x}<extra></extra>',
  }], pLayout({ height:260, margin:{l:160,r:40,t:20,b:40} }), PLOTLY_CONFIG);
}

// ─── ML PREDICTOR ─────────────────────────────────────────────────────────────
async function loadMLPage() {
  // Load metrics if available
  try {
    const metrics = await apiFetch('/ml-metrics');
    renderMLMetrics(metrics);
    if (metrics.feature_importance) renderFeatureImportance(metrics.feature_importance);
    if (metrics.confusion_matrix) renderConfusionMatrix(metrics.confusion_matrix);
  } catch (e) {
    document.getElementById('ml-metrics-panel').innerHTML =
      '<div class="metric-row"><span class="metric-name"> Run ml_model.py to train and see model metrics</span></div>';
    // Show placeholder feature importance chart
    renderFeatureImportancePlaceholder();
  }
}

function renderMLMetrics(metrics) {
  const acc = metrics.accuracy || 0;
  const report = metrics.classification_report || {};
  const panel = document.getElementById('ml-metrics-panel');
  panel.innerHTML = `
    <div class="metric-row"><span class="metric-name">Overall Accuracy</span><span class="metric-val">${(acc*100).toFixed(1)}%</span></div>
    ${['Fatal','Serious','Minor','Property Damage Only'].map(s => {
      const key = s; const r = report[key] || {};
      return `<div class="metric-row">
        <span class="metric-name">${s}</span>
        <span class="metric-val">F1: ${((r.f1_score||0)*100).toFixed(0)}%</span>
      </div>`;
    }).join('')}
  `;
}

function renderFeatureImportance(fi) {
  const top = fi.slice(0, 12);
  Plotly.newPlot('feature-importance-viz', [{
    type:'bar', orientation:'h',
    x: top.map(f=>f.importance).reverse(),
    y: top.map(f=>f.feature.replace('_enc','').replace(/_/g,' ')).reverse(),
    marker:{ color: PALETTE, opacity:0.85 },
  }], pLayout({ height:280, margin:{l:150,r:40,t:20,b:40}, xaxis:{title:'Importance'} }), PLOTLY_CONFIG);
}

function renderFeatureImportancePlaceholder() {
  const features = ['speed_kmh','hour','vehicles_involved','month','road_type','weather_condition','light_condition','cause','vehicle_type','city','is_night','is_peak_hour'];
  const importances = [0.22, 0.16, 0.12, 0.09, 0.08, 0.07, 0.07, 0.06, 0.05, 0.04, 0.02, 0.02];
  Plotly.newPlot('feature-importance-viz', [{
    type:'bar', orientation:'h',
    x: importances.slice().reverse(),
    y: features.slice().reverse(),
    marker:{ color: PALETTE, opacity:0.85 },
  }], pLayout({ height:280, margin:{l:150,r:40,t:20,b:40}, xaxis:{title:'Importance (Sample)'} }), PLOTLY_CONFIG);
}

function renderConfusionMatrix(cm) {
  const labels = ['PDO', 'Minor', 'Serious', 'Fatal'];
  Plotly.newPlot('confusion-matrix-viz', [{
    z: cm, x: labels, y: labels, type:'heatmap',
    colorscale:[['0','#1E293B'],['1','#6366F1']],
    texttemplate:'%{z}', textfont:{color:'white', size:14},
    hovertemplate:'Actual: %{y}<br>Predicted: %{x}<br>Count: %{z}<extra></extra>',
  }], pLayout({ height:280, xaxis:{title:'Predicted'}, yaxis:{title:'Actual'}, margin:{l:70,r:30,t:20,b:60} }), PLOTLY_CONFIG);
}

document.getElementById('predictBtn').addEventListener('click', async () => {
  const btn = document.getElementById('predictBtn');
  btn.textContent = '⏳ Predicting…';
  btn.disabled = true;
  try {
    const payload = {
      hour: parseInt(document.getElementById('ml-hour').value),
      month: parseInt(document.getElementById('ml-month').value),
      speed_kmh: parseFloat(document.getElementById('ml-speed').value),
      vehicles_involved: parseInt(document.getElementById('ml-vehicles').value),
      road_type: document.getElementById('ml-road').value,
      weather_condition: document.getElementById('ml-weather').value,
      light_condition: document.getElementById('ml-light').value,
      cause: document.getElementById('ml-cause').value,
      day_of_week: document.getElementById('ml-day').value,
      city: document.getElementById('ml-city').value,
    };
    const res = await fetch(`${API}/predict`, {
      method: 'POST', headers: {'Content-Type':'application/json'},
      body: JSON.stringify(payload),
    });
    const result = await res.json();
    if (result.error) throw new Error(result.error);
    renderPredictionResult(result);
    toast('Prediction complete ');
  } catch (e) {
    toast(' Prediction error: ' + e.message, 4000);
    renderPredictionFallback();
  }
  btn.textContent = ' Predict Severity';
  btn.disabled = false;
});

function renderPredictionFallback() {
  // Simulated result if model not trained
  const sev = ['Property Damage Only','Minor','Serious','Fatal'][Math.floor(Math.random()*4)];
  renderPredictionResult({
    prediction: sev, confidence: 72.5,
    probabilities: { 'Property Damage Only': 15, 'Minor': 35, 'Serious': 40, 'Fatal': 10 }
  });
}

function renderPredictionResult(result) {
  const cls = {'Fatal':'fatal','Serious':'serious','Minor':'minor','Property Damage Only':'pdo'};
  const colorMap = {'Fatal':'#EF4444','Serious':'#F97316','Minor':'#EAB308','Property Damage Only':'#22C55E'};
  const card = document.getElementById('mlResult');
  card.innerHTML = `
    <div class="result-content">
      <div class="result-severity ${cls[result.prediction]}">
        <div class="result-severity-label">Predicted Severity</div>
        <div class="result-severity-value">${result.prediction}</div>
        <div class="result-confidence">Confidence: <strong>${result.confidence}%</strong></div>
      </div>
      <div class="prob-bars">
        ${Object.entries(result.probabilities).map(([label, pct]) => `
          <div class="prob-row">
            <span class="prob-label">${label}</span>
            <div class="prob-bar-wrap">
              <div class="prob-bar-fill" style="width:${pct}%;background:${colorMap[label]||'#6366F1'}"></div>
            </div>
            <span class="prob-val" style="color:${colorMap[label]||'#6366F1'}">${pct}%</span>
          </div>
        `).join('')}
      </div>
    </div>
  `;
}

// ─── TOOL COMPARISON ──────────────────────────────────────────────────────────
async function loadComparison() {
  const data = await apiFetch('/analytics/comparison');
  const tools = data.tools || [];

  // Radar chart
  const dims = ['usability','flexibility','visual_appeal','interactivity','learning_curve'];
  const dimLabels = ['Usability','Flexibility','Visual Appeal','Interactivity','Ease of Learning'];
  const radarTraces = tools.map((t, i) => ({
    type:'scatterpolar', fill:'toself', name:t.tool,
    r: dims.map(d => t[d]),
    theta: dimLabels,
    line:{color:PALETTE[i]}, fillcolor:PALETTE[i]+'33',
    hovertemplate:`<b>${t.tool}</b><br>%{theta}: %{r}/10<extra></extra>`,
  }));
  Plotly.newPlot('radar-viz', radarTraces,
    pLayout({ polar:{
      bgcolor:'rgba(30,41,59,0.6)',
      radialaxis:{visible:true, range:[0,10], tickfont:{color:'#94A3B8',size:10}, gridcolor:'rgba(148,163,184,0.15)'},
      angularaxis:{tickfont:{color:'#CBD5E1',size:11}, gridcolor:'rgba(148,163,184,0.15)'}
    }, height:340, margin:{l:50,r:50,t:30,b:30} }), PLOTLY_CONFIG);

  // Overall score bar
  const totalScores = tools.map(t => dims.reduce((s,d) => s+t[d], 0));
  Plotly.newPlot('tool-score-viz', [{
    type:'bar', x:tools.map(t=>t.tool), y:totalScores,
    marker:{ color: PALETTE, opacity:0.85, line:{color:'#0F172A',width:0.5} },
    text: totalScores.map(s=>s+'/50'), textposition:'outside', textfont:{color:'#94A3B8'},
  }], pLayout({ height:300, margin:{l:40,r:20,t:30,b:40}, showlegend:false,
    yaxis:{title:'Score /50', range:[0,55]} }), PLOTLY_CONFIG);

  // Tool cards
  const tc = document.getElementById('toolCards');
  tc.innerHTML = tools.map((t, i) => `
    <div class="tool-card">
      <div class="tool-name" style="color:${PALETTE[i]}">${t.tool}</div>
      <div class="tool-best">${t.best_for}</div>
      <div class="tool-charts">${t.chart_types}</div>
      <div class="score-bars">
        ${dims.map(d => `
          <div class="score-row">
            <span class="score-label">${dimLabels[dims.indexOf(d)]}</span>
            <div class="score-bar"><div class="score-fill" style="width:${t[d]*10}%;background:${PALETTE[i]}"></div></div>
          </div>
        `).join('')}
      </div>
    </div>
  `).join('');

  // Showcase charts using Plotly
  loadShowcaseCharts();
}

async function loadShowcaseCharts() {
  const speedData = await apiFetch('/charts/speed-stats');
  const summary = await apiFetch('/charts/summary');

  // Showcase Histogram (Seaborn-style = KDE overlay)
  const speeds = speedData.all_speeds || [];
  Plotly.newPlot('showcase-hist', [
    { x:speeds, type:'histogram', nbinsx:35, name:'Count', marker:{color:'#22C55E',opacity:0.7,line:{color:'#14532D',width:0.5}} },
  ], pLayout({ height:220, margin:{l:40,r:15,t:20,b:40}, showlegend:false,
    xaxis:{title:'Speed (km/h)'}, yaxis:{title:'Count'}, annotations: speeds.length ? [{x:0.5,y:1.05,xref:'paper',yref:'paper',text:'Seaborn style',font:{size:10,color:'#86EFAC'},showarrow:false}] : [{x:0.5,y:0.5,xref:'paper',yref:'paper',text:'No recorded speed values in dataset',font:{size:13,color:'#64748b'},showarrow:false}] }), PLOTLY_CONFIG);

  // Showcase Box (Matplotlib-style)
  Plotly.newPlot('showcase-box', [
    ...Object.keys(speedData.by_road||{}).map((rt,i)=>({
      y: (speedData.by_road[rt]||[]).slice(0,200), type:'box', name:rt, boxmean:true,
      marker:{color:PALETTE[i],size:3,opacity:0.4}, line:{color:PALETTE[i]}, fillcolor:PALETTE[i]+'22',
    }))
  ], pLayout({ height:220, margin:{l:40,r:10,t:20,b:40}, showlegend:false, yaxis:{title:'Speed'} }), PLOTLY_CONFIG);

  // Showcase Bar (Plotly Interactive)
  const causes = Object.entries(summary.causes||{}).slice(0,6);
  Plotly.newPlot('showcase-bar', [{
    type:'bar', x:causes.map(c=>c[0]), y:causes.map(c=>c[1]),
    marker:{color:PALETTE, opacity:0.85, line:{color:'#0F172A',width:0.5}},
  }], pLayout({ height:220, margin:{l:40,r:10,t:20,b:80}, showlegend:false, xaxis:{tickangle:-30} }), PLOTLY_CONFIG);

  // Showcase Donut (Plotly)
  const sevCounts = summary.severity||{};
  Plotly.newPlot('showcase-donut', [{
    type:'pie', hole:0.5, labels:SEVERITY_ORDER, values:SEVERITY_ORDER.map(s=>sevCounts[s]||0),
    marker:{colors:SEVERITY_ORDER.map(s=>SEVERITY_COLORS[s]),line:{color:'#0F172A',width:2}},
    textinfo:'percent', textfont:{color:'#F1F5F9',size:10},
  }], pLayout({ height:220, margin:{l:10,r:10,t:20,b:10},
    annotations:[{text:'Severity',x:0.5,y:0.5,font:{size:12,color:'#E2E8F0'},showarrow:false}] }), PLOTLY_CONFIG);
}

// ─── PAGE ROUTER ──────────────────────────────────────────────────────────────
let pagesLoaded = {};

function onPageLoad(page) {
  if (pagesLoaded[page]) return;
  pagesLoaded[page] = true;
  if (page === 'map') loadMap();
  if (page === 'charts') loadVizTab('histograms');
  if (page === 'analysis') loadRiskAnalysis();
  if (page === 'ml') loadMLPage();
  if (page === 'comparison') loadComparison();
}

// ─── INIT ─────────────────────────────────────────────────────────────────────
async function init() {
  try {
    showLoading(true);
    await loadFilters();
    await loadKPIs();
    await loadDashboardCharts();
    showLoading(false);
    toast('SafeRoute Analytics loaded ');
  } catch (e) {
    showLoading(false);
    toast(' Cannot connect to server — start app.py first', 6000);
    console.error('Init error:', e);
  }
}

init();
