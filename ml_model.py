"""
SafeRoute Analytics - severity classifier.

Trains a Random Forest on the accident records and writes
models/rf_model.pkl, models/features.json and models/metrics.json.

Run:  python ml_model.py
"""

import json
import os

import joblib
import pandas as pd
import sklearn
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.metrics import (accuracy_score, balanced_accuracy_score, classification_report,
                             confusion_matrix, f1_score)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "data", "accidents.csv")
MODEL_DIR = os.path.join(BASE_DIR, "models")

NUMERIC = ["hour", "month", "speed_kmh", "vehicles_involved"]
CATEGORICAL = ["road_type", "weather_condition", "light_condition", "cause", "vehicle_type", "city"]
FEATURES = NUMERIC + CATEGORICAL


def prepare_data(filepath=DATA_PATH):
    if not os.path.exists(filepath):
        from data_loader_india import prepare_indian_dataset
        prepare_indian_dataset()
    df = pd.read_csv(filepath)
    missing = [c for c in FEATURES + ["severity"] if c not in df.columns]
    if missing:
        raise ValueError("Dataset is missing required columns: " + ", ".join(missing))
    df = df.dropna(subset=["severity"]).copy()
    df["severity"] = df["severity"].astype(str)
    return df, FEATURES


def build_pipeline():
    preprocessor = ColumnTransformer([
        ("num", SimpleImputer(strategy="median"), NUMERIC),
        ("cat", Pipeline([("imputer", SimpleImputer(strategy="most_frequent")),
                          ("onehot", OneHotEncoder(handle_unknown="ignore"))]), CATEGORICAL),
    ])
    classifier = RandomForestClassifier(n_estimators=150, min_samples_leaf=2,
                                        class_weight="balanced", random_state=42, n_jobs=-1)
    return Pipeline([("preprocess", preprocessor), ("classifier", classifier)])


def feature_importance(model):
    """Sum one-hot importances back onto the original input column."""
    importances = model.named_steps["classifier"].feature_importances_
    encoder = model.named_steps["preprocess"].named_transformers_["cat"].named_steps["onehot"]
    grouped = {name: float(importances[i]) for i, name in enumerate(NUMERIC)}
    cursor = len(NUMERIC)
    for column, categories in zip(CATEGORICAL, encoder.categories_):
        grouped[column] = float(importances[cursor:cursor + len(categories)].sum())
        cursor += len(categories)
    ranked = sorted(grouped.items(), key=lambda kv: kv[1], reverse=True)
    return [{"feature": k, "importance": round(v, 4)} for k, v in ranked]


def train_model(df, features=FEATURES):
    X, y = df[features], df["severity"]
    stratify = y if y.value_counts().min() >= 2 else None
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=stratify)

    model = build_pipeline()
    model.fit(X_train, y_train)
    pred = model.predict(X_test)
    labels = sorted(y.unique().tolist())

    metrics = {
        "dataset_rows": int(len(df)),
        "training_rows": int(len(X_train)),
        "test_rows": int(len(X_test)),
        "accuracy": round(float(accuracy_score(y_test, pred)), 4),
        "balanced_accuracy": round(float(balanced_accuracy_score(y_test, pred)), 4),
        "macro_f1": round(float(f1_score(y_test, pred, average="macro", zero_division=0)), 4),
        "majority_baseline": round(float(y_test.value_counts(normalize=True).max()), 4),
        "class_share": {k: round(float(v), 4) for k, v in y.value_counts(normalize=True).items()},
        "classification_report": classification_report(y_test, pred, labels=labels,
                                                       output_dict=True, zero_division=0),
        "confusion_matrix": confusion_matrix(y_test, pred, labels=labels).tolist(),
        "target_classes": labels,
        "feature_importance": feature_importance(model),
        "feature_columns": list(features),
        "sklearn_version": sklearn.__version__,
    }
    return model, list(features), labels, metrics


def train_and_save():
    """Train on data/accidents.csv, write all artefacts, return (model, features)."""
    df, features = prepare_data()
    model, features, _, metrics = train_model(df, features)
    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(model, os.path.join(MODEL_DIR, "rf_model.pkl"))
    with open(os.path.join(MODEL_DIR, "features.json"), "w", encoding="utf-8") as f:
        json.dump(features, f, indent=2)
    with open(os.path.join(MODEL_DIR, "metrics.json"), "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
    print(f"Trained on {metrics['dataset_rows']:,} records.")
    print(f"Accuracy {metrics['accuracy']:.3f} | balanced accuracy {metrics['balanced_accuracy']:.3f} "
          f"| macro-F1 {metrics['macro_f1']:.3f} | majority baseline {metrics['majority_baseline']:.3f}")
    return model, features


if __name__ == "__main__":
    train_and_save()
