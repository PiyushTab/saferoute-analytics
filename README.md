# SafeRoute Analytics

A Flask dashboard for exploring Indian road accident records: hotspot maps, statistical charts, risk analysis and a Random Forest severity predictor.

## Quick start

```bash
python -m venv venv
# Windows: venv\Scripts\activate      macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
python ml_model.py      # optional: the app retrains automatically if the model is missing
python app.py
```

Open http://localhost:5050. On Windows you can run `setup.bat` once, then `start.bat`.
Set `PORT`, `HOST` or `FLASK_DEBUG=1` as environment variables if needed (default host is 127.0.0.1).

## Pages

| Page | Contents |
|---|---|
| Dashboard | KPIs, yearly trend, severity split, top cities, accidents by hour |
| Hotspot Map | Heatmap, clusters and points on a map of India, plus a risk-ranked city table |
| Charts | Seaborn and Matplotlib images drawn by the backend, plus interactive Plotly charts |
| Risk Analysis | Hour, weekday and month patterns; fatalities per accident by road type and cause |
| Predictor | Severity prediction, model metrics, feature importance, confusion matrix |
| Tools | Comparison of Seaborn, Matplotlib, Plotly and Excel |

City, year and severity filters apply to every data page. The map needs internet access for basemap tiles; all JavaScript libraries are bundled in `frontend/vendor`.

## API

All data endpoints accept `?city=&year=&severity=`.

`/api/filters` `/api/kpis` `/api/map-data` `/api/analytics/hotspots` `/api/analytics/heatmap` `/api/analytics/comparison`
`/api/charts/summary` `/api/charts/temporal` `/api/charts/city-severity` `/api/charts/casualties` `/api/charts/scatter`
`/api/viz/<name>.png` (speed_hist, injuries_hist, box_severity, box_road, cause_bar, severity_pie, heatmap)
`POST /api/predict` `/api/ml-metrics` `/api/health`

## Data notes

`data/accidents.csv` is built by `data_loader_india.py` from a public Indian road accident dataset (9,106 records, 88 cities, 2010-2024). Some fields are generated rather than measured:

- `hour` is inferred from the lighting condition
- `speed_kmh` is sampled from a distribution per road type
- `vehicles_involved` is random
- coordinates are city centres with a small random spread

Charts based on these fields show modelled values.

## Model

Random Forest (150 trees, balanced class weights) on hour, month, speed, vehicles, road, weather, lighting, cause, vehicle type and city, with an 80/20 split.
Results (in `models/metrics.json`): accuracy 75.7%, balanced accuracy 25.7%, macro-F1 0.23. About 76% of records are "Fatal", so accuracy is close to an always-"Fatal" baseline (76.2%), and balanced accuracy is chance level for four classes. These inputs do not separate severities well; treat predictions as illustrative.

## Structure

```
app.py                 Flask API and static hosting
data_loader_india.py   Builds data/accidents.csv
ml_model.py            Trains and saves the model and metrics
visualizations.py      Matplotlib / Seaborn chart renderer
frontend/              index.html, style.css, app.js, vendor/ (Plotly, Leaflet)
SafeRoute_Maps_No_API_Key.ipynb   Folium maps notebook
```
