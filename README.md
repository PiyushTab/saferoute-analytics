# 🛡️ SafeRoute Analytics
### Road Accident Hotspot Detection

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-3.0-black?logo=flask)](https://flask.palletsprojects.com)
[![scikit-learn](https://img.shields.io/badge/scikit--learn-1.5-orange?logo=scikit-learn)](https://scikit-learn.org)
[![Plotly](https://img.shields.io/badge/Plotly-Interactive-blueviolet?logo=plotly)](https://plotly.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

> A full-stack data analytics platform that analyzes historical road accident data to identify dangerous hotspots, high-risk time periods, and classify accident severity using Machine Learning.

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🗺️ **Hotspot Map** | Interactive Leaflet map with heatmap, cluster, and point layers |
| 📊 **Dashboards** | 8 KPI cards + trend charts + severity breakdown |
| 📈 **Visualizations** | Histograms, Box plots, Bar charts, Pie & Donut charts |
| 🤖 **ML Predictor** | Random Forest classifier — predicts accident severity in real-time |
| 🔍 **Risk Analysis** | Peak hours, seasonal patterns, road-type risk analysis |
| ⚖️ **Tool Comparison** | Seaborn vs Matplotlib vs Plotly vs Excel — radar chart + scoring |

---

## 🖥️ Dashboard Preview

**Pages:**
1. **Dashboard** — KPIs, monthly trends, severity distribution
2. **Hotspot Map** — Filterable Leaflet heatmap across Indian cities
3. **Visualizations** — 5 chart tabs using Seaborn, Matplotlib & Plotly
4. **Risk Analysis** — Temporal and causal risk breakdown
5. **ML Predictor** — Real-time severity prediction with confidence scores
6. **Tool Comparison** — Visual analytics tool benchmark

---

## 📊 Visualization Tools Used

| Tool | Chart Types | Use Case |
|------|------------|----------|
| **Seaborn** | Histogram, Box plot, Heatmap | Statistical EDA |
| **Matplotlib** | Pie, Donut, Bar, Histogram | Publication-ready static charts |
| **Plotly** | All interactive types + Radar | Web dashboard, hover tooltips |
| **Chart.js** | Bar charts | Lightweight frontend rendering |
| **Leaflet.js** | Heatmap, markers, clusters | Geospatial hotspot mapping |

---

## 🤖 Machine Learning

- **Model**: Random Forest Classifier (150 estimators)
- **Features**: Speed, Hour, Road Type, Weather, Light Condition, City, Cause, Vehicle Count, and more (17 features)
- **Target Classes**: `Property Damage Only` · `Minor` · `Serious` · `Fatal`
- **Technique**: Label encoding + StandardScaler + stratified train/test split

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Git

### Setup (Windows)
```bat
git clone https://github.com/Shubhveer/saferoute-analytics.git
cd saferoute-analytics
setup.bat
```

### Start Server
```bat
start.bat
```
Opens at **http://localhost:5050** 🎉

### Manual Setup
```bash
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
python data_generator.py       # Generate 3,000 accident records
python ml_model.py             # Train the Random Forest model
python app.py                  # Start Flask server
```

---

## 📁 Project Structure

```
saferoute-analytics/
├── app.py                  ← Flask backend (13 API endpoints)
├── data_generator.py       ← Synthetic accident dataset (3,000 records)
├── ml_model.py             ← ML training pipeline
├── visualizations.py       ← Seaborn/Matplotlib chart engine
├── requirements.txt
├── setup.bat / start.bat   ← Windows convenience scripts
├── data/                   ← Generated CSV/Excel dataset
├── models/                 ← Trained model + encoders
└── frontend/
    ├── index.html          ← 6-page SPA
    ├── style.css           ← Dark theme
    └── app.js              ← Charts, map, ML UI
```

---

## 🌐 API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/kpis` | Dashboard KPIs |
| `GET /api/map-data` | Accident points & clusters |
| `GET /api/charts/summary` | Category distributions |
| `GET /api/charts/speed-stats` | Speed data by severity/road |
| `GET /api/charts/casualties` | Fatality/injury breakdown |
| `POST /api/predict` | ML severity prediction |
| `GET /api/ml-metrics` | Model accuracy & F1 scores |
| `GET /api/analytics/hotspots` | City risk rankings |
| `GET /api/analytics/comparison` | Tool comparison data |

---

## 🛠️ Tech Stack

`Flask` · `Pandas` · `NumPy` · `scikit-learn` · `Seaborn` · `Matplotlib` · `Plotly` · `Leaflet.js` · `Chart.js` · `Inter Font`

---

## 📌 Dataset

- **3,000 synthetic accident records** across 9 major Indian cities
- **Columns**: accident_id, date, time, lat/lon, city, state, road_type, weather, light, cause, vehicle_type, speed_kmh, fatalities, injuries, severity
- **Time range**: 2020–2024
- Realistic distributions for peak hours, weather, and severity

---

## 📄 License

MIT License — free to use, modify, and distribute.

---

*Built with ❤️ using Python · Flask · scikit-learn · Plotly · Leaflet.js*
