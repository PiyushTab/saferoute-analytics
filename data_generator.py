"""
SafeRoute Analytics - Road Accident Hotspot Detection
Data generator for synthetic accident dataset with realistic distributions
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import random
import os

# Seed for reproducibility
np.random.seed(42)
random.seed(42)

# --- Indian city hotspot coordinates (lat, lon, city) ---
HOTSPOT_ZONES = [
    # Mumbai
    (19.076, 72.877, "Mumbai", "Maharashtra"),
    (19.033, 72.855, "Mumbai", "Maharashtra"),
    (19.120, 72.900, "Mumbai", "Maharashtra"),
    # Delhi
    (28.635, 77.225, "Delhi", "Delhi"),
    (28.700, 77.100, "Delhi", "Delhi"),
    (28.550, 77.200, "Delhi", "Delhi"),
    # Bangalore
    (12.971, 77.594, "Bangalore", "Karnataka"),
    (12.935, 77.620, "Bangalore", "Karnataka"),
    (13.010, 77.550, "Bangalore", "Karnataka"),
    # Chennai
    (13.082, 80.270, "Chennai", "Tamil Nadu"),
    (13.050, 80.210, "Chennai", "Tamil Nadu"),
    # Hyderabad
    (17.385, 78.486, "Hyderabad", "Telangana"),
    (17.440, 78.400, "Hyderabad", "Telangana"),
    # Pune
    (18.520, 73.856, "Pune", "Maharashtra"),
    (18.580, 73.900, "Pune", "Maharashtra"),
    # Kolkata
    (22.572, 88.363, "Kolkata", "West Bengal"),
    (22.600, 88.400, "Kolkata", "West Bengal"),
    # Ahmedabad
    (23.022, 72.571, "Ahmedabad", "Gujarat"),
    (23.070, 72.610, "Ahmedabad", "Gujarat"),
    # Jaipur
    (26.912, 75.787, "Jaipur", "Rajasthan"),
    (26.950, 75.820, "Jaipur", "Rajasthan"),
]

ROAD_TYPES = ["Highway", "Urban Road", "Rural Road", "Expressway", "State Highway", "Service Road"]
WEATHER_CONDITIONS = ["Clear", "Fog", "Rain", "Drizzle", "Haze", "Mist", "Storm"]
LIGHT_CONDITIONS = ["Daylight", "Dusk/Dawn", "Dark (Lit)", "Dark (Unlit)"]
ACCIDENT_TYPES = [
    "Head-on Collision", "Rear-end Collision", "Side Collision", "Rollover",
    "Pedestrian Hit", "Cyclist Hit", "Two-wheeler Collision", "Fixed Object Hit",
    "Animal Hit", "Multi-vehicle Pile-up"
]
CAUSES = [
    "Over-speeding", "Drunk Driving", "Distracted Driving", "Signal Jumping",
    "Wrong-side Driving", "Poor Road Condition", "Vehicle Defect", "Fatigue",
    "Poor Visibility", "Lane Violation"
]
VEHICLE_TYPES = ["Car", "Truck", "Motorcycle", "Bus", "Auto-rickshaw", "Bicycle", "Tractor"]


def generate_accident_data(n_records=3000):
    records = []
    start_date = datetime(2020, 1, 1)
    end_date = datetime(2024, 12, 31)
    date_range_days = (end_date - start_date).days

    for _ in range(n_records):
        # Pick a hotspot zone with spread
        zone = random.choice(HOTSPOT_ZONES)
        base_lat, base_lon, city, state = zone

        # Add noise around the hotspot
        lat = base_lat + np.random.normal(0, 0.05)
        lon = base_lon + np.random.normal(0, 0.05)

        # Random date/time
        rand_days = random.randint(0, date_range_days)
        accident_date = start_date + timedelta(days=rand_days)

        # Hour with peak hours (7-9am, 5-8pm have more accidents)
        hour_weights = [0.5, 0.4, 0.3, 0.3, 0.4, 0.7, 1.2, 2.0, 1.8, 1.0,
                        0.9, 0.9, 1.0, 1.0, 0.9, 0.8, 1.5, 2.2, 2.0, 1.5,
                        1.2, 1.0, 0.8, 0.6]
        hour = random.choices(range(24), weights=hour_weights)[0]
        minute = random.randint(0, 59)

        # Weather (clear is most common)
        weather = random.choices(
            WEATHER_CONDITIONS,
            weights=[60, 8, 12, 6, 7, 5, 2]
        )[0]

        # Light conditions depend on hour
        if 6 <= hour <= 18:
            light = random.choices(LIGHT_CONDITIONS, weights=[85, 5, 8, 2])[0]
        elif hour in [5, 19]:
            light = random.choices(LIGHT_CONDITIONS, weights=[10, 50, 25, 15])[0]
        else:
            light = random.choices(LIGHT_CONDITIONS, weights=[0, 5, 45, 50])[0]

        road_type = random.choices(ROAD_TYPES, weights=[30, 35, 15, 10, 7, 3])[0]
        accident_type = random.choice(ACCIDENT_TYPES)
        cause = random.choice(CAUSES)
        vehicle = random.choice(VEHICLE_TYPES)

        # Speed (km/h) — varies by road type
        speed_map = {
            "Highway": (80, 40), "Urban Road": (40, 20), "Rural Road": (60, 30),
            "Expressway": (100, 30), "State Highway": (70, 35), "Service Road": (30, 15)
        }
        mean_spd, std_spd = speed_map[road_type]
        speed = max(10, np.random.normal(mean_spd, std_spd))

        # Vehicles involved
        vehicles_involved = random.choices([1, 2, 3, 4, 5], weights=[30, 45, 15, 7, 3])[0]

        # Casualties
        fatalities = np.random.poisson(0.4 if road_type in ["Highway", "Expressway"] else 0.2)
        injuries = np.random.poisson(1.5)
        fatalities = min(fatalities, 10)
        injuries = min(injuries, 20)

        # Severity score (composite)
        sev_score = (fatalities * 10 + injuries * 3 + (speed / 100) * 4 +
                     (1 if weather in ["Fog", "Storm", "Rain"] else 0) * 3 +
                     (1 if light in ["Dark (Unlit)", "Dark (Lit)"] else 0) * 2)

        # Severity label
        if sev_score >= 20 or fatalities >= 3:
            severity = "Fatal"
        elif sev_score >= 10 or fatalities >= 1 or injuries >= 4:
            severity = "Serious"
        elif sev_score >= 4 or injuries >= 1:
            severity = "Minor"
        else:
            severity = "Property Damage Only"

        records.append({
            "accident_id": f"ACC{str(_+1).zfill(5)}",
            "date": accident_date.strftime("%Y-%m-%d"),
            "year": accident_date.year,
            "month": accident_date.month,
            "month_name": accident_date.strftime("%B"),
            "day_of_week": accident_date.strftime("%A"),
            "hour": hour,
            "time_of_day": f"{hour:02d}:{minute:02d}",
            "latitude": round(lat, 6),
            "longitude": round(lon, 6),
            "city": city,
            "state": state,
            "road_type": road_type,
            "weather_condition": weather,
            "light_condition": light,
            "accident_type": accident_type,
            "cause": cause,
            "vehicle_type": vehicle,
            "vehicles_involved": vehicles_involved,
            "speed_kmh": round(speed, 1),
            "fatalities": fatalities,
            "injuries": injuries,
            "severity": severity,
            "severity_score": round(sev_score, 2),
        })

    df = pd.DataFrame(records)
    return df


if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    print("Generating accident dataset...")
    df = generate_accident_data(3000)
    df.to_csv("data/accidents.csv", index=False)
    df.to_excel("data/accidents.xlsx", index=False)
    print(f"Dataset saved: {len(df)} records")
    print(df.head())
    print(df['severity'].value_counts())
