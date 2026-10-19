"""
SafeRoute Analytics - Flask Backend API
"""

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
import pandas as pd
import numpy as np
import json
import os
import traceback
from functools import lru_cache

app = Flask(__name__, static_folder='frontend', static_url_path='')
CORS(app)

DATA_PATH = "data/accidents.csv"
MODELS_PATH = "models"


# ─── Data Loading ─────────────────────────────────────────────────────────────

def load_data():
    if not os.path.exists(DATA_PATH):
        from data_generator import generate_accident_data
        os.makedirs("data", exist_ok=True)
        df = generate_accident_data(3000)
        df.to_csv(DATA_PATH, index=False)
    return pd.read_csv(DATA_PATH)


_df_cache = None

def get_df():
    global _df_cache
    if _df_cache is None:
        _df_cache = load_data()
    return _df_cache


# ─── Root Route ───────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return send_from_directory('frontend', 'index.html')


# ─── KPIs ─────────────────────────────────────────────────────────────────────

@app.route('/api/kpis')
def kpis():
    df = get_df()
    total = len(df)
    fatal_count = len(df[df['severity'] == 'Fatal'])
    serious_count = len(df[df['severity'] == 'Serious'])
    total_fatalities = int(df['fatalities'].sum())
    total_injuries = int(df['injuries'].sum())
    avg_speed = round(float(df['speed_kmh'].mean()), 1)
    hotspot_count = df.groupby(['city']).size().count()

    peak_hour = int(df.groupby('hour').size().idxmax())
    worst_city = df.groupby('city')['fatalities'].sum().idxmax()
    top_cause = df['cause'].value_counts().index[0]

    return jsonify({
        'total_accidents': total,
        'fatal_count': fatal_count,
        'serious_count': serious_count,
        'total_fatalities': total_fatalities,
        'total_injuries': total_injuries,
        'avg_speed': avg_speed,
        'hotspot_cities': int(hotspot_count),
        'peak_hour': peak_hour,
        'worst_city': worst_city,
        'top_cause': top_cause,
        'fatal_pct': round(fatal_count / total * 100, 1),
        'serious_pct': round(serious_count / total * 100, 1),
    })


# ─── Map Data ─────────────────────────────────────────────────────────────────

@app.route('/api/map-data')
def map_data():
    df = get_df()
    severity_filter = request.args.get('severity', 'all')
    city_filter = request.args.get('city', 'all')
    year_filter = request.args.get('year', 'all')

    filtered = df.copy()
    if severity_filter != 'all':
        filtered = filtered[filtered['severity'] == severity_filter]
    if city_filter != 'all':
        filtered = filtered[filtered['city'] == city_filter]
    if year_filter != 'all':
        filtered = filtered[filtered['year'] == int(year_filter)]

    # Sample for performance
    sample = filtered.sample(min(1500, len(filtered)), random_state=42) if len(filtered) > 1500 else filtered

    records = sample[[
        'accident_id', 'latitude', 'longitude', 'severity', 'city',
        'date', 'hour', 'cause', 'road_type', 'speed_kmh',
        'fatalities', 'injuries', 'weather_condition'
    ]].to_dict(orient='records')

    # Hotspot clusters (grid-based)
    filtered['lat_round'] = filtered['latitude'].round(2)
    filtered['lon_round'] = filtered['longitude'].round(2)
    clusters = (filtered.groupby(['lat_round', 'lon_round'])
                .agg(count=('accident_id', 'count'),
                     avg_severity_score=('severity_score', 'mean'),
                     fatal=('fatalities', 'sum'),
                     city=('city', 'first'))
                .reset_index()
                .rename(columns={'lat_round': 'lat', 'lon_round': 'lon'}))
    clusters = clusters[clusters['count'] >= 2].sort_values('count', ascending=False).head(100)

    return jsonify({
        'points': records,
        'clusters': clusters.to_dict(orient='records'),
        'total_filtered': len(filtered)
    })


# ─── Charts ───────────────────────────────────────────────────────────────────

@app.route('/api/charts/summary')
def charts_summary():
    df = get_df()
    return jsonify({
        'severity': df['severity'].value_counts().to_dict(),
        'causes': df['cause'].value_counts().head(10).to_dict(),
        'road_types': df['road_type'].value_counts().to_dict(),
        'weather': df['weather_condition'].value_counts().to_dict(),
        'cities': df['city'].value_counts().to_dict(),
        'light': df['light_condition'].value_counts().to_dict(),
        'vehicles': df['vehicle_type'].value_counts().to_dict(),
        'years': sorted(df['year'].unique().tolist()),
    })


@app.route('/api/charts/temporal')
def charts_temporal():
    df = get_df()
    hourly = df.groupby('hour').size().reset_index(name='count')
    monthly = df.groupby(['year', 'month']).size().reset_index(name='count')
    day_of_week = df.groupby('day_of_week').size().reset_index(name='count')
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    day_of_week['sort'] = day_of_week['day_of_week'].map({d: i for i, d in enumerate(day_order)})
    day_of_week = day_of_week.sort_values('sort')

    return jsonify({
        'hourly': hourly.to_dict(orient='records'),
        'monthly': monthly.to_dict(orient='records'),
        'day_of_week': day_of_week[['day_of_week', 'count']].to_dict(orient='records'),
    })


@app.route('/api/charts/speed-stats')
def charts_speed():
    df = get_df()
    by_severity = {}
    for sev in df['severity'].unique():
        speeds = df[df['severity'] == sev]['speed_kmh'].tolist()
        by_severity[sev] = speeds[:500]  # cap for response size

    by_road = {}
    for rt in df['road_type'].unique():
        speeds = df[df['road_type'] == rt]['speed_kmh'].tolist()
        by_road[rt] = speeds[:500]

    return jsonify({
        'all_speeds': df['speed_kmh'].tolist()[:1000],
        'by_severity': by_severity,
        'by_road': by_road,
        'stats': {
            'mean': round(float(df['speed_kmh'].mean()), 1),
            'median': round(float(df['speed_kmh'].median()), 1),
            'std': round(float(df['speed_kmh'].std()), 1),
            'min': round(float(df['speed_kmh'].min()), 1),
            'max': round(float(df['speed_kmh'].max()), 1),
        }
    })


@app.route('/api/charts/casualties')
def charts_casualties():
    df = get_df()
    return jsonify({
        'total_by_city': df.groupby('city').agg(
            fatalities=('fatalities', 'sum'),
            injuries=('injuries', 'sum'),
            accidents=('accident_id', 'count')
        ).reset_index().to_dict(orient='records'),
        'by_cause': df.groupby('cause').agg(
            fatalities=('fatalities', 'sum'),
            injuries=('injuries', 'sum'),
            accidents=('accident_id', 'count')
        ).reset_index().sort_values('fatalities', ascending=False).to_dict(orient='records'),
        'by_road': df.groupby('road_type').agg(
            fatalities=('fatalities', 'sum'),
            injuries=('injuries', 'sum'),
            accidents=('accident_id', 'count')
        ).reset_index().to_dict(orient='records'),
        'monthly_trend': df.groupby(['year', 'month']).agg(
            fatalities=('fatalities', 'sum'),
            injuries=('injuries', 'sum'),
            accidents=('accident_id', 'count')
        ).reset_index().to_dict(orient='records'),
        'severity_counts': df['severity'].value_counts().to_dict(),
    })


@app.route('/api/charts/heatmap')
def charts_heatmap():
    df = get_df()
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    pivot = df.pivot_table(index='day_of_week', columns='hour', values='accident_id',
                           aggfunc='count', fill_value=0)
    pivot = pivot.reindex([d for d in day_order if d in pivot.index])

    result = []
    for day in pivot.index:
        for hr in pivot.columns:
            result.append({'day': day, 'hour': int(hr), 'count': int(pivot.loc[day, hr])})

    return jsonify({'heatmap': result, 'days': day_order, 'hours': list(range(24))})


# ─── ML Prediction ────────────────────────────────────────────────────────────

@app.route('/api/predict', methods=['POST'])
def predict():
    try:
        import joblib
        data = request.get_json()

        model = joblib.load(f"{MODELS_PATH}/rf_model.pkl")
        scaler = joblib.load(f"{MODELS_PATH}/scaler.pkl")
        encoders = joblib.load(f"{MODELS_PATH}/encoders.pkl")

        with open(f"{MODELS_PATH}/features.json") as f:
            features = json.load(f)

        hour = int(data.get('hour', 12))
        month = int(data.get('month', 6))
        speed = float(data.get('speed_kmh', 60))
        vehicles = int(data.get('vehicles_involved', 2))

        row = {
            'hour': hour, 'month': month,
            'is_peak_hour': 1 if (7 <= hour <= 9) or (17 <= hour <= 20) else 0,
            'is_night': 1 if hour < 6 or hour >= 21 else 0,
            'is_weekend': 1 if data.get('day_of_week') in ['Saturday', 'Sunday'] else 0,
            'bad_weather': 1 if data.get('weather_condition') in ['Fog', 'Rain', 'Storm', 'Haze'] else 0,
            'poor_visibility': 1 if data.get('light_condition') in ['Dark (Unlit)', 'Dusk/Dawn'] else 0,
            'speed_kmh': speed,
            'vehicles_involved': vehicles,
        }

        cat_cols = ['road_type', 'weather_condition', 'light_condition',
                    'accident_type', 'cause', 'vehicle_type', 'city', 'state']
        for col in cat_cols:
            val = data.get(col, '')
            enc = encoders.get(col)
            if enc and val in enc.classes_:
                row[col + '_enc'] = int(enc.transform([val])[0])
            else:
                row[col + '_enc'] = 0

        X = pd.DataFrame([row])[features]
        X_sc = scaler.transform(X)
        pred = int(model.predict(X_sc)[0])
        proba = model.predict_proba(X_sc)[0].tolist()

        labels = ['Property Damage Only', 'Minor', 'Serious', 'Fatal']
        return jsonify({
            'prediction': labels[pred],
            'confidence': round(max(proba) * 100, 1),
            'probabilities': {labels[i]: round(p * 100, 1) for i, p in enumerate(proba)}
        })

    except Exception as e:
        return jsonify({'error': str(e), 'trace': traceback.format_exc()}), 500


@app.route('/api/ml-metrics')
def ml_metrics():
    metrics_file = f"{MODELS_PATH}/metrics.json"
    if os.path.exists(metrics_file):
        with open(metrics_file) as f:
            return jsonify(json.load(f))
    return jsonify({'error': 'Model not trained yet. Run ml_model.py first.'}), 404


# ─── Filters ──────────────────────────────────────────────────────────────────

@app.route('/api/filters')
def filters():
    df = get_df()
    return jsonify({
        'cities': sorted(df['city'].unique().tolist()),
        'years': sorted(df['year'].unique().tolist()),
        'severities': ['Property Damage Only', 'Minor', 'Serious', 'Fatal'],
        'road_types': sorted(df['road_type'].unique().tolist()),
        'weather': sorted(df['weather_condition'].unique().tolist()),
        'causes': sorted(df['cause'].unique().tolist()),
        'vehicle_types': sorted(df['vehicle_type'].unique().tolist()),
        'light_conditions': sorted(df['light_condition'].unique().tolist()),
        'states': sorted(df['state'].unique().tolist()),
        'days': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'],
    })


# ─── Analytics ────────────────────────────────────────────────────────────────

@app.route('/api/analytics/hotspots')
def hotspots():
    df = get_df()
    city_stats = df.groupby('city').agg(
        total=('accident_id', 'count'),
        fatalities=('fatalities', 'sum'),
        injuries=('injuries', 'sum'),
        avg_speed=('speed_kmh', 'mean'),
        fatal_count=('severity', lambda x: (x == 'Fatal').sum()),
    ).reset_index()
    city_stats['risk_score'] = (
        city_stats['fatalities'] * 10 +
        city_stats['injuries'] * 2 +
        city_stats['total'] * 0.5
    ).round(1)
    city_stats = city_stats.sort_values('risk_score', ascending=False)
    city_stats['avg_speed'] = city_stats['avg_speed'].round(1)
    return jsonify(city_stats.to_dict(orient='records'))


@app.route('/api/analytics/risk-periods')
def risk_periods():
    df = get_df()
    # By hour
    hourly = df.groupby('hour').agg(
        accidents=('accident_id', 'count'),
        fatalities=('fatalities', 'sum'),
        avg_severity_score=('severity_score', 'mean')
    ).reset_index()

    # By month
    monthly = df.groupby('month_name').agg(
        accidents=('accident_id', 'count'),
        fatalities=('fatalities', 'sum')
    ).reset_index()

    month_order = ['January', 'February', 'March', 'April', 'May', 'June',
                   'July', 'August', 'September', 'October', 'November', 'December']
    monthly['sort'] = monthly['month_name'].map({m: i for i, m in enumerate(month_order)})
    monthly = monthly.sort_values('sort')

    return jsonify({
        'hourly': hourly.to_dict(orient='records'),
        'monthly': monthly[['month_name', 'accidents', 'fatalities']].to_dict(orient='records'),
    })


@app.route('/api/analytics/comparison')
def tool_comparison():
    """Comparison data for visualization tools."""
    return jsonify({
        'tools': [
            {
                'tool': 'Seaborn',
                'usability': 9, 'flexibility': 7, 'visual_appeal': 8,
                'interactivity': 2, 'learning_curve': 8,
                'best_for': 'Statistical plots, quick analysis',
                'chart_types': 'Histogram, Box, Violin, Heatmap, Pair plots'
            },
            {
                'tool': 'Matplotlib',
                'usability': 7, 'flexibility': 10, 'visual_appeal': 6,
                'interactivity': 2, 'learning_curve': 6,
                'best_for': 'Full control, publication-ready figures',
                'chart_types': 'All types: bar, pie, scatter, histogram'
            },
            {
                'tool': 'Plotly',
                'usability': 9, 'flexibility': 9, 'visual_appeal': 10,
                'interactivity': 10, 'learning_curve': 8,
                'best_for': 'Interactive dashboards, web apps',
                'chart_types': 'All types + 3D, animated, geo maps'
            },
            {
                'tool': 'Excel',
                'usability': 10, 'flexibility': 5, 'visual_appeal': 7,
                'interactivity': 4, 'learning_curve': 10,
                'best_for': 'Non-technical users, quick reports',
                'chart_types': 'Bar, pie, line, scatter (limited)'
            },
        ]
    })


if __name__ == '__main__':
    print("Starting SafeRoute Analytics server...")
    print("Ensuring data is available...")
    df = get_df()
    print(f"Loaded {len(df)} accident records.")
    app.run(debug=True, port=5050, host='0.0.0.0')
