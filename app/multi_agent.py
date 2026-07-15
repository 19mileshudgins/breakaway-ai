import logging
from typing import Dict, Any

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
    calibrate_biometric_zones
)

logger = logging.getLogger("breakaway_ai.multi_agent")

# 1. Physiology & Diagnostics Agent (Fast Model Routing: gemini-2.5-flash)
physiology_agent = Agent(
    name="PhysiologyDiagnosticsAgent",
    model="gemini-2.5-flash",
    instruction=(
        "You are a specialized exercise physiologist. Your sole focus is calculating Acute/Chronic EWMA workloads, "
        "detecting cardiovascular drift, and calibrating biometric zones. Always invoke calculate_workload_memory and analyze_exertion_and_drift."
    ),
    tools=[calculate_workload_memory, analyze_exertion_and_drift, calibrate_biometric_zones]
)

# 2. Strategic Periodization Coach Agent (Reasoning Model Routing: gemini-2.5-pro)
coach_agent = Agent(
    name="PeriodizationCoachAgent",
    model="gemini-2.5-pro",
    instruction=(
        "You are a master endurance coach. Formulate structured multi-sport periodization plans across 5 categories: "
        "Active Recovery, Zone 2 Endurance, Sweet Spot, Lactate Threshold, and Anaerobic Sprint. Provide 3 alternative options per day."
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

guardrail_inspector = GuardrailAgent()
