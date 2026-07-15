import unittest
import pandas as pd
from parser import parse_activities_csv
from physiology import compute_ewma_workloads, UserProfile
from optimizer import generate_recommendations, build_structured_workout

class TestOptimizer(unittest.TestCase):
    def test_build_structured_workout(self):
        profile = UserProfile(ftp_watts=250, weight_kg=60.0)
        w = build_structured_workout("Cycling", "Zone 2 Endurance", 80.0, profile, "Thursday", 1.0)

        self.assertEqual(w["modality"], "Cycling")
        self.assertEqual(w["category"], "Zone 2 Endurance")
        self.assertEqual(w["target_load"], 80.0)
        self.assertIn("prescription", w)
        self.assertIn("interval_structure", w)

    def test_generate_recommendations(self):
        sample_path = "/usr/local/google/home/mileshudgins/sandbox/breakaway-ai/sample_workouts.csv"
        df = compute_ewma_workloads(parse_activities_csv(sample_path))
        profile = UserProfile()

        # Day Recommendation
        day_res = generate_recommendations(df, horizon_days=1, user_profile=profile)
        self.assertIn("current_state", day_res)
        self.assertIn("recommendations", day_res)
        self.assertEqual(len(day_res["recommendations"]), 1)

        rec = day_res["recommendations"][0]
        self.assertIn("primary", rec)
        self.assertIn("alt1", rec)
        self.assertIn("alt2", rec)

        # Week Recommendation
        week_res = generate_recommendations(df, horizon_days=7, user_profile=profile)
        self.assertEqual(len(week_res["recommendations"]), 7)

if __name__ == "__main__":
    unittest.main()
