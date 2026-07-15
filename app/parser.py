import pandas as pd
import numpy as np
import math
from datetime import datetime, timedelta
from typing import Tuple, Dict, Any, Union, List
import io

ACTIVITY_TYPE_MAP = {
    "Ride": "Cycling",
    "VirtualRide": "Cycling",
    "GravelRide": "Cycling",
    "Run": "Running",
    "TrailRun": "Running",
    "Hike": "Hiking",
    "WeightTraining": "Strength",
}

def normalize_activity_type(raw_type: str) -> str:
    if not isinstance(raw_type, str):
        return "Other"
    return ACTIVITY_TYPE_MAP.get(raw_type.strip(), "Other")

def calculate_fallback_load(row: pd.Series, max_hr_default: int = 205, resting_hr_default: int = 47) -> float:
    load_val = row.get("Load")
    if pd.notna(load_val) and load_val != "" and float(load_val) >= 0:
        return float(load_val)

    activity_type = normalize_activity_type(str(row.get("Type", "")))
    moving_time_sec = float(row.get("Moving Time", 0)) if pd.notna(row.get("Moving Time")) else 0.0
    duration_mins = moving_time_sec / 60.0

    if activity_type == "Cycling":
        norm_power = float(row.get("Norm Power", 0)) if pd.notna(row.get("Norm Power")) else 0.0
        ftp = float(row.get("FTP", 0)) if pd.notna(row.get("FTP")) else 0.0
        intensity = float(row.get("Intensity", 0)) if pd.notna(row.get("Intensity")) else 0.0
        
        if norm_power > 0 and ftp > 0 and moving_time_sec > 0:
            intensity_factor = intensity / 100.0 if intensity > 1.0 else intensity
            load = ((moving_time_sec * norm_power * intensity_factor) / (3600.0 * ftp)) * 100.0
            return max(0.0, load)

    avg_hr = float(row.get("Avg HR", 0)) if pd.notna(row.get("Avg HR")) else 0.0
    resting_hr = float(row.get("Resting HR", resting_hr_default)) if pd.notna(row.get("Resting HR")) else float(resting_hr_default)
    max_hr = float(max_hr_default)

    if avg_hr > resting_hr and max_hr > resting_hr and duration_mins > 0:
        hr_ratio = (avg_hr - resting_hr) / (max_hr - resting_hr)
        hr_ratio = max(0.0, min(1.0, hr_ratio))
        trimp = duration_mins * hr_ratio * 0.64 * math.exp(1.92 * hr_ratio)
        return max(0.0, trimp)

    rpe = float(row.get("RPE", 0)) if pd.notna(row.get("RPE")) else 0.0
    if duration_mins > 0 and rpe > 0:
        return max(0.0, duration_mins * rpe * 0.15)

    return 0.0

def parse_activities_csv(file_input: Union[str, io.BytesIO, io.StringIO], max_hr_default: int = 205, resting_hr_default: int = 47) -> pd.DataFrame:
    """
    Parses CSV into daily aggregated DataFrame, preserving Avg Power, Norm Power, Avg HR, RPE, and activity names.
    """
    if isinstance(file_input, str):
        df = pd.read_csv(file_input)
    else:
        df = pd.read_csv(file_input)

    df.columns = [c.strip() for c in df.columns]

    if "Date" not in df.columns:
        raise ValueError("CSV missing required 'Date' column.")

    df["Date_Parsed"] = pd.to_datetime(df["Date"], errors="coerce").dt.date
    df = df.dropna(subset=["Date_Parsed"]).sort_values("Date_Parsed")

    if df.empty:
        raise ValueError("CSV contains no valid date entries.")

    df["Computed_Load"] = df.apply(lambda r: calculate_fallback_load(r, max_hr_default, resting_hr_default), axis=1)
    df["Normalized_Type"] = df["Type"].apply(normalize_activity_type)
    df["Distance_km"] = df["Distance"].apply(lambda x: float(x)/1000.0 if pd.notna(x) else 0.0)
    df["Moving_Time_mins"] = df["Moving Time"].apply(lambda x: float(x)/60.0 if pd.notna(x) else 0.0)

    daily_rows = []
    grouped = df.groupby("Date_Parsed")

    min_date = df["Date_Parsed"].min()
    max_date = df["Date_Parsed"].max()

    date_map = {}

    for date_key, group in grouped:
        total_load = group["Computed_Load"].sum()
        total_dist = group["Distance_km"].sum()
        total_time = group["Moving_Time_mins"].sum()

        top_activity = group.sort_values("Computed_Load", ascending=False).iloc[0]
        primary_type = top_activity["Normalized_Type"]

        avg_power_val = float(top_activity["Avg Power"]) if ("Avg Power" in top_activity and pd.notna(top_activity["Avg Power"])) else np.nan
        norm_power_val = float(top_activity["Norm Power"]) if ("Norm Power" in top_activity and pd.notna(top_activity["Norm Power"])) else np.nan
        avg_hr_val = float(top_activity["Avg HR"]) if ("Avg HR" in top_activity and pd.notna(top_activity["Avg HR"])) else np.nan
        name_val = str(top_activity["Name"]) if ("Name" in top_activity and pd.notna(top_activity["Name"])) else ""
        rpe_val = float(top_activity["RPE"]) if ("RPE" in top_activity and pd.notna(top_activity["RPE"])) else np.nan

        date_map[date_key] = {
            "Date": date_key,
            "Load": float(total_load),
            "Distance_km": float(total_dist),
            "Moving_Time_mins": float(total_time),
            "Type": primary_type,
            "Is_Rest": False,
            "Activity_Count": len(group),
            "Avg_Power": avg_power_val,
            "Norm_Power": norm_power_val,
            "Avg_HR": avg_hr_val,
            "Name": name_val,
            "RPE": rpe_val
        }

    full_timeline = []
    curr_date = min_date
    while curr_date <= max_date:
        if curr_date in date_map:
            full_timeline.append(date_map[curr_date])
        else:
            full_timeline.append({
                "Date": curr_date,
                "Load": 0.0,
                "Distance_km": 0.0,
                "Moving_Time_mins": 0.0,
                "Type": "Rest",
                "Is_Rest": True,
                "Activity_Count": 0,
                "Avg_Power": np.nan,
                "Norm_Power": np.nan,
                "Avg_HR": np.nan,
                "Name": "Rest Day",
                "RPE": np.nan
            })
        curr_date += timedelta(days=1)

    result_df = pd.DataFrame(full_timeline)
    return result_df
