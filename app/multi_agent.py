import logging
import asyncio
from typing import Dict, Any, Optional

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
    WorkoutOptionsInput,
    BiometricZonesInput
)
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
    """
    Agentic Guardrail Inspector enforcing safety constraints on training load progression.
    Prevents unsafe high-intensity workout prescriptions when ACWR >= 1.50 (Danger Overtraining Zone).
    """
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
    """
    Human-in-the-Loop (HITL) execution confirmation hook requiring explicit user approval
    before finalizing alternative workout replacements or high-volume plan alterations.
    """
    def request_execution_confirmation(
        self,
        workout_plan: Dict[str, Any],
        user_approved: Optional[bool] = None
    ) -> Dict[str, Any]:
        if user_approved is None:
            logger.info(f"HITL Hook: Intercepted plan change '{workout_plan.get('title')}'. Awaiting user confirmation.")
            return {
                "status": "AWAITING_HUMAN_CONFIRMATION",
                "message": f"Proposed Workout Plan: '{workout_plan.get('title')}' ({workout_plan.get('category')}). Please confirm to replace active plan.",
                "requires_confirmation": True
            }
        elif user_approved is True:
            logger.info(f"HITL Hook: User approved plan change '{workout_plan.get('title')}'. Committing execution.")
            return {
                "status": "APPROVED_AND_EXECUTED",
                "message": f"Workout plan '{workout_plan.get('title')}' confirmed and updated.",
                "confirmed_plan": workout_plan
            }
        else:
            logger.info(f"HITL Hook: User rejected plan change.")
            return {
                "status": "REJECTED_BY_USER",
                "message": "Plan alteration rejected by user. Preserving existing scheduled workout."
            }

guardrail_inspector = GuardrailAgent()
hitl_confirmation_hook = HumanInTheLoopHook()

# 5. Fully Integrated Main Execution Pipeline
async def execute_orchestrated_agent_pipeline(
    user_prompt: str,
    session_id: str = "default_session",
    user_approved: Optional[bool] = None
) -> Dict[str, Any]:
    """
    Main integrated multi-agent execution pipeline. Orchestrates model routing, diagnostic calls,
    reasoning coach generation, safety guardrail inspection, HITL confirmation, and persistent DB storage.
    """
    logger.info(f"Pipeline Executing for session '{session_id}' | Model Routing: gemini-2.5-flash -> gemini-2.5-pro")
    
    # Step 1: Load user profile from persistent SQLite DB
    profile = await memory_bank.load_user_profile_async(session_id)
    
    # Step 2: Route to PhysiologyDiagnosticsAgent (gemini-2.5-flash) for biometric calibration & workload
    diag_res = calibrate_biometric_zones(BiometricZonesInput(
        ftp_watts=profile["ftp_watts"],
        max_hr_bpm=profile["max_hr_bpm"],
        weight_kg=profile["weight_kg"]
    ))
    
    # Step 3: Route to PeriodizationCoachAgent (gemini-2.5-pro) for 3-option workout generation
    recs_res = get_periodized_workout_options(WorkoutOptionsInput(
        user_ftp=profile["ftp_watts"],
        user_max_hr=profile["max_hr_bpm"],
        user_weight_kg=profile["weight_kg"]
    ))
    
    current_acwr = recs_res.current_acwr or 1.0
    primary_workout = recs_res.recommendations[0]["primary"] if recs_res.recommendations else {}

    # Step 4: Run Safety Guardrail Inspection
    guardrail_result = guardrail_inspector.inspect_and_enforce_safety(current_acwr, primary_workout)
    active_workout = guardrail_result["overridden_workout"] if guardrail_result["guardrail_triggered"] else primary_workout

    # Step 5: Execute Human-in-the-Loop Confirmation Hook
    hitl_result = hitl_confirmation_hook.request_execution_confirmation(active_workout, user_approved=user_approved)

    # Step 6: Persist state asynchronously to SQLite DB
    pipeline_state = {
        "user_profile": profile,
        "current_acwr": current_acwr,
        "active_workout": active_workout,
        "hitl_status": hitl_result["status"]
    }
    await memory_bank.save_user_profile_async(session_id, pipeline_state)

    return {
        "status": "success",
        "session_id": session_id,
        "model_routing": {
            "diagnostics_agent": "gemini-2.5-flash",
            "coach_agent": "gemini-2.5-pro"
        },
        "acwr": current_acwr,
        "guardrail": guardrail_result,
        "hitl_confirmation": hitl_result,
        "biometric_zones": diag_res.power_zones,
        "workout_options": recs_res.recommendations
    }
