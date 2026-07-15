import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import os
import io
import asyncio

from app.parser import parse_activities_csv
from app.physiology import (
    compute_ewma_workloads, classify_acwr_zone, calculate_power_zones,
    calculate_hr_zones, calculate_running_paces, parse_time_to_seconds,
    generate_recent_training_summary, generate_latest_workout_analysis, UserProfile
)
from app.habits import analyze_habits
from app.optimizer import generate_recommendations
from app.multi_agent import execute_orchestrated_agent_pipeline

# Page Configuration
st.set_page_config(
    page_title="BreakawayAI",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for Large Legible Typography, Borderless Expander, and Clean Styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Outfit:wght@500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
        font-size: 19px !important;
        line-height: 1.8 !important;
    }

    .stApp {
        background-color: #090D16;
        background-image: 
            radial-gradient(circle at 10% 10%, rgba(245, 158, 11, 0.14) 0%, transparent 40%),
            radial-gradient(circle at 90% 90%, rgba(16, 185, 129, 0.08) 0%, transparent 40%);
    }

    .brand-title {
        font-family: 'Outfit', sans-serif;
        font-size: 52px !important;
        font-weight: 800 !important;
        background: linear-gradient(135deg, #FEF08A 0%, #F59E0B 50%, #D97706 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 4px;
        letter-spacing: -0.5px;
    }

    .date-header {
        font-family: 'Outfit', sans-serif;
        font-size: 24px !important;
        font-weight: 700 !important;
        color: #FEF08A;
        margin-top: 24px;
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        gap: 16px;
    }

    .summary-box {
        background: rgba(245, 158, 11, 0.06);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: none !important;
        border-left: 6px solid #F59E0B !important;
        border-radius: 18px;
        padding: 26px 30px;
        margin-bottom: 24px;
        line-height: 1.8;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
    }

    .summary-header {
        color: #FDE047;
        font-family: 'Outfit', sans-serif;
        font-size: 26px !important;
        font-weight: 700 !important;
        margin-bottom: 14px;
    }

    .summary-section-title {
        font-family: 'Outfit', sans-serif;
        font-size: 20px !important;
        font-weight: 700 !important;
        color: #FEF08A;
        margin-top: 14px;
        margin-bottom: 6px;
    }

    .summary-text {
        font-size: 18px !important;
        color: #F3F4F6;
        line-height: 1.8 !important;
    }

    .latest-stats-bar {
        background: rgba(255, 255, 255, 0.05);
        padding: 12px 18px;
        border-radius: 12px;
        font-size: 17px !important;
        color: #F9FAFB;
        margin-bottom: 16px;
        border: none !important;
    }

    div[data-testid="stExpander"] {
        background: rgba(16, 185, 129, 0.05) !important;
        border: none !important;
        border-left: 6px solid #10B981 !important;
        border-radius: 16px !important;
        box-shadow: none !important;
        margin-bottom: 24px !important;
    }
    div[data-testid="stExpander"] details {
        border: none !important;
    }
    div[data-testid="stExpander"] summary {
        font-family: 'Outfit', sans-serif !important;
        font-size: 26px !important;
        font-weight: 800 !important;
        color: #6EE7B7 !important;
        padding: 18px 22px !important;
        border: none !important;
        cursor: pointer !important;
    }
    div[data-testid="stExpander"] summary:hover {
        color: #A7F3D0 !important;
    }

    div[data-testid="stRadio"] label {
        font-size: 18px !important;
        font-weight: 600 !important;
        color: #F3F4F6 !important;
        padding: 10px 18px !important;
        border-radius: 12px !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        background: rgba(255, 255, 255, 0.04) !important;
        cursor: pointer !important;
        transition: all 0.2s ease !important;
    }
    div[data-testid="stRadio"] label:hover {
        background: rgba(245, 158, 11, 0.2) !important;
        border-color: rgba(245, 158, 11, 0.5) !important;
        color: #FDE047 !important;
    }

    .workout-card {
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: none !important;
        border-left: 5px solid #F59E0B !important;
        padding: 26px;
        border-radius: 18px;
        margin-bottom: 24px;
        transition: all 0.3s ease;
    }
</style>
""", unsafe_allow_html=True)

def load_data(file_source, max_hr=205, resting_hr=47):
    df_parsed = parse_activities_csv(file_source, max_hr_default=max_hr, resting_hr_default=resting_hr)
    df_ewma = compute_ewma_workloads(df_parsed)
    return df_ewma

def main():
    # --- SIDEBAR: Settings & Controls ---
    with st.sidebar:
        st.subheader("⚙️ Settings & Controls")

        uploaded_file = st.file_uploader("Upload Activities CSV", type=["csv"])
        sample_path = "/usr/local/google/home/mileshudgins/sandbox/breakaway-ai/sample_workouts.csv"

        if uploaded_file is not None:
            file_source = uploaded_file
            st.success("Custom CSV uploaded successfully!")
        elif os.path.exists(sample_path):
            file_source = sample_path
            st.info("Using default dataset (`sample_workouts.csv`).")
        else:
            st.warning("Please upload a CSV file to begin.")
            return

        with st.expander("👤 Physiological Profile & Calibrations", expanded=True):
            st.write("**Biometrics (Live Calibrations)**")
            weight_unit = st.radio("Weight Unit", ["kg", "lbs"], horizontal=True, key="weight_unit_select")
            default_wt = 63.0 if weight_unit == "kg" else 138.9
            weight_val = st.number_input("Weight", value=default_wt, key="weight_input")
            weight_kg = weight_val if weight_unit == "kg" else weight_val * 0.453592

            ftp_watts = st.number_input("Functional Threshold Power (FTP Watts)", value=261, key="ftp_input")
            max_hr = st.number_input("Max Heart Rate (BPM)", value=205, key="max_hr_input")
            resting_hr = st.number_input("Resting Heart Rate (BPM)", value=47, key="resting_hr_input")

            st.write("**Best Effort Running PRs (HH:MM:SS or MM:SS)**")
            c_pr1, c_pr2 = st.columns(2)
            pr_5k_str = c_pr1.text_input("5K PR", value="", key="pr_5k")
            pr_10k_str = c_pr2.text_input("10K PR", value="", key="pr_10k")
            pr_half_str = c_pr1.text_input("Half Marathon PR", value="", key="pr_half")
            pr_mar_str = c_pr2.text_input("Marathon PR", value="", key="pr_marathon")

            user_profile = UserProfile(
                weight_kg=float(weight_kg),
                ftp_watts=int(ftp_watts),
                max_hr_bpm=int(max_hr),
                resting_hr_bpm=int(resting_hr),
                pr_5k_sec=parse_time_to_seconds(pr_5k_str),
                pr_10k_sec=parse_time_to_seconds(pr_10k_str),
                pr_half_sec=parse_time_to_seconds(pr_half_str),
                pr_marathon_sec=parse_time_to_seconds(pr_mar_str)
            )

        st.subheader("🎯 Recommendation Horizon")
        horizon = st.radio("Select Horizon", ["Plan the Day", "Plan the Week"], index=0, key="horizon_select")
        horizon_days = 1 if horizon == "Plan the Day" else 7

    # Load Data Ephemerally
    try:
        df = load_data(file_source, max_hr=user_profile.max_hr_bpm, resting_hr=user_profile.resting_hr_bpm)
    except Exception as e:
        st.error(f"Error parsing CSV: {e}")
        return

    # Periodized Computational Analysis
    recs_output = generate_recommendations(df, horizon_days=horizon_days, user_profile=user_profile)
    curr_state = recs_output["current_state"]
    recs = recs_output["recommendations"]
    training_summary = generate_recent_training_summary(df)
    latest_workout = generate_latest_workout_analysis(df, user_profile)

    # Main Single Column View
    st.markdown('<div class="brand-title">BreakawayAI</div>', unsafe_allow_html=True)
    st.caption("Structured multi-sport periodization, physiological progression modeling, and adaptive analytics.")

    # 1. Prominent Glassmorphism Training Summary Card (TOP ITEM)
    past_state_clean = training_summary['past_state'].replace("**", "")
    future_outlook_clean = training_summary['future_outlook'].replace("**", "")

    st.markdown(f"""
    <div class="summary-box">
        <div class="summary-header">📋 Training State & Outlook Summary</div>
        <div class="summary-section-title">Recent Training Context</div>
        <div class="summary-text">{past_state_clean}</div>
        <div class="summary-section-title" style="margin-top: 14px;">Recommended Path</div>
        <div class="summary-text">{future_outlook_clean}</div>
    </div>
    """, unsafe_allow_html=True)

    # 2. Latest Workout Breakdown
    color_cfg = latest_workout["color_cfg"]
    badge_html = f'<span style="background: {color_cfg["bg"]}; color: {color_cfg["text"]}; border: 1px solid {color_cfg["border"]}; padding: 4px 14px; border-radius: 20px; font-weight: 700; font-size: 15px; margin-left: 10px;">{latest_workout["category"]}</span>'
    
    with st.expander(f"{latest_workout['title']}", expanded=False):
        st.markdown(f"""
        <div style="padding: 6px 0px;">
            <div style="margin-bottom: 12px;">Classification: {badge_html}</div>
            <div class="latest-stats-bar">{latest_workout['stats_summary']}</div>
            <div class="summary-section-title">Performance & Exertion Analysis</div>
            <div class="summary-text">{latest_workout['analysis']}</div>
            <div class="summary-section-title" style="margin-top: 14px;">Physiological Impact & Adaptations</div>
            <div class="summary-text">{latest_workout['impact']}</div>
        </div>
        """, unsafe_allow_html=True)

    # Key Metrics Row
    m1, m2, m3 = st.columns(3)

    m1.metric(
        "Acute Load (7-Day Fatigue)",
        f"{curr_state['acute']}",
        help="Recent 7-day average daily fatigue score (e.g. 60 TSS/day ≈ 1 hour of moderate endurance effort per day). Higher numbers reflect higher short-term exertion."
    )

    m2.metric(
        "Chronic Load (28-Day Fitness)",
        f"{curr_state['chronic']}",
        help="28-day baseline aerobic fitness capacity (e.g. 60 TSS/day ≈ 6–7 hours per week aerobic baseline). Higher numbers reflect a stronger overall training foundation."
    )

    status_info = curr_state["acwr_status"]
    acwr_tooltip = (
        "Acute:Chronic Workload Ratio (7-Day Fatigue ÷ 28-Day Fitness baseline).\n\n"
        "• Sweet Spot (0.80 – 1.30): Safe progression zone where short-term fatigue matches baseline fitness.\n"
        "• High Danger (≥ 1.50): Overtraining zone; short-term fatigue is 50%+ higher than your 28-day baseline.\n"
        "• Under-training (< 0.80): Detraining zone; fatigue is 20%+ below your baseline, risking fitness loss."
    )

    m3.metric(
        "Current ACWR",
        f"{curr_state['acwr']}",
        delta=status_info["zone"],
        delta_color="normal" if status_info["status"]=="optimal" else "inverse",
        help=acwr_tooltip
    )

    # --- CLEAN RENAMED CHAT CONSOLE ---
    st.subheader("💬 Ask anything!")
    st.caption("Ask breakaway AI anything related to your training history or goals")

    user_query = st.text_input(
        "Enter your question:",
        placeholder="e.g. What was the highest paced run I've done in the past month?",
        key="adk_agent_query",
        label_visibility="collapsed"
    )

    if user_query:
        with st.spinner("Analyzing your training history..."):
            pipeline_result = asyncio.run(execute_orchestrated_agent_pipeline(
                user_prompt=user_query,
                session_id="streamlit_user_session",
                user_approved=True
            ))

        # Render with explicit HTML styling and bold text tags
        st.markdown(f"""
        <div style="background: rgba(16, 185, 129, 0.08); padding: 20px 24px; border-radius: 16px; border-left: 6px solid #10B981; margin-top: 14px; margin-bottom: 28px;">
            <div style="font-size: 20px; font-weight: 700; color: #6EE7B7; margin-bottom: 8px;">💬 BreakawayAI Coach:</div>
            <div style="font-size: 18px; color: #F3F4F6; line-height: 1.8;">
                {pipeline_result['coaching_response']}
            </div>
        </div>
        """, unsafe_allow_html=True)

    # --- "WHAT'S NEXT?" WORKOUT RECOMMENDATIONS WITH ALTERNATIVE MODALITIES ---
    st.subheader("💡 What's Next?")
    st.caption("Select your preferred modality or training focus below for each day. Selecting an alternative option instantly updates your workout prescription and projected timeline.")

    active_daily_workouts = []

    for idx, rec in enumerate(recs):
        rec_date = rec["date"]
        
        primary = rec["primary"]
        alt1 = rec["alt1"]
        alt2 = rec["alt2"]

        opt_labels = [
            f"Option A (Primary): {primary['emoji']} {primary['title']} — {primary['duration_mins']}m",
            f"Option B (Alternative): {alt1['emoji']} {alt1['title']} — {alt1['duration_mins']}m",
            f"Option C (Alternative): {alt2['emoji']} {alt2['title']} — {alt2['duration_mins']}m"
        ]

        state_key = f"selected_opt_{rec_date}"
        if state_key not in st.session_state:
            st.session_state[state_key] = opt_labels[0]

        # Date Subheader with Greyed-out "What are my zones?" prompt
        st.markdown(f"""
        <div class="date-header">
            <span>🗓️ {rec['date']} ({rec['weekday']})</span>
            <span style="font-size: 16px; font-weight: 600; color: #9CA3AF;">— (What are my zones? See below)</span>
        </div>
        """, unsafe_allow_html=True)

        selected_label = st.radio(
            "Select Workout Focus",
            opt_labels,
            key=f"radio_{rec_date}",
            horizontal=True,
            label_visibility="collapsed"
        )
        st.session_state[state_key] = selected_label

        if selected_label.startswith("Option A"):
            active_w = primary
        elif selected_label.startswith("Option B"):
            active_w = alt1
        else:
            active_w = alt2

        active_daily_workouts.append(active_w)

        # Color-Coded Category Badge for Selected Workout
        w_cfg = active_w["color_cfg"]
        w_badge_html = f'<span style="background: {w_cfg["bg"]}; color: {w_cfg["text"]}; border: 1px solid {w_cfg["border"]}; padding: 4px 14px; border-radius: 20px; font-weight: 700; font-size: 15px; margin-left: 12px;">{active_w["category"]}</span>'

        # Render Periodized Workout Card
        st.markdown(f"""
        <div class="workout-card">
            <h3 style="color: #FDE047; font-family: 'Outfit', sans-serif; margin-bottom: 8px;">
                {rec['date']} ({rec['weekday']}) — {active_w['emoji']} {active_w['title']}
                {w_badge_html}
            </h3>
            <p style="font-size: 18px !important; margin-bottom: 8px;">
                <b>🎯 Exertion & Zone Target:</b> {active_w['prescription']}
            </p>
            <p style="font-size: 18px !important; margin-bottom: 8px;">
                <b>⏱️ Interval Structure:</b> {active_w['interval_structure']}
            </p>
            <p style="font-size: 18px !important; margin-bottom: 8px;">
                <b>⏱️ Duration & Workload:</b> Est. {active_w['duration_mins']} mins | {active_w['target_load']} TSS
            </p>
            <p style="font-size: 18px !important; margin-bottom: 8px;">
                <b>🧠 Why Recommended:</b> {active_w['why_recommended']}
            </p>
            <p style="font-size: 18px !important; margin-bottom: 0px;">
                <b>🔬 Physiological Adaptation:</b> {active_w['benefit']}
            </p>
        </div>
        """, unsafe_allow_html=True)

    # --- "MY ZONES" EXPANDER ---
    with st.expander("📊 My Zones", expanded=False):
        col_pz, col_hrz, col_rp = st.columns(3)
        
        with col_pz:
            st.write("**Cycling Power Zones**")
            pz = calculate_power_zones(user_profile.ftp_watts, user_profile.weight_kg)
            st.table(pd.DataFrame(list(pz.items()), columns=["Zone", "Target Output"]))

        with col_hrz:
            st.write("**Heart Rate Zones**")
            hrz = calculate_hr_zones(user_profile.max_hr_bpm, user_profile.resting_hr_bpm)
            st.table(pd.DataFrame(list(hrz.items()), columns=["Zone", "BPM Range"]))

        with col_rp:
            st.write("**Target Running Paces (min/mi)**")
            rp = calculate_running_paces(user_profile)
            st.table(pd.DataFrame(list(rp.items()), columns=["Target Zone", "Pace (/mi)"]))

    # --- RECALCULATE SIMULATED EWMA TIMELINE BASED ON USER'S SELECTED ALTERNATIVES ---
    alpha_a = 2.0 / (7.0 + 1.0)  # 0.25
    alpha_c = 2.0 / (28.0 + 1.0) # ~0.0689655

    sim_acute = curr_state["acute"]
    sim_chronic = curr_state["chronic"]
    proj_dates = [pd.to_datetime(df["Date"].iloc[-1]).date()]
    proj_acute = [sim_acute]
    proj_chronic = [sim_chronic]

    for idx, rec in enumerate(recs):
        w = active_daily_workouts[idx]
        l = w["target_load"]
        sim_acute = l * alpha_a + sim_acute * (1.0 - alpha_a)
        sim_chronic = l * alpha_c + sim_chronic * (1.0 - alpha_c)
        proj_dates.append(pd.to_datetime(rec["date"]).date())
        proj_acute.append(round(sim_acute, 1))
        proj_chronic.append(round(sim_chronic, 1))

    # --- PROJECTIONS CHART ---
    st.subheader("📈 Projections")

    fig = go.Figure()

    fig.add_hrect(y0=0.8, y1=1.3, fillcolor="#10B981", opacity=0.12, line_width=0)
    fig.add_hrect(y0=1.5, y1=3.0, fillcolor="#F43F5E", opacity=0.12, line_width=0)

    # Historical Lines
    fig.add_trace(go.Scatter(
        x=df["Date"], y=df["Acute_Load"],
        mode="lines", name="Acute Load (7d Fatigue)",
        line=dict(color="#FF3366", width=2.8)
    ))
    fig.add_trace(go.Scatter(
        x=df["Date"], y=df["Chronic_Load"],
        mode="lines", name="Chronic Load (28d Fitness)",
        line=dict(color="#00E5FF", width=2.8)
    ))

    # Activity Marker Dots
    color_map = {"Cycling": "#FF9900", "Running": "#00E5FF", "Hiking": "#10B981", "Strength": "#B388FF", "Rest": "#64748B"}
    active_df = df[df["Type"] != "Rest"]
    fig.add_trace(go.Scatter(
        x=active_df["Date"], y=active_df["Load"],
        mode="markers", name="Recorded Workouts",
        marker=dict(size=9, color=[color_map.get(t, "#FFFFFF") for t in active_df["Type"]]),
        hovertext=[f"{r['Type']} | Dist: {r['Distance_km']:.1f}km | Time: {r['Moving_Time_mins']:.0f}m" for _, r in active_df.iterrows()]
    ))

    # Dynamic Projected Lines
    fig.add_trace(go.Scatter(
        x=proj_dates, y=proj_acute,
        mode="lines+markers", name="Projected Fatigue (Selected Plan)",
        line=dict(color="#FF3366", width=2.5, dash="dash")
    ))
    fig.add_trace(go.Scatter(
        x=proj_dates, y=proj_chronic,
        mode="lines+markers", name="Projected Fitness (Selected Plan)",
        line=dict(color="#00E5FF", width=2.5, dash="dash")
    ))

    # Vertical line for Current Date divider
    last_hist_date = df["Date"].iloc[-1]
    fig.add_vline(x=str(last_hist_date), line_width=2, line_dash="dot", line_color="white", annotation_text="Today")

    x_min_date = (pd.to_datetime(df["Date"].iloc[-1]) - timedelta(days=7)).strftime("%Y-%m-%d")
    x_max_date = str(proj_dates[-1])

    fig.update_layout(
        xaxis=dict(range=[x_min_date, x_max_date], title="Timeline Date"),
        yaxis=dict(title="Training Stress / Load Units"),
        template="plotly_dark",
        height=480,
        margin=dict(l=20, r=20, t=20, b=20)
    )

    st.plotly_chart(fig, use_container_width=True)

if __name__ == "__main__":
    main()
