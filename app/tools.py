import json
import logging
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional

try:
    from google.adk.tools import tool
except ImportError:
    def tool(fn):
        return fn

from app.parser import parse_activities_csv
from app.physiology import (
    compute_ewma_workloads, classify_acwr_zone, calculate_power_zones,
    calculate_hr_zones, calculate_running_paces, generate_latest_workout_analysis,
    generate_recent_training_summary, UserProfile
)
from app.optimizer import generate_recommendations

logger = logging.getLogger("breakaway_ai.tools")

@tool
def calculate_workload_memory(csv_data_str: str) -> str:
    """
    Parses historical activity CSV content and calculates rolling 7-day Acute Load (EWMA lambda=7),
    28-day Chronic Load (EWMA lambda=28), and Acute:Chronic Workload Ratio (ACWR).

    Args:
        csv_data_str (str): Raw CSV content containing activity Date, Load, Type, Distance, Moving Time, Power, and HR.

    Returns:
        str: JSON string containing final date, acute load, chronic load, acwr ratio, and zone classification.
    """
    try:
        if not csv_data_str or not isinstance(csv_data_str, str):
            return json.dumps({
                "status": "error",
                "error_code": "INVALID_INPUT",
                "message": "CSV data content must be a non-empty string. Please provide valid CSV formatting."
            })
            
        import io
        df_parsed = parse_activities_csv(io.StringIO(csv_data_str))
        df_ewma = compute_ewma_workloads(df_parsed)
        
        last_row = df_ewma.iloc[-1]
        acwr_val = float(last_row["ACWR"])
        status_info = classify_acwr_zone(acwr_val)
        
        return json.dumps({
            "status": "success",
            "date": str(last_row["Date"]),
            "acute_load": round(float(last_row["Acute_Load"]), 2),
            "chronic_load": round(float(last_row["Chronic_Load"]), 2),
            "acwr": round(acwr_val, 2),
            "acwr_zone": status_info["zone"],
            "safety_status": status_info["status"]
        })
    except Exception as e:
        logger.error(f"Error in calculate_workload_memory tool: {e}")
        return json.dumps({
            "status": "error",
            "error_code": "PROCESSING_FAILED",
            "message": f"Failed to calculate workload memory: {str(e)}. Please check CSV schema continuity."
        })

@tool
def analyze_exertion_and_drift(
    avg_power_watts: float,
    avg_hr_bpm: float,
    distance_miles: float,
    duration_mins: float,
    ftp_watts: int = 261,
    max_hr_bpm: int = 205
) -> str:
    """
    Analyzes historical workout exertion, calculating speed, % FTP, % Max HR, and detecting cardiovascular drift phenomena.

    Args:
        avg_power_watts (float): Average power output in Watts.
        avg_hr_bpm (float): Average heart rate in Beats Per Minute.
        distance_miles (float): Distance covered in miles.
        duration_mins (float): Duration in minutes.
        ftp_watts (int): User Functional Threshold Power baseline in Watts. Default is 261W.
        max_hr_bpm (int): User Maximum Heart Rate baseline in BPM. Default is 205 BPM.

    Returns:
        str: JSON string containing calculated metrics, cardiovascular drift detection, and physiological takeaways.
    """
    try:
        if duration_mins <= 0 or distance_miles <= 0:
            return json.dumps({
                "status": "error",
                "error_code": "INVALID_PARAMETERS",
                "message": "Duration and distance must be greater than 0."
            })

        speed_mph = distance_miles / (duration_mins / 60.0)
        pct_ftp = (avg_power_watts / ftp_watts) * 100.0 if ftp_watts > 0 else 0.0
        pct_max_hr = (avg_hr_bpm / max_hr_bpm) * 100.0 if max_hr_bpm > 0 else 0.0
        
        has_cardio_drift = (pct_ftp <= 78.0 and pct_max_hr >= 82.0)
        
        category = "Cardiovascular Drift" if has_cardio_drift else ("Lactate Threshold" if pct_max_hr >= 85.0 else "Zone 2 Endurance")
        
        return json.dumps({
            "status": "success",
            "speed_mph": round(speed_mph, 1),
            "pct_ftp": round(pct_ftp, 1),
            "pct_max_hr": round(pct_max_hr, 1),
            "category": category,
            "cardiovascular_drift_detected": has_cardio_drift,
            "coaching_takeaway": (
                "Cardiovascular drift detected: Heart rate reached Zone 4 Threshold territory despite Zone 2 power. "
                "Indicates accumulated fatigue, dehydration, or heat stress requiring active recovery."
                if has_cardio_drift else "Heart rate response aligned well with target power output."
            )
        })
    except Exception as e:
        logger.error(f"Error in analyze_exertion_and_drift tool: {e}")
        return json.dumps({
            "status": "error",
            "error_code": "CALCULATION_ERROR",
            "message": f"Exertion calculation error: {str(e)}"
        })

@tool
def get_periodized_workout_options(
    horizon_days: int = 1,
    user_ftp: int = 261,
    user_max_hr: int = 205,
    user_weight_kg: float = 63.0
) -> str:
    """
    Generates structured periodized workout recommendations with 3 alternative workout modalities per day.

    Args:
        horizon_days (int): 1 for single day, 7 for full week recommendations.
        user_ftp (int): FTP in Watts. Default 261W.
        user_max_hr (int): Max HR in BPM. Default 205 BPM.
        user_weight_kg (float): Weight in kg. Default 63.0 kg.

    Returns:
        str: JSON string containing current ACWR state and 3 periodized workout options per date.
    """
    try:
        sample_path = "/usr/local/google/home/mileshudgins/sandbox/breakaway-ai/sample_workouts.csv"
        df_parsed = parse_activities_csv(sample_path)
        df_ewma = compute_ewma_workloads(df_parsed)
        
        profile = UserProfile(ftp_watts=user_ftp, max_hr_bpm=user_max_hr, weight_kg=user_weight_kg)
        recs = generate_recommendations(df_ewma, horizon_days=horizon_days, user_profile=profile)
        
        return json.dumps({
            "status": "success",
            "current_acwr": recs["current_state"]["acwr"],
            "acwr_zone": recs["current_state"]["acwr_status"]["zone"],
            "recommendations": recs["recommendations"]
        })
    except Exception as e:
        logger.error(f"Error in get_periodized_workout_options tool: {e}")
        return json.dumps({
            "status": "error",
            "error_code": "PERIODIZATION_ERROR",
            "message": f"Failed to generate periodized options: {str(e)}"
        })

@tool
def calibrate_biometric_zones(ftp_watts: int = 261, max_hr_bpm: int = 205, weight_kg: float = 63.0) -> str:
    """
    Calibrates cycling power zones (W & W/kg) and heart rate zones (BPM) based on user biometrics.

    Args:
        ftp_watts (int): Functional Threshold Power in Watts.
        max_hr_bpm (int): Maximum Heart Rate in BPM.
        weight_kg (float): Weight in kilograms.

    Returns:
        str: JSON string with calibrated power and heart rate zones.
    """
    try:
        power_zones = calculate_power_zones(ftp_watts, weight_kg)
        hr_zones = calculate_hr_zones(max_hr_bpm)
        
        return json.dumps({
            "status": "success",
            "power_zones": power_zones,
            "hr_zones": hr_zones
        })
    except Exception as e:
        logger.error(f"Error in calibrate_biometric_zones tool: {e}")
        return json.dumps({
            "status": "error",
            "error_code": "ZONE_CALIBRATION_FAILED",
            "message": str(e)
        })
