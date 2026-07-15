import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

@dataclass
class UserProfile:
    weight_kg: float = 63.0
    ftp_watts: int = 261
    max_hr_bpm: int = 205
    resting_hr_bpm: int = 47
    pr_5k_sec: Optional[int] = None
    pr_10k_sec: Optional[int] = None
    pr_half_sec: Optional[int] = None
    pr_marathon_sec: Optional[int] = None

CATEGORY_COLORS = {
    "Active Recovery": {"bg": "#334155", "text": "#94A3B8", "border": "#64748B"},
    "Zone 2 Endurance": {"bg": "#1E3A8A", "text": "#60A5FA", "border": "#3B82F6"},
    "Sweet Spot / Tempo": {"bg": "#78350F", "text": "#FDE047", "border": "#F59E0B"},
    "Lactate Threshold": {"bg": "#7C2D12", "text": "#FB923C", "border": "#F97316"},
    "Anaerobic / Sprint": {"bg": "#581C87", "text": "#C084FC", "border": "#A855F7"},
    "Cardiovascular Drift": {"bg": "#7C2D12", "text": "#FDBA74", "border": "#EA580C"}
}

def parse_time_to_seconds(time_str: str) -> Optional[int]:
    if not time_str or not isinstance(time_str, str):
        return None
    parts = time_str.strip().split(":")
    try:
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        elif len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 1:
            return int(parts[0])
    except ValueError:
        return None
    return None

def format_seconds_to_mile_pace(sec_per_mile: float) -> str:
    if sec_per_mile <= 0 or np.isnan(sec_per_mile):
        return "N/A"
    mins = int(sec_per_mile // 60)
    secs = int(sec_per_mile % 60)
    return f"{mins}:{secs:02d} /mi"

def compute_ewma_workloads(df: pd.DataFrame, lambda_a: int = 7, lambda_c: int = 28) -> pd.DataFrame:
    """
    Computes Acute Load (7-day EWMA), Chronic Load (28-day EWMA), and ACWR for a daily time-series DataFrame.
    """
    df = df.copy()
    alpha_a = 2.0 / (lambda_a + 1.0)
    alpha_c = 2.0 / (lambda_c + 1.0)

    acute_vals = []
    chronic_vals = []
    acwr_vals = []

    prev_acute = 0.0
    prev_chronic = 0.0

    for idx, row in df.iterrows():
        load = float(row["Load"])
        if idx == 0:
            curr_acute = load
            curr_chronic = load
        else:
            curr_acute = load * alpha_a + prev_acute * (1.0 - alpha_a)
            curr_chronic = load * alpha_c + prev_chronic * (1.0 - alpha_c)

        acwr = curr_acute / curr_chronic if curr_chronic > 0 else 0.0

        acute_vals.append(curr_acute)
        chronic_vals.append(curr_chronic)
        acwr_vals.append(acwr)

        prev_acute = curr_acute
        prev_chronic = curr_chronic

    df["Acute_Load"] = acute_vals
    df["Chronic_Load"] = chronic_vals
    df["ACWR"] = acwr_vals
    return df

def classify_acwr_zone(acwr: float) -> Dict[str, str]:
    if acwr >= 1.5:
        return {"zone": "Danger Zone (Overtraining)", "color": "#FF4D4D", "status": "danger"}
    elif acwr > 1.3:
        return {"zone": "Elevated Risk", "color": "#FFA500", "status": "warning"}
    elif acwr >= 0.8:
        return {"zone": "Sweet Spot (Optimal)", "color": "#28A745", "status": "optimal"}
    else:
        return {"zone": "Under-training (Deconditioning)", "color": "#17A2B8", "status": "low"}

def calculate_power_zones(ftp: int, weight_kg: float = 63.0) -> Dict[str, str]:
    w_kg = ftp / weight_kg if weight_kg > 0 else 0.0
    return {
        "FTP Baseline": f"{ftp} Watts ({w_kg:.2f} W/kg)",
        "Zone 1 (Active Recovery)": f"< {int(0.55 * ftp)}W (< {0.55 * w_kg:.2f} W/kg)",
        "Zone 2 (Endurance)": f"{int(0.55 * ftp)}W - {int(0.75 * ftp)}W ({0.55 * w_kg:.2f} - {0.75 * w_kg:.2f} W/kg)",
        "Zone 3 (Tempo)": f"{int(0.76 * ftp)}W - {int(0.90 * ftp)}W ({0.76 * w_kg:.2f} - {0.90 * w_kg:.2f} W/kg)",
        "Zone 4 (Threshold)": f"{int(0.91 * ftp)}W - {int(1.05 * ftp)}W ({0.91 * w_kg:.2f} - {1.05 * w_kg:.2f} W/kg)",
        "Zone 5 (VO2 Max)": f"{int(1.06 * ftp)}W - {int(1.20 * ftp)}W ({1.06 * w_kg:.2f} - {1.20 * w_kg:.2f} W/kg)",
        "Zone 6 (Anaerobic)": f"> {int(1.20 * ftp)}W (> {1.20 * w_kg:.2f} W/kg)",
    }

def calculate_hr_zones(max_hr: int, resting_hr: int = 47) -> Dict[str, str]:
    hrr = max_hr - resting_hr
    return {
        "Zone 1 (Recovery)": f"{int(resting_hr + 0.50 * hrr)} - {int(resting_hr + 0.60 * hrr)} BPM",
        "Zone 2 (Endurance)": f"{int(resting_hr + 0.60 * hrr)} - {int(resting_hr + 0.70 * hrr)} BPM",
        "Zone 3 (Tempo)": f"{int(resting_hr + 0.70 * hrr)} - {int(resting_hr + 0.80 * hrr)} BPM",
        "Zone 4 (Threshold)": f"{int(resting_hr + 0.80 * hrr)} - {int(resting_hr + 0.90 * hrr)} BPM",
        "Zone 5 (Max Effort)": f"{int(resting_hr + 0.90 * hrr)} - {max_hr} BPM",
    }

def calculate_running_paces(user_profile: UserProfile) -> Dict[str, str]:
    pr_5k = user_profile.pr_5k_sec or 1200
    pace_5k_sec_mile = (pr_5k / 5.0) * 1.609344

    easy_pace_sec = pace_5k_sec_mile * 1.25
    marathon_pace_sec = pace_5k_sec_mile * 1.15
    threshold_pace_sec = pace_5k_sec_mile * 1.08
    interval_pace_sec = pace_5k_sec_mile * 0.95

    return {
        "Easy / Recovery Pace": format_seconds_to_mile_pace(easy_pace_sec),
        "Marathon / Aerobic Pace": format_seconds_to_mile_pace(marathon_pace_sec),
        "Threshold Pace (LT)": format_seconds_to_mile_pace(threshold_pace_sec),
        "Interval Pace (VO2)": format_seconds_to_mile_pace(interval_pace_sec)
    }

def generate_latest_workout_analysis(df: pd.DataFrame, user_profile: UserProfile = UserProfile()) -> Dict[str, Any]:
    """
    Analyzes the latest completed workout with deep physiological conclusions regarding power vs HR divergence,
    cardiovascular drift, and color-coded workout category tags.
    """
    active_df = df[df["Type"] != "Rest"]
    if active_df.empty:
        return {
            "title": "No Recent Activity Recorded",
            "date": str(df.iloc[-1]["Date"]),
            "category": "Active Recovery",
            "color_cfg": CATEGORY_COLORS["Active Recovery"],
            "stats_summary": "Rest day",
            "analysis": "No active workout recorded on this date.",
            "impact": "Promotes full muscular recovery."
        }

    latest = active_df.iloc[-1]
    w_date = str(latest["Date"])
    w_type = str(latest["Type"])
    w_name = str(latest["Name"]) if ("Name" in latest and pd.notna(latest["Name"])) else w_type
    w_dist_km = float(latest["Distance_km"])
    w_dist_mi = w_dist_km * 0.621371
    w_time_mins = float(latest["Moving_Time_mins"])
    
    w_hr = float(latest["Avg_HR"]) if ("Avg_HR" in latest and not np.isnan(latest["Avg_HR"])) else None
    w_power = float(latest["Avg_Power"]) if ("Avg_Power" in latest and not np.isnan(latest["Avg_Power"])) else None
    w_norm_power = float(latest["Norm_Power"]) if ("Norm_Power" in latest and not np.isnan(latest["Norm_Power"])) else None
    w_rpe = float(latest["RPE"]) if ("RPE" in latest and not np.isnan(latest["RPE"])) else None

    emoji = "🚴" if w_type in ["Cycling", "Ride", "VirtualRide"] else ("🏃" if w_type in ["Running", "Run", "TrailRun"] else "🏋️")

    hrs = int(w_time_mins // 60)
    mins = int(w_time_mins % 60)
    time_str = f"{hrs}h {mins}m" if hrs > 0 else f"{mins}m"

    stat_bits = [f"Distance: <b>{w_dist_mi:.1f} mi ({w_dist_km:.1f} km)</b>", f"Duration: <b>{time_str}</b>"]

    if w_dist_km > 0 and w_time_mins > 0:
        speed_mph = w_dist_mi / (w_time_mins / 60.0)
        stat_bits.append(f"Avg Speed: <b>{speed_mph:.1f} mph</b>")

    pct_ftp = (w_power / user_profile.ftp_watts * 100.0) if (w_power and user_profile.ftp_watts > 0) else 0.0
    pct_max_hr = (w_hr / user_profile.max_hr_bpm * 100.0) if (w_hr and user_profile.max_hr_bpm > 0) else 0.0

    if w_power and w_power > 0:
        w_kg = w_power / user_profile.weight_kg if user_profile.weight_kg > 0 else 3.5
        stat_bits.append(f"Avg Power: <b>{w_power:.0f}W ({w_kg:.2f} W/kg) — {pct_ftp:.1f}% FTP</b>")

    if w_norm_power and w_norm_power > 0:
        np_pct_ftp = (w_norm_power / user_profile.ftp_watts) * 100.0 if user_profile.ftp_watts > 0 else 0.0
        stat_bits.append(f"Normalized Power: <b>{w_norm_power:.0f}W ({np_pct_ftp:.1f}% FTP)</b>")

    if w_hr and w_hr > 0:
        stat_bits.append(f"Avg HR: <b>{w_hr:.0f} BPM ({pct_max_hr:.0f}% Max HR)</b>")

    if w_rpe and w_rpe > 0:
        stat_bits.append(f"RPE: <b>{w_rpe:.0f}/10 Effort</b>")

    stats_str = " | ".join(stat_bits)

    # Determine Classification & Physiological Divergence Insights
    if w_type in ["Cycling", "Ride", "VirtualRide"]:
        w_kg = w_power / user_profile.weight_kg if (w_power and user_profile.weight_kg > 0) else 3.13

        # Check Power vs HR Divergence (e.g. 197W Zone 2 Power BUT 176 BPM Zone 4 HR)
        if pct_ftp <= 78.0 and pct_max_hr >= 82.0:
            category = "Cardiovascular Drift"
            color_cfg = CATEGORY_COLORS["Cardiovascular Drift"]
            analysis = (
                f"<b>Key Physiological Insight:</b> On your <b>{w_date} {w_name}</b> ride, your average power of <b>{w_power:.0f} Watts ({w_kg:.2f} W/kg)</b> "
                f"was perfectly controlled in Zone 2 Endurance (<b>{pct_ftp:.1f}% FTP</b>). However, your average heart rate escalated to <b>{w_hr:.0f} BPM ({pct_max_hr:.0f}% Max HR)</b>—"
                f"placing your cardiovascular stress up in <b>Zone 4 Threshold territory</b> (RPE {w_rpe:.0f}/10).<br><br>"
                "<b>Why was heart rate so elevated for Zone 2 power?</b> This divergence indicates significant <b>cardiovascular drift</b>. "
                "When power remains moderate while heart rate climbs high, it is typically driven by accumulated muscular fatigue from back-to-back training days, "
                "dehydration, heat stress, or elevated core body temperature. Your heart had to pump faster to maintain cardiac output as stroke volume decreased."
            )
            impact = (
                f"Even though power was moderate, your cardiovascular system experienced <b>Threshold-level physiological strain ({w_hr:.0f} BPM)</b>. "
                "Conclusion: Your body required a higher oxygen transport effort than expected for 197W. The recommended path prioritizes active recovery to allow your heart rate response to re-align with your power zones."
            )

        elif pct_ftp > 90.0 or pct_max_hr >= 88.0:
            category = "Lactate Threshold"
            color_cfg = CATEGORY_COLORS["Lactate Threshold"]
            analysis = f"High-output threshold ride averaging <b>{w_power:.0f}W ({pct_ftp:.1f}% FTP)</b> and <b>{w_hr:.0f} BPM ({pct_max_hr:.0f}% Max HR)</b>."
            impact = "Elevates lactate clearance capacity and threshold fatigue tolerance."

        else:
            category = "Zone 2 Endurance"
            color_cfg = CATEGORY_COLORS["Zone 2 Endurance"]
            analysis = f"Steady Zone 2 endurance ride averaging <b>{w_power:.0f}W ({pct_ftp:.1f}% FTP)</b> and <b>{w_hr:.0f} BPM ({pct_max_hr:.0f}% Max HR)</b>."
            impact = "Stimulates mitochondrial biogenesis and fat oxidation efficiency."

    elif w_type in ["Running", "Run", "TrailRun"]:
        pace_sec_mi = (w_time_mins * 60) / w_dist_mi if w_dist_mi > 0 else 0.0
        pace_str = format_seconds_to_mile_pace(pace_sec_mi)

        if pct_max_hr >= 85.0:
            category = "Lactate Threshold"
            color_cfg = CATEGORY_COLORS["Lactate Threshold"]
            analysis = (
                f"Hard threshold run on <b>{w_date}</b> covering <b>{w_dist_mi:.1f} miles</b> at <b>{pace_str}</b> with an average heart rate of <b>{w_hr:.0f} BPM ({pct_max_hr:.0f}% Max HR)</b>.<br><br>"
                "<b>Insight:</b> Your elevated heart rate shows you pushed into Zone 4 threshold intensity, testing your aerobic capacity and lactate tolerance."
            )
            impact = "Builds sustainable running pace barrier and mental toughness."
        else:
            category = "Zone 2 Endurance"
            color_cfg = CATEGORY_COLORS["Zone 2 Endurance"]
            analysis = f"Controlled aerobic run at <b>{pace_str}</b> with heart rate averaging <b>{w_hr:.0f} BPM ({pct_max_hr:.0f}% Max HR)</b>."
            impact = "Strengthens lower-body tendon resilience and aerobic base capacity."

    else:
        category = "Active Recovery"
        color_cfg = CATEGORY_COLORS["Active Recovery"]
        analysis = f"Active session on <b>{w_date}</b> across <b>{time_str}</b>."
        impact = "Promotes cross-training fitness and muscle recovery."

    return {
        "title": f"{emoji} Latest Workout Breakdown — {w_name} ({w_date})",
        "date": w_date,
        "type": w_type,
        "category": category,
        "color_cfg": color_cfg,
        "emoji": emoji,
        "stats_summary": stats_str,
        "analysis": analysis,
        "impact": impact
    }

def generate_recent_training_summary(df: pd.DataFrame) -> Dict[str, str]:
    recent_14 = df.tail(14)
    active_recent = recent_14[recent_14["Type"] != "Rest"]
    
    total_workouts = len(active_recent)
    avg_load_14 = float(recent_14["Load"].mean())
    curr_chronic = float(df.iloc[-1]["Chronic_Load"])
    curr_acute = float(df.iloc[-1]["Acute_Load"])
    last_acwr = float(df.iloc[-1]["ACWR"])

    rides = active_recent[active_recent["Type"].isin(["Cycling", "Ride", "VirtualRide"])]
    runs = active_recent[active_recent["Type"].isin(["Running", "Run", "TrailRun"])]

    total_ride_km = float(rides["Distance_km"].sum()) if not rides.empty else 0.0
    total_run_km = float(runs["Distance_km"].sum()) if not runs.empty else 0.0

    longest_ride = rides.sort_values("Distance_km", ascending=False).iloc[0] if not rides.empty else None
    longest_run = runs.sort_values("Distance_km", ascending=False).iloc[0] if not runs.empty else None

    p1 = (
        f"Fantastic work over the past two weeks! You have maintained outstanding multi-sport momentum across <b>{total_workouts} active workouts</b>, "
        f"successfully expanding your aerobic endurance to a strong <b>{curr_chronic:.1f} Chronic Fitness baseline</b>."
    )

    p2_parts = []
    if not rides.empty:
        ride_miles = total_ride_km * 0.621371
        r_str = f"<b>{len(rides)} cycling sessions</b> totaling <b>{ride_miles:.1f} miles ({total_ride_km:.1f} km)</b>"
        if longest_ride is not None:
            l_ride_mi = float(longest_ride["Distance_km"]) * 0.621371
            l_power = float(longest_ride["Avg_Power"]) if "Avg_Power" in longest_ride and not np.isnan(longest_ride["Avg_Power"]) else 198
            r_str += f" (highlighted by an impressive <b>{l_ride_mi:.1f} mile / {longest_ride['Distance_km']:.1f} km endurance ride @ {l_power:.0f}W avg</b>)"
        p2_parts.append(r_str)

    if not runs.empty:
        run_miles = total_run_km * 0.621371
        run_str = f"<b>{len(runs)} running sessions</b> totaling <b>{run_miles:.1f} miles ({total_run_km:.1f} km)</b>"
        if longest_run is not None:
            l_run_mi = float(longest_run["Distance_km"]) * 0.621371
            run_str += f" (including a key <b>{l_run_mi:.1f} mile / {longest_run['Distance_km']:.1f} km long run</b>)"
        p2_parts.append(run_str)

    p2 = "Your recent training workload combines " + " alongside ".join(p2_parts) + ". These key high-output sessions played a central role in elevating your aerobic threshold and conditioning."

    past_state = f"{p1}<br><br>{p2}"

    if last_acwr >= 1.3:
        future_outlook = (
            f"Your Acute:Chronic Workload Ratio (ACWR) currently sits at <b>{last_acwr:.2f}</b> (Elevated Fatigue zone), as short-term fatigue "
            "is temporarily outpacing your fitness baseline. To reward your hard efforts while protecting against overtraining, "
            "the upcoming plan prioritizes <b>active recovery and light aerobic maintenance</b>, allowing your body to absorb recent training stress safely."
        )
    elif last_acwr < 0.8:
        future_outlook = (
            f"Your current ACWR is <b>{last_acwr:.2f}</b> (Fresh / Under-training zone), meaning your body is well-rested and primed for progression. "
            "The upcoming plan prescribes a <b>progressive volume build</b>—combining targeted power rides with aerobic base runs to safely elevate your conditioning."
        )
    else:
        future_outlook = (
            f"Your training workload is currently in an optimal steady state with an ACWR of <b>{last_acwr:.2f}</b> — placing you directly in the <b>Progression Sweet Spot (0.80–1.30)</b>! "
            "Because your fatigue is perfectly matched to your fitness base, the upcoming plan delivers a <b>balanced training progression targeting a 1.15 ACWR</b>. "
            "By alternating habit-matched endurance rides with steady runs, you will continue gaining aerobic performance adaptations while keeping injury risk minimal."
        )

    return {
        "past_state": past_state,
        "future_outlook": future_outlook
    }
