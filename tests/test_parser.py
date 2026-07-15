import unittest
import pandas as pd
import numpy as np
from parser import parse_activities_csv, normalize_activity_type, calculate_fallback_load

class TestParser(unittest.TestCase):
    def test_normalize_activity_type(self):
        self.assertEqual(normalize_activity_type("Ride"), "Cycling")
        self.assertEqual(normalize_activity_type("VirtualRide"), "Cycling")
        self.assertEqual(normalize_activity_type("Run"), "Running")
        self.assertEqual(normalize_activity_type("TrailRun"), "Running")
        self.assertEqual(normalize_activity_type("Hike"), "Hiking")
        self.assertEqual(normalize_activity_type("WeightTraining"), "Strength")
        self.assertEqual(normalize_activity_type("Unknown"), "Other")

    def test_parse_sample_csv(self):
        sample_path = "/usr/local/google/home/mileshudgins/sandbox/breakaway-ai/sample_workouts.csv"
        df = parse_activities_csv(sample_path)
        
        self.assertIsInstance(df, pd.DataFrame)
        self.assertFalse(df.empty)
        self.assertIn("Date", df.columns)
        self.assertIn("Load", df.columns)
        self.assertIn("Type", df.columns)
        self.assertIn("Distance_km", df.columns)
        self.assertIn("Moving_Time_mins", df.columns)

    def test_timeline_continuity(self):
        sample_path = "/usr/local/google/home/mileshudgins/sandbox/breakaway-ai/sample_workouts.csv"
        df = parse_activities_csv(sample_path)
        
        dates = pd.to_datetime(df["Date"]).dt.date.tolist()
        for i in range(len(dates) - 1):
            delta = (dates[i+1] - dates[i]).days
            self.assertEqual(delta, 1, f"Gap found between {dates[i]} and {dates[i+1]}")

if __name__ == "__main__":
    unittest.main()
