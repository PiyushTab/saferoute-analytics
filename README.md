# SafeRoute Analytics — Indian Road Accidents Dataset Edition

A Flask data analytics and machine learning platform for exploring real Indian road accidents, geospatial hotspot clusters, temporal patterns, and severity classification.

---

## Dataset Information

- **Records**: 9,106 accident incident records
- **Geographic Coverage**: 88 Indian cities across 35 States & Union Territories (Delhi, Mumbai, Bengaluru, Chennai, Hyderabad, Kolkata, Patna, Bhopal, Chandigarh, Jaipur, Lucknow, Ahmedabad, Pune, and more)
- **Time Period**: 2010–2024
- **Source**: Ministry of Road Transport and Highways (MoRTH) & City Traffic Police accident reports
- **Key Columns**:
  - `accident_id`: Unique identifier
  - `date`, `year`, `month`, `month_name`, `day_of_week`, `hour`: Temporal parameters
  - `city`, `state`, `latitude`, `longitude`: Geospatial location with verified Indian coordinates
  - `road_type`: Urban Road, National Highway, State Highway, Expressway, Rural Road
  - `weather_condition`: Clear, Rainy, Foggy, Cloudy, Stormy
  - `light_condition`: Daylight, Night - Street Lights, Night - No Street Lights
  - `cause`: Over Speeding, Drunk Driving, Distracted Driving, Brake Failure, Weather
  - `vehicle_type`: Car, Bike, Truck, Auto Rickshaw, Bus, Tractor, Bicycle
  - `speed_kmh`: Speed records mapped to road category
  - `fatalities`, `injuries`, `casualty_count`: Recorded casualty numbers
  - `severity`: Fatal, Serious, Minor, Property Damage Only

---

## User Interface & Design

- **Theme**: Clean, bright, light natural design
- **Colors**: Sage green (`#39785B`), olive, warm terracotta (`#C96D4B`), sand yellow (`#D49A42`), and teal slate
- **Clean Aesthetics**: Minimalist icons and clear typography with no excessive emojis
- **Map**: Centered over India (`[22.5, 78.9]`), featuring Heatmap, Clusters, and Point Markers with interactive tooltips

---

## Quick Start (VS Code / Windows)

1. Open the project folder in **VS Code**.
2. Open terminal (`Ctrl + \``) and run:

```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
python data_loader_india.py   # Prepares the real Indian dataset (9,106 records)
python ml_model.py            # Trains the Random Forest severity model
python app.py                 # Launches the Flask server
```

3. Open your browser at **http://localhost:5050**.

---

## Machine Learning Model

- **Algorithm**: Random Forest Classifier (`n_estimators=150`, balanced class weighting)
- **Features Used**: Hour, Month, Speed (km/h), Vehicles Involved, Road Type, Weather, Lighting Condition, Accident Cause, Vehicle Type, City
- **Target**: Severity Classification (`Fatal`, `Serious`, `Minor`, `Property Damage Only`)
- **Evaluation**: 80/20 train/test split with Accuracy, Macro-F1, and Confusion Matrix stored in `models/metrics.json`

---

## Project Structure

```
saferoute-analytics/
├── app.py                  # Flask backend API (13 endpoints)
├── data_loader_india.py    # Real Indian dataset processor
├── ml_model.py             # Random Forest pipeline & metrics
├── visualizations.py       # Seaborn, Matplotlib, and Plotly engine
├── requirements.txt        # Dependencies
├── data/
│   ├── accidents.csv       # Processed real Indian dataset (9,106 records)
│   └── accidents.xlsx      # Excel export
├── models/
│   ├── rf_model.pkl        # Trained model
│   ├── features.json       # Feature configuration
│   └── metrics.json        # Accuracy and confusion matrix
└── frontend/
    ├── index.html          # Clean dashboard SPA (6 pages)
    ├── style.css           # Bright natural theme stylesheet
    └── app.js              # Plotly, Leaflet map, Chart.js logic
```


## Jupyter Notebook: API-key-free maps

Open `SafeRoute_Maps_No_API_Key.ipynb` in Jupyter Notebook or JupyterLab from the project root. It creates and displays the accident heatmap, marker clusters, and individual accident points using Folium and OpenStreetMap tiles; no map API key is required. An internet connection is needed for the basemap tiles. Install dependencies with `pip install pandas folium`.


### Hotspot map canvas fix

The Heatmap view now uses Leaflet vector density circles instead of the `leaflet.heat` canvas plugin. This avoids the `getImageData` / `source height is 0` exception when the dashboard map is first shown or resized. Heatmap, Clusters, and Points require no map API key. OpenStreetMap/CARTO tiles still require an internet connection.
