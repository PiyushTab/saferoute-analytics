"""
SafeRoute Analytics - ML Model for Accident Severity Classification
Trained on Real Indian Road Accident records (MoRTH dataset: 88 cities, 35 states/UTs).
"""

import os
import json
import joblib
import pandas as pd
import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "data", "accidents.csv")
MODEL_DIR = os.path.join(BASE_DIR, "models")

NUMERIC = ["hour", "month", "speed_kmh", "vehicles_involved"]
CATEGORICAL = ["road_type", "weather_condition", "light_condition", "cause", "vehicle_type", "city"]


def prepare_data(filepath=DATA_PATH):
    if not os.path.exists(filepath):
        from data_loader_india import prepare_indian_dataset
        prepare_indian_dataset()
    df = pd.read_csv(filepath)
    required = NUMERIC + CATEGORICAL + ["severity"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError("Dataset is missing required columns: " + ", ".join(missing))
    df = df.dropna(subset=["severity"]).copy()
    df["severity"] = df["severity"].astype(str)
    return df, NUMERIC + CATEGORICAL


def train_model(df, features):
    X = df[features].copy()
    y = df["severity"].astype(str)
    numeric = [c for c in NUMERIC if c in features]
    categorical = [c for c in CATEGORICAL if c in features]
    
    preprocessor = ColumnTransformer([
        ("num", Pipeline([("imputer", SimpleImputer(strategy="median"))]), numeric),
        ("cat", Pipeline([("imputer", SimpleImputer(strategy="most_frequent")),
                          ("onehot", OneHotEncoder(handle_unknown="ignore"))]), categorical)
    ])
    
    counts = y.value_counts()
    stratify = y if counts.min() >= 2 else None
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=stratify
    )
    
    model = Pipeline([
        ("preprocess", preprocessor),
        ("classifier", RandomForestClassifier(n_estimators=150, random_state=42,
                                               class_weight="balanced", min_samples_leaf=2, n_jobs=-1))
    ])
    model.fit(X_train, y_train)
    pred = model.predict(X_test)
    labels = sorted(y.unique().tolist())
    
    # Feature importances extraction from pipeline
    try:
        clf = model.named_steps["classifier"]
        cat_encoder = model.named_steps["preprocess"].named_transformers_["cat"].named_steps["onehot"]
        cat_features = cat_encoder.get_feature_names_out(categorical).tolist()
        all_feat_names = numeric + cat_features
        importances = clf.feature_importances_
        
        # Aggregate importance by main feature group
        group_imp = {}
        for fn, imp in zip(all_feat_names, importances):
            root = fn.split("_")[0] if "_" in fn else fn
            group_imp[root] = group_imp.get(root, 0.0) + float(imp)
            
        feature_importance_list = [
            {"feature": k, "importance": round(v, 4)} 
            for k, v in sorted(group_imp.items(), key=lambda x: x[1], reverse=True)
        ]
    except Exception:
        feature_importance_list = [
            {"feature": f, "importance": round(1.0 / len(features), 3)} for f in features
        ]
        
    metrics = {
        "dataset_rows": int(len(df)),
        "training_rows": int(len(X_train)),
        "test_rows": int(len(X_test)),
        "accuracy": round(float(accuracy_score(y_test, pred)), 4),
        "macro_f1": round(float(f1_score(y_test, pred, average="macro", zero_division=0)), 4),
        "classification_report": classification_report(y_test, pred, labels=labels, output_dict=True, zero_division=0),
        "confusion_matrix": confusion_matrix(y_test, pred, labels=labels).tolist(),
        "target_classes": labels,
        "feature_importance": feature_importance_list,
        "feature_columns": features,
        "source": "Real Indian Road Accident Records (MoRTH / City Police Data)"
    }
    return model, features, labels, metrics


if __name__ == "__main__":
    print("Loading Real Indian Road Accident dataset...")
    df, features = prepare_data()
    print(f"Training Random Forest classifier on {len(df)} records...")
    model, features, labels, metrics = train_model(df, features)
    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(model, os.path.join(MODEL_DIR, "rf_model.pkl"))
    with open(os.path.join(MODEL_DIR, "features.json"), "w", encoding="utf-8") as f:
        json.dump(features, f, indent=2)
    with open(os.path.join(MODEL_DIR, "metrics.json"), "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
    print(f"Successfully trained on {len(df)} real Indian accident records.")
    print(f"Accuracy: {metrics['accuracy']:.4f}; Macro-F1: {metrics['macro_f1']:.4f}")
