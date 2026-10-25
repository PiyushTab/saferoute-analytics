"""
SafeRoute Analytics - Flask backend.

Serves the single-page dashboard from ./frontend and a small JSON API.
Every data endpoint accepts the optional filters ?city=, ?year=, ?severity=.
"""

import json
import os
import threading
from functools import lru_cache

import numpy as np
import pandas as pd
from flask import Flask, Response, abort, jsonify as flask_jsonify, request, send_from_directory
from flask_cors import CORS

import visualizations

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "data", "accidents.csv")
MODELS_PATH = os.path.join(BASE_DIR, "models")

app = Flask(__name__, static_folder=os.path.join(BASE_DIR, "frontend"), static_url_path="")
CORS(app)

DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MONTH_ORDER = ["January", "February", "March", "April", "May", "June", "July",
               "August", "September", "October", "November", "December"]
SEVERITY_ORDER = ["Property Damage Only", "Minor", "Serious", "Fatal"]
REQUIRED_COLUMNS = {
    "accident_id", "date", "year", "month", "month_name", "day_of_week", "hour",
    "latitude", "longitude", "city", "state", "road_type", "weather_condition",
    "light_condition", "cause", "vehicle_type", "speed_kmh", "fatalities", "injuries",
    "vehicles_involved", "severity", "severity_score",
}


# ─── JSON helpers ─────────────────────────────────────────────────────────────

def _json_safe(value):
    """Convert NumPy/Pandas scalars and NaN/inf into strict-JSON values."""
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return float(value) if np.isfinite(value) else None
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if value is None or value is pd.NA or value is pd.NaT:
        return None
    return value


def jsonify(value, status=200):
    response = flask_jsonify(_json_safe(value))
    response.status_code = status
    return response


def records(frame):
    return frame.to_dict(orient="records")


# ─── Data ─────────────────────────────────────────────────────────────────────

_df = None
_df_lock = threading.Lock()


def load_data():
    if not os.path.exists(DATA_PATH):
        from data_loader_india import prepare_indian_dataset
        prepare_indian_dataset()
    df = pd.read_csv(DATA_PATH)
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError("data/accidents.csv is missing columns: " + ", ".join(sorted(missing)))
    if df.empty:
        raise ValueError("data/accidents.csv is empty.")
    return df


def get_df():
    global _df
    if _df is None:
        with _df_lock:
            if _df is None:
                _df = load_data()
    return _df


def filter_args():
    """Read ?city=&year=&severity= as a hashable tuple (so results can be cached)."""
    return (
        request.args.get("city", "all"),
        request.args.get("year", "all"),
        request.args.get("severity", "all"),
    )


def apply_filters(df, city="all", year="all", severity="all"):
    if city != "all":
        df = df[df["city"] == city]
    if year != "all":
        try:
            df = df[df["year"] == int(year)]
        except ValueError:
            df = df.iloc[0:0]
    if severity != "all":
        df = df[df["severity"] == severity]
    return df


def current_df():
    return apply_filters(get_df(), *filter_args())


def ordered(series, order):
    """Counts of `series` as a list of {label, count} following a fixed order."""
    counts = series.value_counts()
    return [{"label": k, "count": int(counts.get(k, 0))} for k in order]


# ─── Pages ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


API_VERSION = 2


@app.route("/api/health")
def health():
    df = get_df()
    return jsonify({
        "status": "ok",
        "api_version": API_VERSION,
        "records": len(df),
        "fatalities": int(df["fatalities"].sum()),
        "injuries": int(df["injuries"].sum()),
    })


# ─── Filters and KPIs ─────────────────────────────────────────────────────────

@app.route("/api/filters")
def filters():
    df = get_df()
    return jsonify({
        "cities": sorted(df["city"].dropna().unique().tolist(), key=str.casefold),
        "years": sorted(int(y) for y in df["year"].unique()),
        "severities": [s for s in reversed(SEVERITY_ORDER) if s in set(df["severity"])],
        "road_types": sorted(df["road_type"].unique().tolist()),
        "weather": sorted(df["weather_condition"].unique().tolist()),
        "light_conditions": sorted(df["light_condition"].unique().tolist()),
        "causes": sorted(df["cause"].unique().tolist()),
        "vehicle_types": sorted(df["vehicle_type"].unique().tolist()),
        "total_records": len(df),
    })


@app.route("/api/kpis")
def kpis():
    df = current_df()
    total = len(df)
    if total == 0:
        return jsonify({"total_accidents": 0, "empty": True})
    fatal = int((df["severity"] == "Fatal").sum())
    return jsonify({
        "total_accidents": total,
        "fatal_count": fatal,
        "fatal_pct": round(fatal / total * 100, 1),
        "total_fatalities": int(df["fatalities"].sum()),
        "total_injuries": int(df["injuries"].sum()),
        "cities": int(df["city"].nunique()),
        "peak_hour": int(df.groupby("hour").size().idxmax()),
        "top_city": df.groupby("city")["fatalities"].sum().idxmax(),
        "top_cause": df["cause"].value_counts().index[0],
    })


# ─── Map ──────────────────────────────────────────────────────────────────────

@app.route("/api/map-data")
def map_data():
    df = current_df()
    sample = df.sample(min(2000, len(df)), random_state=42) if len(df) > 2000 else df
    points = sample[[
        "accident_id", "latitude", "longitude", "severity", "city", "date", "hour",
        "cause", "road_type", "weather_condition", "fatalities", "injuries",
    ]]

    grid = df.assign(lat=df["latitude"].round(1), lon=df["longitude"].round(1))
    clusters = (grid.groupby(["lat", "lon"])
                .agg(count=("accident_id", "count"),
                     fatalities=("fatalities", "sum"),
                     injuries=("injuries", "sum"),
                     risk=("severity_score", "mean"),
                     city=("city", lambda s: s.mode().iat[0]))
                .reset_index())
    clusters = clusters[clusters["count"] >= 3].sort_values("count", ascending=False).head(80)

    return jsonify({
        "points": records(points),
        "clusters": records(clusters),
        "total": len(df),
    })


@app.route("/api/analytics/hotspots")
def hotspots():
    df = current_df()
    if df.empty:
        return jsonify([])
    stats = df.groupby("city").agg(
        total=("accident_id", "count"),
        fatalities=("fatalities", "sum"),
        injuries=("injuries", "sum"),
    ).reset_index()
    stats["risk_score"] = (stats["fatalities"] * 10 + stats["injuries"] * 2 + stats["total"] * 0.5).round(0)
    return jsonify(records(stats.sort_values("risk_score", ascending=False).head(10)))


# ─── Charts ───────────────────────────────────────────────────────────────────

@app.route("/api/charts/summary")
def charts_summary():
    df = current_df()
    return jsonify({
        "severity": ordered(df["severity"], SEVERITY_ORDER),
        "weather": records(df["weather_condition"].value_counts().rename_axis("label").reset_index(name="count")),
        "road_types": records(df["road_type"].value_counts().rename_axis("label").reset_index(name="count")),
        "vehicles": records(df["vehicle_type"].value_counts().rename_axis("label").reset_index(name="count")),
        "causes": records(df["cause"].value_counts().rename_axis("label").reset_index(name="count")),
    })


@app.route("/api/charts/temporal")
def charts_temporal():
    df = current_df()
    hourly = df.groupby("hour").agg(accidents=("accident_id", "count"),
                                    fatalities=("fatalities", "sum")).reindex(range(24), fill_value=0)
    yearly = df.groupby("year").agg(accidents=("accident_id", "count"),
                                    fatalities=("fatalities", "sum")).reset_index()
    monthly = (df.groupby("month_name").agg(accidents=("accident_id", "count"),
                                            fatalities=("fatalities", "sum"))
               .reindex(MONTH_ORDER, fill_value=0))
    dow = (df.groupby("day_of_week").agg(accidents=("accident_id", "count"),
                                         fatalities=("fatalities", "sum"))
           .reindex(DAY_ORDER, fill_value=0))
    return jsonify({
        "hourly": [{"hour": int(h), **row} for h, row in zip(hourly.index, records(hourly))],
        "yearly": records(yearly),
        "monthly": [{"month": m, **row} for m, row in zip(monthly.index, records(monthly))],
        "day_of_week": [{"day": d, **row} for d, row in zip(dow.index, records(dow))],
    })


@app.route("/api/charts/city-severity")
def charts_city_severity():
    """Top cities by accident count, split by severity (real counts)."""
    df = current_df()
    top = df["city"].value_counts().head(10).index.tolist()
    table = (df[df["city"].isin(top)].groupby(["city", "severity"]).size()
             .unstack(fill_value=0).reindex(index=top, columns=SEVERITY_ORDER, fill_value=0))
    return jsonify({
        "cities": top,
        "series": {s: table[s].astype(int).tolist() for s in SEVERITY_ORDER},
    })


@app.route("/api/charts/casualties")
def charts_casualties():
    df = current_df()

    def group(col):
        out = df.groupby(col).agg(fatalities=("fatalities", "sum"), injuries=("injuries", "sum"),
                                  accidents=("accident_id", "count")).reset_index()
        out["fatality_rate"] = (out["fatalities"] / out["accidents"]).round(3)
        return records(out.sort_values("fatalities", ascending=False))

    return jsonify({"by_cause": group("cause"), "by_road": group("road_type")})


@app.route("/api/charts/scatter")
def charts_scatter():
    """A reproducible sample of speed vs injuries for the scatter plot."""
    df = current_df()
    sample = df.sample(min(1200, len(df)), random_state=7) if len(df) else df
    return jsonify(records(sample[["speed_kmh", "injuries", "severity", "city", "road_type"]]))


@app.route("/api/analytics/heatmap")
def heatmap_data():
    df = current_df()
    pivot = (df.pivot_table(index="day_of_week", columns="hour", values="accident_id",
                            aggfunc="count", fill_value=0)
             .reindex(index=DAY_ORDER, columns=range(24), fill_value=0))
    return jsonify({"days": DAY_ORDER, "hours": list(range(24)), "z": pivot.values.tolist()})


# ─── Static Matplotlib / Seaborn images ───────────────────────────────────────

@lru_cache(maxsize=256)
def _render_chart(name, city, year, severity):
    df = apply_filters(get_df(), city, year, severity)
    return visualizations.CHARTS[name](df)


@app.route("/api/viz/<name>.png")
def viz_png(name):
    if name not in visualizations.CHARTS:
        abort(404)
    try:
        png = _render_chart(name, *filter_args())
    except Exception as exc:  # report instead of returning a broken image silently
        app.logger.exception("Chart %s failed", name)
        return jsonify({"error": str(exc)}), 500
    return Response(png, mimetype="image/png", headers={"Cache-Control": "no-cache"})


# ─── Machine learning ─────────────────────────────────────────────────────────

_model_bundle = None
_model_lock = threading.Lock()


def _check_model_version():
    """A pickle is only trusted if it was written by the installed scikit-learn."""
    import sklearn
    path = os.path.join(MODELS_PATH, "metrics.json")
    with open(path, encoding="utf-8") as f:
        saved = json.load(f).get("sklearn_version")
    if saved != sklearn.__version__:
        raise RuntimeError(f"model trained with scikit-learn {saved}, installed {sklearn.__version__}")


def get_model():
    """Load the trained model; retrain automatically if the pickle is missing or
    was written by a different scikit-learn version."""
    global _model_bundle
    if _model_bundle is not None:
        return _model_bundle
    with _model_lock:
        if _model_bundle is not None:
            return _model_bundle
        import joblib
        model_path = os.path.join(MODELS_PATH, "rf_model.pkl")
        features_path = os.path.join(MODELS_PATH, "features.json")
        try:
            _check_model_version()
            model = joblib.load(model_path)
            with open(features_path, encoding="utf-8") as f:
                features = json.load(f)
        except Exception as exc:
            app.logger.warning("Saved model unusable (%s); retraining.", exc)
            import ml_model
            model, features = ml_model.train_and_save()
        _model_bundle = (model, features)
    return _model_bundle


@app.route("/api/predict", methods=["POST"])
def predict():
    try:
        data = request.get_json(silent=True) or {}
        model, features = get_model()
        row = {
            "hour": int(data.get("hour", 12)),
            "month": int(data.get("month", 6)),
            "speed_kmh": float(data.get("speed_kmh", 55)),
            "vehicles_involved": int(data.get("vehicles_involved", 2)),
            "road_type": data.get("road_type"),
            "weather_condition": data.get("weather_condition"),
            "light_condition": data.get("light_condition"),
            "cause": data.get("cause"),
            "vehicle_type": data.get("vehicle_type"),
            "city": data.get("city"),
        }
        X = pd.DataFrame([{f: row.get(f) for f in features}])
        probs = model.predict_proba(X)[0]
        labels = [str(c) for c in model.classes_]
        best = int(np.argmax(probs))
        return jsonify({
            "prediction": labels[best],
            "confidence": round(float(probs[best]) * 100, 1),
            "probabilities": {l: round(float(p) * 100, 1) for l, p in zip(labels, probs)},
        })
    except (TypeError, ValueError) as exc:
        return jsonify({"error": f"Invalid input: {exc}"}), 400
    except Exception as exc:
        app.logger.exception("Prediction failed")
        return jsonify({"error": str(exc)}), 500


@app.route("/api/ml-metrics")
def ml_metrics():
    path = os.path.join(MODELS_PATH, "metrics.json")
    if not os.path.exists(path):
        return jsonify({"error": "Model not trained yet. Run: python ml_model.py"}), 404
    with open(path, encoding="utf-8") as f:
        return jsonify(json.load(f))


# ─── Visualisation tool comparison (static reference data) ────────────────────

TOOLS = [
    {"tool": "Seaborn", "usability": 9, "flexibility": 7, "visual_appeal": 8, "interactivity": 2,
     "best_for": "Statistical plots and quick exploratory analysis"},
    {"tool": "Matplotlib", "usability": 7, "flexibility": 10, "visual_appeal": 6, "interactivity": 2,
     "best_for": "Full control and publication-ready figures"},
    {"tool": "Plotly", "usability": 9, "flexibility": 9, "visual_appeal": 10, "interactivity": 10,
     "best_for": "Interactive dashboards and web apps"},
    {"tool": "Excel", "usability": 10, "flexibility": 5, "visual_appeal": 7, "interactivity": 4,
     "best_for": "Non-technical users and quick reports"},
]


@app.route("/api/analytics/comparison")
def tool_comparison():
    return jsonify({"tools": TOOLS})


if __name__ == "__main__":
    print(f"Loaded {len(get_df()):,} accident records.")
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "5050"))
    app.run(host=host, port=port, debug=os.environ.get("FLASK_DEBUG") == "1")
