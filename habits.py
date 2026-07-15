import pandas as pd
import numpy as np
from typing import Dict, Any, List

WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

def analyze_habits(df: pd.DataFrame, trailing_days: int = 60) -> Dict[int, Dict[str, Any]]:
    """
    Analyzes the trailing N days of historical training data to construct weekday habit profiles.
    Returns a dictionary keyed by weekday integer (0=Monday, ..., 6=Sunday).
    """
    df = df.copy()
    df["Date_Obj"] = pd.to_datetime(df["Date"])
    df["Weekday"] = df["Date_Obj"].dt.weekday

    max_date = df["Date_Obj"].max()
    cutoff_date = max_date - pd.Timedelta(days=trailing_days)
    recent_df = df[df["Date_Obj"] >= cutoff_date]

    if recent_df.empty:
        recent_df = df

    habit_profile = {}

    for day_idx in range(7):
        day_name = WEEKDAYS[day_idx]
        day_data = recent_df[recent_df["Weekday"] == day_idx]
        total_occurrences = len(day_data)

        if total_occurrences == 0:
            habit_profile[day_idx] = {
                "weekday_name": day_name,
                "preferred_modality": "Rest",
                "modality_probabilities": {"Rest": 1.0},
                "avg_load": 0.0,
                "std_load": 0.0,
                "avg_duration_mins": 0.0,
                "is_typical_rest": True
            }
            continue

        # Count modalities
        modality_counts = day_data["Type"].value_counts()
        probabilities = {mod: float(count / total_occurrences) for mod, count in modality_counts.items()}
        preferred_modality = modality_counts.index[0] if not modality_counts.empty else "Rest"

        active_days = day_data[day_data["Type"] != "Rest"]
        avg_load = float(day_data["Load"].mean())
        std_load = float(day_data["Load"].std()) if total_occurrences > 1 else 0.0
        avg_duration = float(active_days["Moving_Time_mins"].mean()) if not active_days.empty else 0.0

        is_typical_rest = (preferred_modality == "Rest") or (avg_load < 10.0)

        habit_profile[day_idx] = {
            "weekday_name": day_name,
            "preferred_modality": preferred_modality,
            "modality_probabilities": probabilities,
            "avg_load": round(avg_load, 1),
            "std_load": round(np.nan_to_num(std_load), 1),
            "avg_duration_mins": round(avg_duration, 1),
            "is_typical_rest": is_typical_rest
        }

    return habit_profile
