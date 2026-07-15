import unittest
import pandas as pd
import numpy as np
from parser import parse_activities_csv
from physiology import (
    compute_ewma_workloads, classify_acwr_zone, calculate_power_zones,
    calculate_hr_zones, calculate_running_paces, generate_latest_workout_analysis,
    generate_recent_training_summary, UserProfile
)

class TestPhysiology(unittest.TestCase):
    def test_ewma_calculations(self):
        sample_path = "/usr/local/google/home/mileshudgins/sandbox/breakaway-ai/sample_workouts.csv"
        df_parsed = parse_activities_csv(sample_path)
        df_ewma = compute_ewma_workloads(df_parsed)

        self.assertIn("Acute_Load", df_ewma.columns)
        self.assertIn("Chronic_Load", df_ewma.columns)
        self.assertIn("ACWR", df_ewma.columns)
        self.assertFalse(df_ewma["Acute_Load"].isna().any())
        self.assertFalse(df_ewma["Chronic_Load"].isna().any())
        self.assertFalse(df_ewma["ACWR"].isna().any())

    def test_classify_acwr_zone(self):
        self.assertEqual(classify_acwr_zone(1.6)["status"], "danger")
        self.assertEqual(classify_acwr_zone(1.4)["status"], "warning")
        self.assertEqual(classify_acwr_zone(1.1)["status"], "optimal")
        self.assertEqual(classify_acwr_zone(0.6)["status"], "low")

    def test_user_profile_zones(self):
        profile = UserProfile(ftp_watts=260, weight_kg=65.0, max_hr_bpm=200, resting_hr_bpm=50)
        
        pz = calculate_power_zones(profile.ftp_watts, profile.weight_kg)
        self.assertIn("Zone 2 (Endurance)", pz)
        self.assertIn("143W", pz["Zone 2 (Endurance)"])

        hrz = calculate_hr_zones(profile.max_hr_bpm, profile.resting_hr_bpm)
        self.assertIn("Zone 2 (Endurance)", hrz)

        paces = calculate_running_paces(profile)
        self.assertIn("Easy / Recovery Pace", paces)
        self.assertIn("Threshold Pace (LT)", paces)

    def test_latest_workout_analysis(self):
        sample_path = "/usr/local/google/home/mileshudgins/sandbox/breakaway-ai/sample_workouts.csv"
        df = compute_ewma_workloads(parse_activities_csv(sample_path))
        profile = UserProfile()

        analysis = generate_latest_workout_analysis(df, profile)
        self.assertIn("title", analysis)
        self.assertIn("category", analysis)
        self.assertIn("color_cfg", analysis)
        self.assertIn("stats_summary", analysis)
        self.assertIn("analysis", analysis)
        self.assertIn("impact", analysis)

if __name__ == "__main__":
    unittest.main()
