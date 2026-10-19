"""
SafeRoute Analytics - ML Model for Accident Severity Classification
Uses Random Forest, with feature engineering and evaluation metrics
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.metrics import (
    classification_report, confusion_matrix, accuracy_score,
    roc_auc_score
)
import joblib
import os
import json


def load_and_preprocess(filepath="data/accidents.csv"):
    df = pd.read_csv(filepath)

    # Feature engineering
    df['is_peak_hour'] = df['hour'].apply(
        lambda h: 1 if (7 <= h <= 9) or (17 <= h <= 20) else 0
    )
    df['is_night'] = df['hour'].apply(lambda h: 1 if h < 6 or h >= 21 else 0)
    df['is_weekend'] = df['day_of_week'].apply(
        lambda d: 1 if d in ['Saturday', 'Sunday'] else 0
    )
    df['bad_weather'] = df['weather_condition'].apply(
        lambda w: 1 if w in ['Fog', 'Rain', 'Storm', 'Haze'] else 0
    )
    df['poor_visibility'] = df['light_condition'].apply(
        lambda l: 1 if l in ['Dark (Unlit)', 'Dusk/Dawn'] else 0
    )

    # Categorical encoding
    cat_cols = ['road_type', 'weather_condition', 'light_condition',
                'accident_type', 'cause', 'vehicle_type', 'city', 'state']
    encoders = {}
    for col in cat_cols:
        le = LabelEncoder()
        df[col + '_enc'] = le.fit_transform(df[col].astype(str))
        encoders[col] = le

    # Target encoding
    severity_map = {'Property Damage Only': 0, 'Minor': 1, 'Serious': 2, 'Fatal': 3}
    df['severity_num'] = df['severity'].map(severity_map)

    return df, encoders


def train_model(df):
    features = [
        'hour', 'month', 'is_peak_hour', 'is_night', 'is_weekend',
        'bad_weather', 'poor_visibility', 'speed_kmh', 'vehicles_involved',
        'road_type_enc', 'weather_condition_enc', 'light_condition_enc',
        'accident_type_enc', 'cause_enc', 'vehicle_type_enc',
        'city_enc', 'state_enc'
    ]

    X = df[features].fillna(0)
    y = df['severity_num']

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42, stratify=y
    )

    scaler = StandardScaler()
    X_train_sc = scaler.fit_transform(X_train)
    X_test_sc = scaler.transform(X_test)

    # Random Forest
    rf = RandomForestClassifier(
        n_estimators=150, max_depth=12, min_samples_split=5,
        random_state=42, class_weight='balanced', n_jobs=-1
    )
    rf.fit(X_train_sc, y_train)

    y_pred = rf.predict(X_test_sc)
    accuracy = accuracy_score(y_test, y_pred)

    # Feature importance
    feature_importance = pd.DataFrame({
        'feature': features,
        'importance': rf.feature_importances_
    }).sort_values('importance', ascending=False)

    # Classification report
    report = classification_report(
        y_test, y_pred,
        target_names=['Property Damage Only', 'Minor', 'Serious', 'Fatal'],
        output_dict=True
    )

    # Confusion matrix
    cm = confusion_matrix(y_test, y_pred)

    return rf, scaler, features, {
        'accuracy': float(accuracy),
        'classification_report': report,
        'confusion_matrix': cm.tolist(),
        'feature_importance': feature_importance.to_dict(orient='records')
    }


def save_model(model, scaler, features, metrics, encoders, out_dir="models"):
    os.makedirs(out_dir, exist_ok=True)
    joblib.dump(model, f"{out_dir}/rf_model.pkl")
    joblib.dump(scaler, f"{out_dir}/scaler.pkl")
    joblib.dump(encoders, f"{out_dir}/encoders.pkl")

    with open(f"{out_dir}/features.json", "w") as f:
        json.dump(features, f)

    # Save metrics (exclude confusion matrix numpy objects)
    metrics_to_save = {k: v for k, v in metrics.items() if k != 'confusion_matrix'}
    metrics_to_save['confusion_matrix'] = metrics['confusion_matrix']
    with open(f"{out_dir}/metrics.json", "w") as f:
        json.dump(metrics_to_save, f, indent=2)

    print(f"Model saved to {out_dir}/")
    print(f"Accuracy: {metrics['accuracy']:.4f}")


if __name__ == "__main__":
    print("Loading data...")
    df, encoders = load_and_preprocess("data/accidents.csv")
    print("Training model...")
    model, scaler, features, metrics = train_model(df)
    save_model(model, scaler, features, metrics, encoders)
    print("Done!")
