import unittest
import asyncio
from app.agent import root_agent
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
from app.multi_agent import guardrail_inspector, hitl_confirmation_hook
from app.memory import memory_bank, history_compactor
from app.observability import AgentJsonFormatter

class TestADKAgent(unittest.TestCase):
    def test_root_agent_initialization(self):
        self.assertEqual(root_agent.name, "breakaway_ai")
        self.assertEqual(len(root_agent.tools), 4)

    def test_pydantic_adk_tools_execution(self):
        # 1. Biometric Zones Tool
        res_zones = calibrate_biometric_zones(BiometricZonesInput(ftp_watts=261, max_hr_bpm=205, weight_kg=63.0))
        self.assertEqual(res_zones.status, "success")
        self.assertIn("Zone 2 (Endurance)", res_zones.power_zones)

        # 2. Exertion & Drift Tool
        res_drift = analyze_exertion_and_drift(ExertionAnalysisInput(
            avg_power_watts=197.0, avg_hr_bpm=176.0, distance_miles=17.9, duration_mins=54.0
        ))
        self.assertEqual(res_drift.status, "success")
        self.assertTrue(res_drift.cardiovascular_drift_detected)
        self.assertEqual(res_drift.category, "Cardiovascular Drift")

        # 3. Periodized Workout Options Tool
        res_opts = get_periodized_workout_options(WorkoutOptionsInput(horizon_days=1))
        self.assertEqual(res_opts.status, "success")
        self.assertEqual(len(res_opts.recommendations), 1)

    def test_async_memory_bank_and_compactor(self):
        # Async memory test
        async def run_async_test():
            saved = await memory_bank.save_user_profile_async("test_session", {"ftp_watts": 270})
            self.assertTrue(saved)
            loaded = await memory_bank.load_user_profile_async("test_session")
            self.assertEqual(loaded["ftp_watts"], 270)
        
        asyncio.run(run_async_test())

        # History Compactor test
        turns = [{"role": "user", "content": f"Message {i}"} for i in range(10)]
        compacted = history_compactor.compact_conversation_history(turns, max_turns=4)
        self.assertLess(len(compacted), len(turns))
        self.assertIn("COMPACTED HISTORY SUMMARY", compacted[0]["content"])

    def test_hitl_confirmation_hook(self):
        plan = {"title": "Zone 2 Ride", "category": "Zone 2 Endurance"}
        
        # Unconfirmed
        res_awaiting = hitl_confirmation_hook.request_execution_confirmation(plan, user_approved=None)
        self.assertEqual(res_awaiting["status"], "AWAITING_HUMAN_CONFIRMATION")

        # Confirmed
        res_approved = hitl_confirmation_hook.request_execution_confirmation(plan, user_approved=True)
        self.assertEqual(res_approved["status"], "APPROVED_AND_EXECUTED")

if __name__ == "__main__":
    unittest.main()
