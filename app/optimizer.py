import pandas as pd
import numpy as np
from datetime import timedelta
from typing import Dict, Any, List, Tuple
from habits import analyze_habits, WEEKDAYS
from physiology import classify_acwr_zone, UserProfile, calculate_running_paces, calculate_power_zones, calculate_hr_zones, CATEGORY_COLORS

TARGET_ACWR = 1.15
MAX_ACWR_CEILING = 1.4

SPORT_EMOJIS = {
    "Cycling": "🚴",
    "Running": "🏃",
    "Hiking": "🥾",
    "Strength": "🏋️",
    "Rest": "😴",
    "Swimming": "🏊"
}

def build_structured_workout(
    modality: str,
    workout_type: str,
    target_load: float,
    user_profile: UserProfile,
    weekday_name: str,
    sim_acwr: float
) -> Dict[str, Any]:
    """
    Builds a real periodized workout with precise Heart Rate & Power / Pace Zone targets,
    color-coded category tags, interval structure, physiological adaptation rationale, and ACWR impact.
    """
    ftp = user_profile.ftp_watts
    weight = user_profile.weight_kg
    w_kg = ftp / weight if weight > 0 else 4.14
    running_paces = calculate_running_paces(user_profile)
    
    emoji = SPORT_EMOJIS.get(modality, "🏋️")

    if modality == "Rest":
        return {
            "title": "Full Rest & Recovery",
            "modality": "Rest",
            "category": "Active Recovery",
            "color_cfg": CATEGORY_COLORS["Active Recovery"],
            "emoji": SPORT_EMOJIS["Rest"],
            "target_load": 0.0,
            "duration_mins": 0.0,
            "prescription": "Rest day. Light 15-minute active mobility & stretching.",
            "target_zones": "HR < 115 BPM (Resting Recovery)",
            "interval_structure": "No structured stress. Optional gentle walk or foam rolling.",
            "why_recommended": f"Prescribed to bring short-term fatigue down as your current ACWR is elevated ({sim_acwr:.2f}).",
            "benefit": "Enables central nervous system recovery, muscle tissue repair, and glycogen replenishment."
        }

    if modality == "Cycling":
        if workout_type == "Zone 2 Endurance":
            p_min = int(0.65 * ftp)
            p_max = int(0.75 * ftp)
            w_min = 0.65 * w_kg
            w_max = 0.75 * w_kg
            duration = max(45.0, (target_load / 65.0) * 60.0)
            return {
                "title": "Zone 2 Aerobic Base Ride",
                "modality": "Cycling",
                "category": "Zone 2 Endurance",
                "color_cfg": CATEGORY_COLORS["Zone 2 Endurance"],
                "emoji": "🚴",
                "target_load": round(target_load, 1),
                "duration_mins": round(duration, 1),
                "prescription": f"Target Avg Power: {p_min}W – {p_max}W ({w_min:.2f} – {w_max:.2f} W/kg). Target HR: 135 – 150 BPM (Zone 2).",
                "target_zones": f"Power: {p_min}W–{p_max}W | HR: 135–150 BPM (Zone 2 Endurance)",
                "interval_structure": "10m Warmup @ 140W -> Continuous steady Zone 2 spin @ 85-95 RPM -> 10m Cooldown.",
                "why_recommended": f"Prescribed to build aerobic endurance and mitochondrial density matching your regular {weekday_name} riding habit.",
                "benefit": "Enhances fat oxidation efficiency, increases capillary density, and builds fatigue resistance without high stress."
            }

        elif workout_type == "Sweet Spot / Tempo":
            p_min = int(0.88 * ftp)
            p_max = int(0.94 * ftp)
            duration = max(50.0, (target_load / 80.0) * 60.0)
            return {
                "title": "Sweet Spot Sub-Threshold Intervals",
                "modality": "Cycling",
                "category": "Sweet Spot / Tempo",
                "color_cfg": CATEGORY_COLORS["Sweet Spot / Tempo"],
                "emoji": "🚴",
                "target_load": round(target_load * 1.15, 1),
                "duration_mins": round(duration, 1),
                "prescription": f"Interval Target: {p_min}W – {p_max}W (88-94% FTP). Target HR: 158 – 172 BPM.",
                "target_zones": f"Power: {p_min}W–{p_max}W | HR: 158–172 BPM (Sweet Spot Zone)",
                "interval_structure": "15m Warmup -> 3x12m @ Sweet Spot (230W-245W) w/ 4m easy spin recovery -> 10m Cooldown.",
                "why_recommended": "Higher-intensity stimulus designed to raise your lactate threshold with manageable muscular fatigue.",
                "benefit": "Significantly increases Functional Threshold Power (FTP) and lactate clearance efficiency."
            }

        elif workout_type == "VO2 Max Threshold":
            p_min = int(1.05 * ftp)
            p_max = int(1.15 * ftp)
            duration = max(45.0, (target_load / 90.0) * 50.0)
            return {
                "title": "VO2 Max Aerobic Power Intervals",
                "modality": "Cycling",
                "category": "Anaerobic / Sprint",
                "color_cfg": CATEGORY_COLORS["Anaerobic / Sprint"],
                "emoji": "🚴",
                "target_load": round(target_load * 1.25, 1),
                "duration_mins": round(duration, 1),
                "prescription": f"Interval Target: {p_min}W – {p_max}W (105-115% FTP). Target HR: 175 – 190 BPM.",
                "target_zones": f"Power: {p_min}W–{p_max}W | HR: 175–190 BPM (Zone 5 VO2 Max)",
                "interval_structure": "15m Warmup -> 4x5m @ VO2 Max (275W-295W) w/ 4m recovery spin -> 10m Cooldown.",
                "why_recommended": "High-intensity interval session targeting expansion of your ceiling maximal aerobic capacity.",
                "benefit": "Increases stroke volume, maximal oxygen uptake (VO2 Max), and high-power repeatability."
            }

        else: # Active Recovery
            p_max = int(0.55 * ftp)
            return {
                "title": "Zone 1 Active Recovery Spin",
                "modality": "Cycling",
                "category": "Active Recovery",
                "color_cfg": CATEGORY_COLORS["Active Recovery"],
                "emoji": "🚴",
                "target_load": round(target_load * 0.4, 1),
                "duration_mins": 35.0,
                "prescription": f"Target Power: < {p_max}W (< 55% FTP). Target HR: < 130 BPM (Zone 1).",
                "target_zones": f"Power: < {p_max}W | HR: < 130 BPM (Active Recovery)",
                "interval_structure": "35m continuous easy cadence spin (90+ RPM) with zero high torque effort.",
                "why_recommended": "Low-stress recovery spin to flush metabolic byproducts without adding fatigue.",
                "benefit": "Stimulates leg muscle blood flow and speeds up recovery from recent hard training."
            }

    elif modality == "Running":
        easy_pace = running_paces["Easy / Recovery Pace"]
        thresh_pace = running_paces["Threshold Pace (LT)"]

        if workout_type == "Zone 2 Endurance":
            duration = max(30.0, (target_load / 55.0) * 40.0)
            return {
                "title": "Zone 2 Aerobic Base Run",
                "modality": "Running",
                "category": "Zone 2 Endurance",
                "color_cfg": CATEGORY_COLORS["Zone 2 Endurance"],
                "emoji": "🏃",
                "target_load": round(target_load, 1),
                "duration_mins": round(duration, 1),
                "prescription": f"Target Pace: {easy_pace} (Easy Aerobic Base). Target HR: 138 – 152 BPM.",
                "target_zones": f"Pace: {easy_pace} | HR: 138–152 BPM (Zone 2)",
                "interval_structure": "5m Warmup walk/jog -> Continuous Zone 2 run @ conversational pace -> 5m Cooldown.",
                "why_recommended": f"Matches your regular {weekday_name} running habit while staying strictly within optimal aerobic building load.",
                "benefit": "Builds running economy, strengthens connective tissue, and improves aerobic stamina."
            }

        elif workout_type == "Tempo / Threshold Run":
            duration = max(35.0, (target_load / 70.0) * 45.0)
            return {
                "title": "Lactate Threshold Tempo Run",
                "modality": "Running",
                "category": "Lactate Threshold",
                "color_cfg": CATEGORY_COLORS["Lactate Threshold"],
                "emoji": "🏃",
                "target_load": round(target_load * 1.15, 1),
                "duration_mins": round(duration, 1),
                "prescription": f"Target Pace: {thresh_pace} (LT Threshold). Target HR: 165 – 178 BPM.",
                "target_zones": f"Pace: {thresh_pace} | HR: 165–178 BPM (Zone 4 Threshold)",
                "interval_structure": "10m Warmup @ easy pace -> 3x8m @ LT Pace ({thresh_pace}) w/ 3m recovery jog -> 10m Cooldown.",
                "why_recommended": "Targeted threshold workout designed to lift your sustainable running pace and fatigue barrier.",
                "benefit": "Improves lactate shuttle capability, allowing you to sustain faster paces longer."
            }

        else: # Hill Repeats / Sprint
            duration = max(30.0, (target_load / 65.0) * 35.0)
            return {
                "title": "Hill Repeat Power Intervals",
                "modality": "Running",
                "category": "Anaerobic / Sprint",
                "color_cfg": CATEGORY_COLORS["Anaerobic / Sprint"],
                "emoji": "🏃",
                "target_load": round(target_load * 1.10, 1),
                "duration_mins": round(duration, 1),
                "prescription": "Effort: Hard 30s Hill Ascents (8-10% grade). Target HR: 175 – 188 BPM.",
                "target_zones": "Pace: Hard Hill Effort | HR: 175–188 BPM (Zone 5)",
                "interval_structure": "10m Warmup -> 8x30s Hard Hill Ascents w/ walk-down recovery -> 10m Cooldown.",
                "why_recommended": "Builds running-specific leg strength and power without the high impact of flat sprinting.",
                "benefit": "Recruits fast-twitch muscle fibers, improves running mechanics, and strengthens strides."
            }

    else:
        duration = max(30.0, (target_load / 40.0) * 35.0)
        return {
            "title": f"{modality} Cross-Training",
            "modality": modality,
            "category": "Active Recovery",
            "color_cfg": CATEGORY_COLORS["Active Recovery"],
            "emoji": SPORT_EMOJIS.get(modality, "🏊"),
            "target_load": round(target_load * 0.85, 1),
            "duration_mins": round(duration, 1),
            "prescription": f"Moderate-effort {modality} session.",
            "target_zones": "HR: 125–145 BPM (Zone 1-2)",
            "interval_structure": "Continuous steady-state cross-training effort.",
            "why_recommended": f"Alternative low-impact training modality for {weekday_name}.",
            "benefit": "Maintains aerobic conditioning while resting impact-loaded joints."
        }

def generate_recommendations(
    df: pd.DataFrame,
    horizon_days: int = 1, # 1 for Day, 7 for Week
    user_profile: UserProfile = UserProfile()
) -> Dict[str, Any]:
    """
    Generates structured, periodized workout recommendations with 2 additional modality/type alternative options for each day.
    """
    df = df.sort_values("Date").reset_index(drop=True)
    last_row = df.iloc[-1]
    last_date = pd.to_datetime(last_row["Date"]).date()

    curr_acute = float(last_row["Acute_Load"])
    curr_chronic = float(last_row["Chronic_Load"])
    curr_acwr = float(last_row["ACWR"])

    habit_profile = analyze_habits(df)

    alpha_a = 2.0 / (7.0 + 1.0)  # 0.25
    alpha_c = 2.0 / (28.0 + 1.0) # ~0.0689655

    sim_acute = curr_acute
    sim_chronic = curr_chronic
    recommendations = []

    for i in range(1, horizon_days + 1):
        target_date = last_date + timedelta(days=i)
        weekday_idx = target_date.weekday()
        day_habit = habit_profile[weekday_idx]

        preferred_modality = day_habit["preferred_modality"]
        habit_avg_load = day_habit["avg_load"]

        if sim_chronic > 0:
            desired_acute = TARGET_ACWR * sim_chronic
            needed_load = (desired_acute - sim_chronic * (1.0 - alpha_a)) / alpha_a
            target_load = max(0.0, needed_load)
        else:
            target_load = 40.0

        sim_acwr = sim_acute / sim_chronic if sim_chronic > 0 else 0.0

        if sim_acwr >= 1.5 or day_habit["is_typical_rest"]:
            primary = build_structured_workout("Rest", "Rest", 0.0, user_profile, day_habit["weekday_name"], sim_acwr)
            alt1 = build_structured_workout("Cycling", "Active Recovery", 20.0, user_profile, day_habit["weekday_name"], sim_acwr)
            alt2 = build_structured_workout("Running", "Zone 2 Endurance", 25.0, user_profile, day_habit["weekday_name"], sim_acwr)
        else:
            blended_target = 0.5 * target_load + 0.5 * habit_avg_load
            max_allowed_load = (MAX_ACWR_CEILING * sim_chronic - sim_acute * (1.0 - alpha_a)) / alpha_a
            rec_load = min(blended_target, max(20.0, max_allowed_load))

            if preferred_modality == "Cycling":
                primary = build_structured_workout("Cycling", "Zone 2 Endurance", rec_load, user_profile, day_habit["weekday_name"], sim_acwr)
                alt1 = build_structured_workout("Running", "Zone 2 Endurance", rec_load * 0.9, user_profile, day_habit["weekday_name"], sim_acwr)
                alt2 = build_structured_workout("Cycling", "Sweet Spot / Tempo", rec_load * 1.1, user_profile, day_habit["weekday_name"], sim_acwr)
            elif preferred_modality == "Running":
                primary = build_structured_workout("Running", "Zone 2 Endurance", rec_load, user_profile, day_habit["weekday_name"], sim_acwr)
                alt1 = build_structured_workout("Cycling", "Zone 2 Endurance", rec_load * 1.05, user_profile, day_habit["weekday_name"], sim_acwr)
                alt2 = build_structured_workout("Running", "Tempo / Threshold Run", rec_load * 1.15, user_profile, day_habit["weekday_name"], sim_acwr)
            else:
                primary = build_structured_workout("Cycling", "Zone 2 Endurance", rec_load, user_profile, day_habit["weekday_name"], sim_acwr)
                alt1 = build_structured_workout("Running", "Zone 2 Endurance", rec_load, user_profile, day_habit["weekday_name"], sim_acwr)
                alt2 = build_structured_workout("Swimming", "Cross-Training", rec_load * 0.8, user_profile, day_habit["weekday_name"], sim_acwr)

        p_load = primary["target_load"]
        sim_acute = p_load * alpha_a + sim_acute * (1.0 - alpha_a)
        sim_chronic = p_load * alpha_c + sim_chronic * (1.0 - alpha_c)
        next_acwr = sim_acute / sim_chronic if sim_chronic > 0 else 0.0

        recommendations.append({
            "day_index": i,
            "date": target_date.strftime("%Y-%m-%d"),
            "weekday": WEEKDAYS[weekday_idx],
            "primary": primary,
            "alt1": alt1,
            "alt2": alt2,
            "modality": primary["modality"],
            "emoji": primary["emoji"],
            "target_load": primary["target_load"],
            "target_duration_mins": primary["duration_mins"],
            "projected_acute": round(sim_acute, 1),
            "projected_chronic": round(sim_chronic, 1),
            "projected_acwr": round(next_acwr, 2),
            "prescription": primary["prescription"],
            "why_recommended": primary["why_recommended"],
            "benefit": primary["benefit"]
        })

    return {
        "current_state": {
            "acute": round(curr_acute, 1),
            "chronic": round(curr_chronic, 1),
            "acwr": round(curr_acwr, 2),
            "acwr_status": classify_acwr_zone(curr_acwr)
        },
        "recommendations": recommendations,
        "horizon": "Day" if horizon_days == 1 else "Week"
    }
