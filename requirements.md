Product Requirements Document (PRD): Fitness Analytics & Recommendation Agent (BreakawayAI)

This document establishes the concrete product, technical, architectural, and security requirements for the development of BreakawayAI, an intelligent fitness assistant. BreakawayAI analyzes historical training data from CSV files to model fitness progression, generate tailored single-day or weekly workout plans matching established training patterns, and visualize the impact of these plans on a user's fitness trajectory.

1. Executive Summary & Core Value Proposition

Training for endurance and strength requires balancing progressive overload with recovery to maximize performance while minimizing injury risk. Current fitness trackers collect massive volumes of data but rarely translate past behaviors and physiological loads into concrete, structured recommendations for the next day or week.

BreakawayAI bridges this gap by acting as an automated coach. By uploading historical workout data (CSV format), users receive:

Trend Visualizations: A historical view of training volume, intensity, and recovery states.

Adaptive Recommendations: Next-day or full-week training plans that respect established personal patterns (e.g., preference for running on Tuesdays, cycling on Saturdays) and optimal training principles.

Optional Physiological Calibration: Highly personalized metrics (FTP, Max HR, Weight, Running PRs) to calibrate intensity and pacing zones.

Interactive Conversational Chat: A core, mandatory interface to query past data, ask for workout modifications, and talk through training strategies.

Predictive Impact Modeling: Clear visualizations of how fitness metrics (training load, fatigue, fitness, and injury risk) will change if they accept and execute the recommendations.

2. User Experience & UI/UX Requirements

The web user interface must be clean, responsive, modern, and highly focused. Visualizations, personalized metrics, concrete recommendations, and an integrated chat agent form the core of the experience.

2.1 Interface Layout

Split-Screen / Master-Detail Dashboard: A single-page layout optimized for analysis:

Left Panel (Controls, Setup & Metrics):

Drag-and-drop CSV file uploader.

Optional User Profile Inputs: Dropdown/collapsible form to capture Weight, FTP, Max HR, and Running PRs.

Planning Horizon Control: Slider with exactly two states: Plan the Day and Plan the Week.

Primary action button: Recommend.

Center Panel (Primary Output & Visualizations):

Highly readable card presenting the recommended workout(s) with a concise, jargon-free explanation.

Tabbed or side-by-side interactive charts displaying historical training trends and the projected impact of accepting the recommendation.

Right Panel (Conversational Coach Chat - Mandatory Core Feature):

An active, integrated chat interface allowing the user to converse directly with their training data, request workout adjustments, or discuss their progression. This is a non-optional core feature of the UI.

3. Optional User Profile & Physiological Inputs

To deliver professional-grade pacing, power, and heart rate zones, the application must provide an optional configuration interface. If provided, these metrics override system defaults and calibrate all recommendations.

Input Parameter

Data Type

Units / Format

UI Control

Applied Logic / Calibration

Weight

Float

lbs / kg (Toggle switch)

Numeric input + toggle

Used to calculate power-to-weight ratio (W/kg) for cycling activities. Defaults to 75 kg if unspecified.

Functional Threshold Power (FTP)

Integer

Watts (e.g., 250)

Numeric input

Calibrates cycling intensity zones (Zone 1 to Zone 7) based on actual power output. Defaults to 200W if unspecified.

Maximum Heart Rate (Max HR)

Integer

BPM (e.g., 190)

Numeric input

Sets heart rate training zones (Zone 1 to Zone 5) for both running and cycling. Defaults to 185 BPM if unspecified.

Best Effort Running PRs

Fields

Time (HH:MM:SS) for:<br>- 5K<br>- 10K<br>- Half Marathon<br>- Marathon

Grid of text inputs with placeholder formats

Calibrates running pace thresholds and target paces for recommended running workouts using Jack Daniels' VDOT formulas or Riegel's scaling law.

4. Data Model & CSV Ingestion Specifications

The data parser must handle standard fitness export formats, specifically matching the structured column schema provided in the user's dataset.

4.1 Schema Mapping (Based on Input CSV Spec)

The ingestion engine must parse the following explicit columns:

Column Header

Data Type

Sample Value

Parsing & Normalization Logic

id

String

"i165961646"

Unique activity identifier.

Type

String

"Ride", "Run", "VirtualRide", "TrailRun", "Hike", "WeightTraining"

Normalizes categories to: Cycling (Ride, VirtualRide), Running (Run, TrailRun), Hiking (Hike), Strength (WeightTraining), or Rest.

Date

DateTime

"2026-07-15T07:32:57"

ISO 8601 timestamp. Extract calendar date for time-series alignment.

Distance

Float

28765.779296875

Distance in meters. Convert to kilometers (val / 1000) or miles based on regional preference.

Moving Time

Integer

3265

Duration in seconds. Convert to formatted string (HH:MM:SS) or minutes for load calculations.

Avg HR

Integer

176

Average heart rate in beats per minute (BPM).

Norm Power

Integer

219

Normalized Power (NP) in Watts (Cycling specific).

Avg Power

Integer

197

Average Power in Watts (Cycling specific).

Intensity

Float

84.55598449707

Normalized intensity factor expressed as a percentage of FTP.

Load

Integer

65

Training Stress Score / Training Load value directly calculated by the capturing system.

FTP

Integer

259

Historical FTP value recorded at the time of the workout.

GAP

Float

3.26275563240

Grade Adjusted Pace in meters per second (Running specific).

Resting HR

Integer

48

Resting heart rate in BPM.

RPE

Integer

7

Rate of Perceived Exertion (scale 1–10).

4.2 Ingestion & Fallback Logic

Primary Load Metric: The system must prioritize the Load column directly from the CSV as the absolute measure of training stress (daily training load).

Fallback Load Calculation: If the Load column is empty or missing for a given row:

For Cycling: If Norm Power, FTP, and Moving Time (seconds) exist:
$$\text{Load} = \left( \frac{\text{Moving Time} \times \text{Norm Power} \times \text{Intensity}}{3600 \times \text{FTP}} \right) \times 100$$

For Running / Other: If Avg HR, Resting HR (or default 60), Max HR (or default 190), and Moving Time exist, use TRIMP calculation:
$$\text{TRIMP} = \text{Duration (mins)} \times \Delta\text{HR Ratio} \times 0.64e^{(1.92 \times \Delta\text{HR Ratio})}$$
Where $\Delta\text{HR Ratio} = \frac{\text{Avg HR} - \text{Resting HR}}{\text{Max HR} - \text{Resting HR}}$.

Absolute Fallback: If physiological metrics are completely missing, estimate load using RPE and duration:
$$\text{Load} = \text{Duration (mins)} \times \text{RPE} \times 0.15$$

Timeline Continuity: The parser must identify dates with no entries and automatically insert a virtual "Rest" row with a Load value of 0 to keep time-series calculations consistent.

5. Computational Analysis & Recommendation Engine

The engine pairs sports science thresholds with behavioral constraint mapping to build hyper-personalized training paths.

5.1 Training State Math (ACWR via Exponential Moving Averages)

Instead of simple rolling averages, the system uses exponentially weighted moving averages (EWMA) to calculate the Acute:Chronic Workload Ratio (ACWR), prioritizing recent fatigue:

Acute Workload (Fatigue - $\lambda_a = 7$ days):
$$\text{Acute}_t = \text{Load}t \times \left(\frac{2}{\lambda_a + 1}\right) + \text{Acute}{t-1} \times \left(1 - \frac{2}{\lambda_a + 1}\right)$$

Chronic Workload (Fitness - $\lambda_c = 28$ days):
$$\text{Chronic}_t = \text{Load}t \times \left(\frac{2}{\lambda_c + 1}\right) + \text{Chronic}{t-1} \times \left(1 - \frac{2}{\lambda_c + 1}\right)$$

ACWR Metric:
$$\text{ACWR}_t = \frac{\text{Acute}_t}{\text{Chronic}_t}$$

5.2 Safe Training Zones & Target Optimization

Optimal Training Stress ("Sweet Spot"): $0.8 \le \text{ACWR} \le 1.3$

Overtraining Risk ("Danger Zone"): $\text{ACWR} \ge 1.5$

Deconditioning Zone ("Under-training"): $\text{ACWR} < 0.8$

The Optimization Goal: Generate a single-day or weekly schedule whose total sum load targets a future ACWR of exactly 1.15 (the midpoint of the sweet spot), while never allowing any single day's acute transition to breach $1.4$.

5.3 Behavioral Habit Matching (Constraints Engine)

To prevent generating plans that users will reject (e.g., suggesting a 3-hour cycle on a Tuesday morning), the engine builds a habits profile using the trailing 60 days of uploaded data:

Modality-to-Day Mapping: Calculates probability distributions for each day of the week.

Example: If Tuesdays have 8 runs out of 8 active days, $P(\text{Run} \mid \text{Tuesday}) = 1.0$.

Duration & Load Affinities: Computes the mean and standard deviation of Moving Time and Load for each weekday.

Example: Saturdays show $\mu_{\text{load}} = 120$ (Long rides), Tuesdays show $\mu_{\text{load}} = 45$ (Short recovery runs).

Active/Rest Regularity: Maps standard patterns of rest (e.g., Monday is consistently a rest day with Load = 0).

5.4 Recommendation Generation Workflow

┌────────────────────────────────────────────────────────┐
│               Calculate Current State                  │
│       Compute baseline Acute, Chronic, and ACWR        │
└──────────────────────────┬─────────────────────────────┘
                           ▼
┌────────────────────────────────────────────────────────┐
│           Determine Target Progression Load            │
│  Find load targets that place ACWR in the 0.8-1.3 zone │
└──────────────────────────┬─────────────────────────────┘
                           ▼
┌────────────────────────────────────────────────────────┐
│             Apply Behavioral Constraints               │
│ Match day of week habits (runs on Tue, rides on Sat)   │
└──────────────────────────┬─────────────────────────────┘
                           ▼
┌────────────────────────────────────────────────────────┐
│              Physiological Target Check                │
│    Is ACWR > 1.5? Force rest day / active recovery     │
│    Is ACWR < 0.8? Scale up duration within habit caps   │
└──────────────────────────┬─────────────────────────────┘
                           ▼
┌────────────────────────────────────────────────────────┐
│           Generate Concrete Workout Parameters         │
│  Convert targets to specific pacing/power prescriptions│
└────────────────────────────────────────────────────────┘


6. Conversational Training Coach Chat (Mandatory Core Feature)

The chatbot is a prominent, fully integrated component of the application. It acts as an interactive bridge between the static PRD calculations and the user's daily reality. It is a mandatory, core architectural layer.

6.1 Technical Requirements

Contextual Awareness: The LLM powering the chatbot must be injected with system prompt context containing:

The parsed historical training metrics (current Acute, Chronic, ACWR, resting heart rate trends).

The generated single-day or weekly workout recommendation.

The optional profile metrics (Weight, FTP, Max HR, Running PRs) if configured.

Two-Way Dynamic Manipulation: The chat is not read-only. It must support downstream command updates:

Scenario: User says, "I'm feeling really sore today, make tomorrow's workout easier."

Action: The chat agent captures this intent, issues an API parameter shift (e.g., reduces target load by $30%$), triggers a regeneration of the day/week recommendation, and updates the Plotly visualizations to reflect the adjusted path.

6.2 Key Interaction Capabilities

Data Explanations: Answer complex retrospective queries (e.g., "How does my training intensity over the last two weeks compare to early June?").

Alternative Recommendations: Negotiate workouts (e.g., "I can't ride outside on Saturday due to rain. Can you swap it for an indoor VirtualRide or a run that matches the same target load?").

Physiological Education: Answer training philosophy questions (e.g., "Why did you flag my training path as high risk when my ACWR hit 1.6?").

7. Visualizations & Predictive Modeling

Graphs must transition smoothly from historical realities to simulated futures, allowing real-time interactive adjustments.

                    HISTORICAL VALUES             │      PROJECTED PREDICTIONS
                                                  │
   Training Stress (Load)                         │  [ ] Show Recommendation Impact
        ▲                                         │
        │              ● (Ride, Load: 123)        │       - - - ● (Recommended Run, Load: 45)
        │             / \                         │     -
        │     ●      /   \                        │   -
        │    / \    /     \                       │ -
        │---●---●--●-------●----------------------│─────────────────────────────►
        │  /     \/         \                     │
        │                                         │
        └─────────────────────────────────────────┴─────────────────────────────►
                                            Current Date                        Time


7.1 Interactive Plotly Specifications

Dual-Zone Timeline Display:

Split the horizontal time-axis into two distinct regions using a vertical dashed marker labeled Current Date.

Left Region (Historical): Solid, interactive lines displaying historical Acute Load, Chronic Load, and individual activity markers (colored dots distinguishing running, cycling, hiking, and strength). Hovering over a dot reveals specific performance stats (e.g., "Cambridge Road Cycling: 59.6km, Avg HR: 152, Load: 123").

Right Region (Projected): Dashed lines projecting the training trajectory over the next 1 to 7 days.

Target ACWR Envelope:

Add shaded background bounding bands across the entire timeline chart:

Light Green Shading: $0.8 \le \text{ACWR} \le 1.3$ (Sweet Spot).

Light Red Shading: $\text{ACWR} \ge 1.5$ (Danger Zone).

Real-Time "What-If" Projections:

Provide an interactive slider on the UI to scale recommended training volume/intensity ($50%$ to $150%$).

As the user drags the slider, the backend recalculates the future daily loads, and the dashed projection line on the Plotly chart dynamically bends and updates in real-time.

8. Agent Architecture & Organization

The application utilizes a tri-agent cooperative system managed via a shared state model to handle user interactions and mathematical modeling.

                    ┌────────────────────────┐
                    │   Orchestrator Agent   │
                    │ (Supervisor & Router)  │
                    └──────────┬───▲─────────┘
                               │   │
             ┌─────────────────┴───┴─────────────────┐
             │                                       │
    ┌────────▼──────────────┐               ┌────────▼──────────────┐
    │ Data & Analyst Agent  │               │      Coach Agent      │
    │ (Pandas & Math Engine)│               │  (Conversational LLM) │
    └───────────────────────┘               └───────────────────────┘


Orchestrator Agent (Supervisor):

Manages the global state and user-interface flow (e.g., Streamlit framework).

Directs incoming inputs (CSV uploads, user profile changes, or raw chat messages) to the appropriate specialty agent.

Intercepts structured commands emitted by the Conversational LLM to adjust mathematical variables.

Data & Analyst Agent (Computational Engine):

An automated, non-LLM algorithmic agent that runs the pandas parsing pipeline.

Calculates TRIMP, RPE load approximations, Acute Load, Chronic Load, and ACWR.

Extracts behavioral habit matrices (preferred weekday modalities).

Computes optimization curves to hit the sweet-spot training zone ($1.15$ ACWR).

Coach Agent (Conversational LLM):

An LLM interface tasked with translating user needs into structured application changes and translating complex physiological telemetry into easily understood training guidance.

Operates with continuous system context (read-only snapshots of the user's workload graphs).

Emits structured commands (e.g., JSON schemas) back to the supervisor to dynamically alter scheduling computations.

9. Hosting, Security, & Compliance (Argolis Target)

To run successfully within the Google Argolis demonstration sandbox, the application must adhere to strict enterprise security standards:

Data Minimization & Ephemeral Lifecycle:

Uploaded CSVs are processed completely within the ephemeral memory space of the container (via Streamlit's st.file_uploader buffer). No files are written to physical disks, local volume mounts, or databases.

All user profile calibrations (FTP, Max HR, running PRs) are stored in the memory-bound Streamlit session_state and erased when the user closes their browser window.

Secret Management:

All external API credentials (e.g., Vertex AI endpoints, Gemini API keys) are accessed via Google Cloud Secret Manager at runtime.

Hardcoded keys, environment files (.env) in source control, or unencrypted container variables are strictly prohibited.

Deployment & Access Controls:

The container is compiled using a hardened, secure base image (e.g., Alpine or Python-slim) to minimize package vulnerabilities.

Deployments on Cloud Run must be locked down behind Google Cloud Identity-Aware Proxy (IAP) to ensure only authorized internal Google employees/demonstrators can access the application endpoint.

Argolis Pre-Deployment Checklist

Ensure st.file_uploader uses in-memory streams only.

Connect Python Secret Manager SDK to pull external API tokens.

Dockerfile contains no ENV declarations containing access keys.

Configure the Cloud Run service to require IAP authentication.

10. Development Milestones & Checkpoint Roadmap

To ensure development velocity is decoupled from LLM complexities, the implementing agent (Antigravity) must follow a strict, milestone-driven delivery cycle.

┌──────────────────────────────────────┐
│  MILESTONE 1: Barebones MVP (Check)  │
│  - CSV parsing and load fallbacks    │
│  - Static Plotly historical trends   │
│  - Pure algorithmic recommendation   │
│  - No chatbot, no LLM connection     │
└──────────────────┬───────────────────┘
                   │
                   ▼
┌──────────────────────────────────────┐
│   MILESTONE 2: Core UX & Profiles    │
│  - User profile form calibrations    │
│  - Real-time "What-If" scale slider  │
│  - Interactive projected timeline    │
└──────────────────┬───────────────────┘
                   │
                   ▼
┌──────────────────────────────────────┐
│  MILESTONE 3: Chatbot Integration    │
│  - Context-injected LLM chat panel   │
│  - Two-way command parsing engine    │
│  - Argolis deployment preparations   │
└──────────────────────────────────────┘


10.1 Milestone 1 Checkpoint Requirements (Barebones MVP Check-In)

Before implementing complex features (like the Chat Coach or the "What-If" slider), a fully functional, barebones baseline must be deployed and tested. This checkpoint is considered passing when:

CSV Ingestion Validation: A user can upload the sample i374510_activities.csv file without errors. The application parses the column headers, recognizes the activity types, and parses the timestamps.

Telemetry Calculation: The system calculates and displays the baseline Acute Load, Chronic Load, and current ACWR for the final recorded date in the CSV (e.g., 2026-07-15T07:32:57).

Historical Visualization: The application renders a basic Plotly chart containing the historical Acute and Chronic lines up to the final date. No projections are necessary yet.

Algorithmic Recommendations: The system displays a static, algorithmically generated text block containing the "Next Day" and "Next Week" recommendations based solely on habit-matching and the optimal ACWR target (1.15).

No LLM dependencies: The chat panel must be completely absent, and there are no network dependencies on Vertex AI or Gemini API keys. This guarantees that the core calculations are sound before integrating conversational agents.

10.2 Milestone 1 Verification Protocol (Passing Test Cases)

Test Step

Inputs

Expected Output

Verification Status

TC-1.1: CSV Upload

Upload i374510_activities.csv

File accepted; web app displays "Parsed 51 activities successfully."

Pending Dev

TC-1.2: State Metrics

Ingest complete CSV

Displays exact final day metrics: Acute Load, Chronic Load, and ACWR.

Pending Dev

TC-1.3: Plotly Render

Render Time-Series Chart

Plotly canvas renders with a line for Acute Load (7-day EWMA) and Chronic Load (28-day EWMA).

Pending Dev

TC-1.4: Algorithmic Recs

Trigger Recommendation

Recommendation engine outputs next day workout (e.g., "Running, Target Load: 45, Target Duration: ~30 mins") matching past patterns.

Pending Dev

11. Functional Implementation Checklist

This checklist serves as the absolute target list of deliverables for the Antigravity agent to begin construction:

Data Parser Module (parser.py):

Parse the specific historical CSV columns.

Support auto-conversion from meters to kilometers and seconds to active minutes.

Verify the existence of the direct Load column, defaulting to heart rate or RPE calculations if unavailable.

Physiological Engine (physiology.py):

Implement exponentially weighted moving average formulas for Acute and Chronic workloads.

Implement ACWR calculation.

Calculate user training zones utilizing optional profile metrics (Weight, FTP, Max HR, and Running PRs).

Habits Profiler (habits.py):

Evaluate trailing 60 days of historical data to generate day-of-week probability matrices for sport type (modality), duration, and typical training stress.

Recommendation Optimizer (optimizer.py):

Determine the optimal total workload path to keep target ACWR between $0.8$ and $1.3$.

Produce 1-day or 7-day recommended schedules matching baseline habits, forcing rest days if current ACWR exceeds safety boundaries.

Interactive UI Builder (app.py):

Build the Streamlit master-detail layout containing the profile forms, planning toggles, recommendation cards, and Plotly visualization frames.

Integrate interactive sliders to test scaled training load projections.

Conversational Coach Chat (chat.py):

Construct the active, non-optional chat panel.

Connect user chat intents directly back to the physical model parameter controls (allowing real-time rest requests or schedule modifications).
