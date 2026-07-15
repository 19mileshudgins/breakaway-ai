import logging
import io
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

try:
    from google.adk.tools import tool
except ImportError:
    def tool(fn):
        return fn

from app.parser import parse_activities_csv
from app.physiology import (
    compute_ewma_workloads, classify_acwr_zone, calculate_power_zones,
    calculate_hr_zones, calculate_running_paces, UserProfile
)
from app.optimizer import generate_recommendations

logger = logging.getLogger("breakaway_ai.tools")

# --- Explicit Pydantic Schemas for Tool Inputs & Outputs ---

class WorkloadMemoryInput(BaseModel):
    csv_data_str: str = Field(description="Raw CSV content containing historical activity dates and loads")

class WorkloadMemoryOutput(BaseModel):
    status: str = Field(description="Execution status ('success' or 'error')")
    date: Optional[str] = Field(default=None, description="Final timeline date")
    acute_load: Optional[float] = Field(default=None, description="7-day Acute Load (EWMA Fatigue)")
    chronic_load: Optional[float] = Field(default=None, description="28-day Chronic Load (EWMA Fitness)")
    acwr: Optional[float] = Field(default=None, description="Acute:Chronic Workload Ratio")
    acwr_zone: Optional[str] = Field(default=None, description="Workload zone classification")
    error_message: Optional[str] = Field(default=None, description="Guided recovery message if error occurs")

class ExertionAnalysisInput(BaseModel):
    avg_power_watts: float = Field(description="Average power output in Watts")
    avg_hr_bpm: float = Field(description="Average heart rate in Beats Per Minute")
    distance_miles: float = Field(description="Distance covered in miles")
    duration_mins: float = Field(description="Duration in minutes")
    ftp_watts: int = Field(default=261, description="FTP baseline in Watts")
    max_hr_bpm: int = Field(default=205, description="Max Heart Rate baseline in BPM")

class ExertionAnalysisOutput(BaseModel):
    status: str = Field(description="Execution status")
    speed_mph: Optional[float] = Field(default=None, description="Calculated speed in mph")
    pct_ftp: Optional[float] = Field(default=None, description="Power output as percentage of FTP")
    pct_max_hr: Optional[float] = Field(default=None, description="Heart rate as percentage of Max HR")
    category: Optional[str] = Field(default=None, description="Periodized workout category")
    cardiovascular_drift_detected: Optional[bool] = Field(default=None, description="Cardiovascular drift status")
    coaching_takeaway: Optional[str] = Field(default=None, description="Physiological coaching takeaway")
    error_message: Optional[str] = Field(default=None, description="Error explanation")

class WorkoutOptionsInput(BaseModel):
    horizon_days: int = Field(default=1, description="1 for single day, 7 for full week recommendations")
    user_ftp: int = Field(default=261, description="FTP baseline in Watts")
    user_max_hr: int = Field(default=205, description="Max HR baseline in BPM")
    user_weight_kg: float = Field(default=63.0, description="Weight in kg")

class WorkoutOptionsOutput(BaseModel):
    status: str = Field(description="Execution status")
    current_acwr: Optional[float] = Field(default=None, description="Current ACWR")
    acwr_zone: Optional[str] = Field(default=None, description="Current ACWR zone")
    recommendations: Optional[List[Dict[str, Any]]] = Field(default=None, description="Periodized workout recommendations")
    error_message: Optional[str] = Field(default=None, description="Error explanation")

class BiometricZonesInput(BaseModel):
    ftp_watts: int = Field(default=261, description="FTP in Watts")
    max_hr_bpm: int = Field(default=205, description="Max HR in BPM")
    weight_kg: float = Field(default=63.0, description="Weight in kg")

class BiometricZonesOutput(BaseModel):
    status: str = Field(description="Execution status")
    power_zones: Optional[Dict[str, str]] = Field(default=None, description="Calibrated cycling power zones")
    hr_zones: Optional[Dict[str, str]] = Field(default=None, description="Calibrated heart rate zones")
    error_message: Optional[str] = Field(default=None, description="Error explanation")

# --- Explicitly Typed ADK Tools ---

@tool
def calculate_workload_memory(params: WorkloadMemoryInput) -> WorkloadMemoryOutput:
    """
    Parses historical activity CSV content and calculates rolling 7-day Acute Load (EWMA lambda=7),
    28-day Chronic Load (EWMA lambda=28), and Acute:Chronic Workload Ratio (ACWR).
    """
    try:
        if not params.csv_data_str or not isinstance(params.csv_data_str, str):
            return WorkloadMemoryOutput(
                status="error",
                error_message="CSV data content must be a non-empty string. Please provide valid CSV formatting."
            )
            
        df_parsed = parse_activities_csv(io.StringIO(params.csv_data_str))
        df_ewma = compute_ewma_workloads(df_parsed)
        
        last_row = df_ewma.iloc[-1]
        acwr_val = float(last_row["ACWR"])
        status_info = classify_acwr_zone(acwr_val)
        
        return WorkloadMemoryOutput(
            status="success",
            date=str(last_row["Date"]),
            acute_load=round(float(last_row["Acute_Load"]), 2),
            chronic_load=round(float(last_row["Chronic_Load"]), 2),
            acwr=round(acwr_val, 2),
            acwr_zone=status_info["zone"]
        )
    except Exception as e:
        logger.error(f"Error in calculate_workload_memory tool: {e}")
        return WorkloadMemoryOutput(
            status="error",
            error_message=f"Failed to calculate workload memory: {str(e)}"
        )

@tool
def analyze_exertion_and_drift(params: ExertionAnalysisInput) -> ExertionAnalysisOutput:
    """
    Analyzes historical workout exertion, calculating speed, % FTP, % Max HR, and detecting cardiovascular drift.
    """
    try:
        if params.duration_mins <= 0 or params.distance_miles <= 0:
            return ExertionAnalysisOutput(
                status="error",
                error_message="Duration and distance must be greater than 0."
            )

        speed_mph = params.distance_miles / (params.duration_mins / 60.0)
        pct_ftp = (params.avg_power_watts / params.ftp_watts) * 100.0 if params.ftp_watts > 0 else 0.0
        pct_max_hr = (params.avg_hr_bpm / params.max_hr_bpm) * 100.0 if params.max_hr_bpm > 0 else 0.0
        
        has_cardio_drift = (pct_ftp <= 78.0 and pct_max_hr >= 82.0)
        category = "Cardiovascular Drift" if has_cardio_drift else ("Lactate Threshold" if pct_max_hr >= 85.0 else "Zone 2 Endurance")
        
        return ExertionAnalysisOutput(
            status="success",
            speed_mph=round(speed_mph, 1),
            pct_ftp=round(pct_ftp, 1),
            pct_max_hr=round(pct_max_hr, 1),
            category=category,
            cardiovascular_drift_detected=has_cardio_drift,
            coaching_takeaway=(
                "Cardiovascular drift detected: Heart rate reached Zone 4 Threshold territory despite Zone 2 power. "
                "Indicates accumulated fatigue, dehydration, or heat stress requiring active recovery."
                if has_cardio_drift else "Heart rate response aligned well with target power output."
            )
        )
    except Exception as e:
        logger.error(f"Error in analyze_exertion_and_drift tool: {e}")
        return ExertionAnalysisOutput(
            status="error",
            error_message=f"Exertion calculation error: {str(e)}"
        )

@tool
def get_periodized_workout_options(params: WorkoutOptionsInput) -> WorkoutOptionsOutput:
    """
    Generates structured periodized workout recommendations with 3 alternative workout modalities per day.
    """
    try:
        sample_path = "/usr/local/google/home/mileshudgins/sandbox/breakaway-ai/sample_workouts.csv"
        df_parsed = parse_activities_csv(sample_path)
        df_ewma = compute_ewma_workloads(df_parsed)
        
        profile = UserProfile(ftp_watts=params.user_ftp, max_hr_bpm=params.user_max_hr, weight_kg=params.user_weight_kg)
        recs = generate_recommendations(df_ewma, horizon_days=params.horizon_days, user_profile=profile)
        
        return WorkoutOptionsOutput(
            status="success",
            current_acwr=recs["current_state"]["acwr"],
            acwr_zone=recs["current_state"]["acwr_status"]["zone"],
            recommendations=recs["recommendations"]
        )
    except Exception as e:
        logger.error(f"Error in get_periodized_workout_options tool: {e}")
        return WorkoutOptionsOutput(
            status="error",
            error_message=f"Failed to generate periodized options: {str(e)}"
        )

@tool
def calibrate_biometric_zones(params: BiometricZonesInput) -> BiometricZonesOutput:
    """
    Calibrates cycling power zones (W & W/kg) and heart rate zones (BPM) based on user biometrics.
    """
    try:
        power_zones = calculate_power_zones(params.ftp_watts, params.weight_kg)
        hr_zones = calculate_hr_zones(params.max_hr_bpm)
        
        return BiometricZonesOutput(
            status="success",
            power_zones=power_zones,
            hr_zones=hr_zones
        )
    except Exception as e:
        logger.error(f"Error in calibrate_biometric_zones tool: {e}")
        return BiometricZonesOutput(
            status="error",
            error_message=str(e)
        )
