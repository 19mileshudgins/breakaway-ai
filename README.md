# ⚡ BreakawayAI — Multi-Sport Periodization & Physiological Progression Agent

> **AI in 5 Days Assessment Agent Submission**  
> **Track**: Concierge / Enterprise / Freestyle  
> **Deployment Target**: Google Cloud Run (GCP Project: `sandbox-500619`)

---

## 📌 Problem & Objective

Traditional fitness dashboards track basic Acute:Chronic Workload Ratios (ACWR), but fail to provide structured periodization or meaningful physiological context. A raw load number like `60 TSS` offers no insight into exertion relative to a user's Functional Threshold Power (FTP) or Heart Rate limits, nor does it account for training specificity (Aerobic Base vs. Sweet Spot vs. VO2 Max Intervals).

**BreakawayAI** solves this by delivering an intelligent, adaptive multi-sport periodization assistant that:
1. **Computes EWMA Workload Memory**: Tracks 7-day Acute Fatigue ($\lambda_a=7$) and 28-day Chronic Fitness ($\lambda_c=28$) memory from activity data.
2. **Performs Deep Exertion & Cardiovascular Drift Analysis**: Calculates real-world speed (mph), pace (min/mi), power output (% FTP, W/kg), and heart rate intensity (% Max HR), detecting key phenomena like cardiovascular drift (elevated HR relative to Zone 2 power).
3. **Prescribes Periodized Workout Modalities**: Generates structured daily recommendations across 5 training categories (*Active Recovery, Zone 2 Endurance, Sweet Spot, Lactate Threshold, Anaerobic/Sprint*) with 2 alternative modality options per day.
4. **Interactive Trajectory Projection**: Dynamically updates projected fatigue/fitness curves on a Plotly timeline whenever a user selects an alternative workout.

---

## 🏗️ Repository Architecture

```
breakaway-ai/
├── app.py                      # Primary Streamlit Interactive Dashboard UI
├── physiology.py               # EWMA math, zone calibrations, HR drift & exertion analysis
├── optimizer.py                # Periodized Specificity Engine & 3-option workout generator
├── parser.py                   # CSV parser & date continuity pipeline
├── habits.py                   # 60-day trailing habit profiler
├── tests/                      # Standard python test suite
│   ├── test_parser.py          # CSV parsing & timeline continuity tests
│   ├── test_physiology.py      # EWMA, zones, and exertion analysis tests
│   └── test_optimizer.py       # Periodization engine & modality recommendation tests
├── Dockerfile                  # Container specification for Cloud Run deployment
├── deploy.sh                   # One-click deployment script
├── requirements.txt            # Python dependencies
├── submission_frontend/
│   ├── main.py                 # ADK Agent Runtime & FastAPI Manager Approval Service
│   └── pyproject.toml          # FastAPI & ADK dependencies
└── sample_workouts.csv         # Sample multi-sport activities dataset
```

---

## 📊 Core Features & Technical Highlights

### 1. Exponentially Weighted Moving Average (EWMA) Memory
Calculates Acute Load ($A_t$) and Chronic Load ($C_t$) via recursive EWMA smoothing:
$$\alpha_a = \frac{2}{\lambda_a + 1} = 0.25 \quad (\lambda_a = 7 \text{ days})$$
$$\alpha_c = \frac{2}{\lambda_c + 1} \approx 0.069 \quad (\lambda_c = 28 \text{ days})$$
$$\text{ACWR}_t = \frac{A_t}{C_t}$$

### 2. Cardiovascular Drift & Exertion Engine
Detects physiological divergence between mechanical output (Watts / Speed) and internal strain (Heart Rate / RPE). Provides actionable coaching feedback when heart rate drifts into threshold territory during Zone 2 efforts.

### 3. Color-Coded Periodization Categories
- ⚪ **Active Recovery** (`#64748B`): Low-torque spin or light mobility (< 55% FTP / < 60% Max HR).
- 🔵 **Zone 2 Endurance** (`#3B82F6`): Conversational aerobic base building (55%–75% FTP / 60%–75% Max HR).
- 🟡 **Sweet Spot / Tempo** (`#F59E0B`): Sub-threshold aerobic power expansion (88%–94% FTP).
- 🟠 **Lactate Threshold** (`#F97316`): Sustainable pace barrier lifting (91%–105% FTP / Zone 4 HR).
- 🟣 **Anaerobic / Sprint** (`#A855F7`): High-intensity VO2 Max power intervals (> 105% FTP / Zone 5 HR).

---

## 🚀 Quick Start Guide

### Local Development

1. **Clone Repository**:
   ```bash
   git clone https://github.com/<your-username>/breakaway-ai.git
   cd breakaway-ai
   ```

2. **Create Virtual Environment & Install Dependencies**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Run the Streamlit Dashboard**:
   ```bash
   streamlit run app.py
   ```
   Access the dashboard at `http://localhost:8501`.

---

## 🧪 Testing

Run the automated test suite:

```bash
python3 -m unittest discover tests
```

Output:
```
.........
----------------------------------------------------------------------
Ran 9 tests in 0.229s

OK
```

---

## ☁️ Production Deployment (Google Cloud Run)

Deploy to Google Cloud Run targeting GCP Project `sandbox-500619`:

```bash
chmod +x deploy.sh
./deploy.sh
```

---

## 📄 License

Apache License 2.0. Developed for the Google AI in 5 Days Assessment.
