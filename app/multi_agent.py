import logging
import asyncio
import os
import re
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional

try:
    import google.genai as genai
    HAS_GENAI = True
except ImportError:
    HAS_GENAI = False

try:
    from google.adk.agent import Agent
except ImportError:
    class Agent:
        def __init__(self, name: str, model: str, instruction: str, tools: list):
            self.name = name
            self.model = model
            self.instruction = instruction
            self.tools = tools

from app.tools import (
    calculate_workload_memory,
    analyze_exertion_and_drift,
    get_periodized_workout_options,
    calibrate_biometric_zones,
    WorkloadMemoryInput,
    ExertionAnalysisInput,
    WorkoutOptionsInput,
    BiometricZonesInput
)
from app.parser import parse_activities_csv
from app.physiology import compute_ewma_workloads, format_seconds_to_mile_pace, UserProfile
from app.memory import memory_bank, history_compactor

logger = logging.getLogger("breakaway_ai.multi_agent")

# 1. Physiology & Diagnostics Agent (Fast Model Routing: gemini-2.5-flash)
physiology_agent = Agent(
    name="PhysiologyDiagnosticsAgent",
    model="gemini-2.5-flash",
    instruction=(
        "You are a specialized exercise physiologist. Your sole focus is calculating Acute/Chronic EWMA workloads, "
        "detecting cardiovascular drift, and calibrating biometric zones."
    ),
    tools=[calculate_workload_memory, analyze_exertion_and_drift, calibrate_biometric_zones]
)

# 2. Strategic Periodization Coach Agent (Reasoning Model Routing: gemini-2.5-pro)
coach_agent = Agent(
    name="PeriodizationCoachAgent",
    model="gemini-2.5-pro",
    instruction=(
        "You are a master endurance coach. Formulate structured multi-sport periodization plans across 5 categories: "
        "Active Recovery, Zone 2 Endurance, Sweet Spot, Lactate Threshold, and Anaerobic Sprint."
    ),
    tools=[get_periodized_workout_options]
)

# 3. Agentic Safety & Guardrail Inspector
class GuardrailAgent:
    def inspect_and_enforce_safety(self, acwr: float, proposed_workout: Dict[str, Any]) -> Dict[str, Any]:
        if acwr >= 1.50 and proposed_workout.get("category") not in ["Active Recovery", "Rest"]:
            logger.warning(f"Guardrail triggered! ACWR is {acwr:.2f} (Danger Zone). Overriding proposed workout with Active Recovery.")
            return {
                "guardrail_triggered": True,
                "reason": f"Safety Intercept: ACWR is {acwr:.2f} (Overtraining Danger Zone). High-stress workout blocked.",
                "overridden_workout": {
                    "title": "Active Recovery Mobility & Spin",
                    "modality": "Active Recovery",
                    "category": "Active Recovery",
                    "target_load": 15.0,
                    "duration_mins": 30.0,
                    "prescription": "Light 30m Zone 1 spin (< 55% FTP) or active stretching. HR < 125 BPM."
                }
            }
        return {
            "guardrail_triggered": False,
            "reason": "ACWR within safe training progression boundaries.",
            "workout": proposed_workout
        }

# 4. Human-in-the-Loop (HITL) Execution Confirmation Hook
class HumanInTheLoopHook:
    def request_execution_confirmation(
        self,
        workout_plan: Dict[str, Any],
        user_approved: Optional[bool] = None
    ) -> Dict[str, Any]:
        if user_approved is None:
            return {
                "status": "AWAITING_HUMAN_CONFIRMATION",
                "message": f"Proposed Workout Plan: '{workout_plan.get('title')}'. Please confirm to replace active plan.",
                "requires_confirmation": True
            }
        elif user_approved is True:
            return {
                "status": "APPROVED_AND_EXECUTED",
                "message": f"Workout plan '{workout_plan.get('title')}' confirmed and updated.",
                "confirmed_plan": workout_plan
            }
        else:
            return {
                "status": "REJECTED_BY_USER",
                "message": "Plan alteration rejected by user. Preserving existing scheduled workout."
            }

guardrail_inspector = GuardrailAgent()
hitl_confirmation_hook = HumanInTheLoopHook()

def invoke_gemini_llm_reasoning(user_prompt: str, sample_path: str = "/usr/local/google/home/mileshudgins/sandbox/breakaway-ai/sample_workouts.csv") -> str:
    """
    Invokes Gemini 2.5 Flash directly via Vertex AI genai.Client with dataset context
    to perform dynamic LLM reasoning and answer any natural language training query.
    """
    df_parsed = parse_activities_csv(sample_path)
    active_df = df_parsed[df_parsed["Type"] != "Rest"].tail(14)

    full_prompt = f"""
You are BreakawayAI, an elite multi-sport periodization coach and endurance physiological analyst.

USER ATHLETE BIOMETRICS:
- Functional Threshold Power (FTP): 261 Watts
- Max Heart Rate: 205 BPM | Resting HR: 47 BPM
- Weight: 63.0 kg | Current ACWR: 0.99 (Sweet Spot)

RECENT ATHLETE ACTIVITY DATASET (CSV):
{active_df.to_csv(index=False)}

USER QUESTION:
{user_prompt}

INSTRUCTIONS FOR GEMINI COACH:
1. Answer the user's question accurately based on the provided activity dataset and biometrics.
2. Perform any needed math, averages, date filtering, pace conversions, or power calculations dynamically.
3. Keep the tone encouraging, concise, professional, and data-driven.
4. Format all key dates, metrics, paces, and wattages using clean HTML <b>bold</b> tags (e.g. <b>158.5 BPM</b>, <b>7:00 /mi</b>). Make sure every opening <b> tag has a matching closing </b> tag!
"""

    if HAS_GENAI:
        try:
            client = genai.Client(vertexai=True, project="sandbox-500619", location="us-central1")
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=full_prompt
            )
            if response and response.text:
                clean_text = response.text
                clean_text = re.sub(r'<b>(.*?)<b>', r'<b>\1</b>', clean_text, flags=re.IGNORECASE)
                clean_text = clean_text.replace("**", "<b>").replace("<b><b>", "<b>")
                return clean_text
        except Exception as e:
            logger.warning(f"Gemini API call failed: {e}. Falling back to computational analyzer.")

    # Computational Fallback if API is offline
    prompt_lower = user_prompt.lower()
    active_df["dist_mi"] = active_df["Distance_km"] * 0.621371
    active_df["pace_sec_mi"] = (active_df["Moving_Time_mins"] * 60.0) / active_df["dist_mi"].replace(0, np.nan)
    runs = active_df[active_df["Type"].isin(["Running", "Run", "TrailRun"])]

    if "run" in prompt_lower or "pace" in prompt_lower:
        if not runs.empty:
            is_lowest = any(w in prompt_lower for w in ["lowest", "slowest", "easiest", "recovery"])
            selected_run = runs.sort_values(by="pace_sec_mi", ascending=not is_lowest).iloc[0]
            w_date = str(selected_run["Date"])
            w_dist_mi = float(selected_run["dist_mi"])
            w_mins = float(selected_run["Moving_Time_mins"])
            w_pace_str = format_seconds_to_mile_pace(float(selected_run["pace_sec_mi"]))
            w_hr = float(selected_run["Avg_HR"]) if ("Avg_HR" in selected_run and not np.isnan(selected_run["Avg_HR"])) else 158
            desc = "lowest paced (easiest)" if is_lowest else "highest paced (fastest)"
            return f"Your <b>{desc} run</b> was on <b>{w_date}</b> covering <b>{w_dist_mi:.1f} miles</b> in <b>{w_mins:.0f}m</b> at a pace of <b>{w_pace_str}</b> (Avg HR: <b>{w_hr:.0f} BPM</b>)."

    return f"Based on your <b>261W FTP</b> and current <b>0.99 ACWR</b>, your baseline aerobic conditioning is sitting in the Sweet Spot progression zone."

def execute_orchestrated_agent_pipeline(
    user_prompt: str,
    session_id: str = "default_session",
    user_approved: Optional[bool] = None
) -> Dict[str, Any]:
    """
    Main integrated multi-agent execution pipeline. Uses Gemini 2.5 Flash LLM to reason dynamically
    over athlete dataset and answer natural language training queries.
    """
    logger.info(f"Pipeline Executing Gemini LLM reasoning query: '{user_prompt}' for session '{session_id}'")
    
    profile = memory_bank.load_user_profile(session_id)
    user_prof = profile.get("user_profile", profile) if isinstance(profile, dict) else profile
    ftp_watts = user_prof.get("ftp_watts", 261) if isinstance(user_prof, dict) else 261

    coaching_response = invoke_gemini_llm_reasoning(user_prompt)

    diag_res = calibrate_biometric_zones(BiometricZonesInput(ftp_watts=ftp_watts, max_hr_bpm=205, weight_kg=63.0))
    recs_res = get_periodized_workout_options(WorkoutOptionsInput(user_ftp=ftp_watts))
    primary_workout = recs_res.recommendations[0]["primary"] if recs_res.recommendations else {}
    
    guardrail_result = guardrail_inspector.inspect_and_enforce_safety(0.99, primary_workout)
    hitl_result = hitl_confirmation_hook.request_execution_confirmation(primary_workout, user_approved=user_approved)

    return {
        "status": "success",
        "session_id": session_id,
        "coaching_response": coaching_response,
        "acwr": 0.99,
        "guardrail": guardrail_result,
        "hitl_confirmation": hitl_result,
        "biometric_zones": diag_res.power_zones,
        "model_routing": {"diagnostics_agent": "gemini-2.5-flash", "coach_agent": "gemini-2.5-pro"}
    }
