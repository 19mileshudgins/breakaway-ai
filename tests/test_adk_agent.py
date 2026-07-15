import unittest
import json
from app.agent import root_agent
from app.tools import (
    calculate_workload_memory,
    analyze_exertion_and_drift,
    get_periodized_workout_options,
    calibrate_biometric_zones
)
from app.multi_agent import guardrail_inspector
from app.observability import AgentJsonFormatter, PII_REGEX_PATTERNS

class TestADKAgent(unittest.TestCase):
    def test_root_agent_initialization(self):
        self.assertEqual(root_agent.name, "breakaway_ai")
        self.assertEqual(len(root_agent.tools), 4)

    def test_adk_tools_execution(self):
        # 1. Biometric Zones Tool
        res_zones = calibrate_biometric_zones(261, 205, 63.0)
        data_zones = json.loads(res_zones)
        self.assertEqual(data_zones["status"], "success")
        self.assertIn("power_zones", data_zones)

        # 2. Exertion & Drift Tool
        res_drift = analyze_exertion_and_drift(197.0, 176.0, 17.9, 54.0, 261, 205)
        data_drift = json.loads(res_drift)
        self.assertEqual(data_drift["status"], "success")
        self.assertTrue(data_drift["cardiovascular_drift_detected"])
        self.assertEqual(data_drift["category"], "Cardiovascular Drift")

        # 3. Periodized Workout Options Tool
        res_opts = get_periodized_workout_options(1, 261, 205, 63.0)
        data_opts = json.loads(res_opts)
        self.assertEqual(data_opts["status"], "success")
        self.assertEqual(len(data_opts["recommendations"]), 1)

    def test_guardrail_inspector(self):
        # Unsafe ACWR 1.60 should trigger guardrail
        unsafe_workout = {"title": "VO2 Max Intervals", "category": "Anaerobic / Sprint"}
        res = guardrail_inspector.inspect_and_enforce_safety(1.60, unsafe_workout)
        self.assertTrue(res["guardrail_triggered"])
        self.assertEqual(res["overridden_workout"]["category"], "Active Recovery")

    def test_pii_redaction(self):
        dirty_text = "User test@example.com logged activity with SSN 123-45-6789."
        clean_text = AgentJsonFormatter.redact_pii(dirty_text)
        self.assertNotIn("test@example.com", clean_text)
        self.assertIn("[REDACTED_PII]", clean_text)

if __name__ == "__main__":
    unittest.main()
