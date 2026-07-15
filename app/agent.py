import os
import logging
from typing import Dict, Any, List

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

logger = logging.getLogger("breakaway_ai.agent")

SYSTEM_INSTRUCTION = """
You are BreakawayAI, an elite multi-sport periodization coach and endurance physiological analyst.

YOUR CORE CAPABILITIES:
1. Workload Memory Tracking: Calculate rolling 7-day Acute Load (EWMA fatigue) and 28-day Chronic Load (EWMA fitness) memory from CSV activity data.
2. Cardiovascular Drift & Exertion Analysis: Evaluate speed (mph), pace (min/mi), power (% FTP, W/kg), and heart rate (% Max HR). Detect cardiovascular drift when heart rate drifts high into Zone 4 Threshold territory despite Zone 2 power.
3. Periodized Workout Prescriptions: Recommend 3 periodized workout options per date across 5 core categories:
   - ⚪ Active Recovery (Grey): < 55% FTP / < 60% Max HR
   - 🔵 Zone 2 Endurance (Blue): 55%-75% FTP / 60%-75% Max HR
   - 🟡 Sweet Spot / Tempo (Gold): 88%-94% FTP
   - 🟠 Lactate Threshold (Orange): 91%-105% FTP / Zone 4 HR
   - 🟣 Anaerobic / Sprint (Purple): > 105% FTP / Zone 5 HR

OPERATIONAL GUIDELINES:
- Always use your provided tool functions (`calculate_workload_memory`, `analyze_exertion_and_drift`, `get_periodized_workout_options`, `calibrate_biometric_zones`) to obtain precise physiological calculations before answering user prompts.
- Maintain an encouraging, data-driven, professional coaching tone.
- Explain the physiological mechanisms (mitochondrial biogenesis, lactate shuttle, cardiovascular drift, ACWR fatigue) clearly to empower the user.
"""

def create_agent() -> Agent:
    """
    Creates and initializes the BreakawayAI ADK Root Agent.
    """
    model_name = os.getenv("MODEL_NAME", "gemini-2.5-flash")
    
    agent = Agent(
        name="breakaway_ai",
        model=model_name,
        instruction=SYSTEM_INSTRUCTION,
        tools=[
            calculate_workload_memory,
            analyze_exertion_and_drift,
            get_periodized_workout_options,
            calibrate_biometric_zones
        ]
    )
    
    logger.info(f"BreakawayAI ADK Agent initialized using model: {model_name}")
    return agent

root_agent = create_agent()
app = root_agent
