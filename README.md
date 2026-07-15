# ⚡ BreakawayAI — Multi-Sport Periodization & ADK Agent

> **AI in 5 Days Assessment Agent Submission**  
> **Track**: Concierge / Enterprise / Freestyle  
> **Deployment Target**: Google Cloud Run / Agent Runtime (GCP Project: `sandbox-500619`)

---

## 📌 Problem & Objective

Traditional fitness dashboards track basic Acute:Chronic Workload Ratios (ACWR), but fail to provide structured periodization or meaningful physiological context. A raw load number like `60 TSS` offers no insight into exertion relative to a user's Functional Threshold Power (FTP) or Heart Rate limits, nor does it account for training specificity (Aerobic Base vs. Sweet Spot vs. VO2 Max Intervals).

**BreakawayAI** solves this by delivering an intelligent, adaptive multi-sport periodization assistant that:
1. **Computes EWMA Workload Memory**: Tracks 7-day Acute Fatigue ($\lambda_a=7$) and 28-day Chronic Fitness ($\lambda_c=28$) memory from activity data.
2. **Performs Deep Exertion & Cardiovascular Drift Analysis**: Calculates real-world speed (mph), pace (min/mi), power output (% FTP, W/kg), and heart rate intensity (% Max HR), detecting key phenomena like cardiovascular drift (elevated HR relative to Zone 2 power).
3. **Prescribes Periodized Workout Modalities**: Generates structured daily recommendations across 5 training categories (*Active Recovery, Zone 2 Endurance, Sweet Spot, Lactate Threshold, Anaerobic/Sprint*) with 2 alternative modality options per day.
4. **Interactive Trajectory Projection**: Dynamically updates projected fatigue/fitness curves on a Plotly timeline whenever a user selects an alternative workout.

---

## 🏗️ Repository Structure

```
breakaway-ai/
├── app/                        # ADK Agent Implementation Directory
│   ├── agent.py               # Root ADK Agent, Model routing & System Prompt
│   ├── tools.py               # Explicit @adk.tool functions with JSON Schema docstrings
│   ├── multi_agent.py         # Multi-Agent orchestrator (Coach, Physiology, Guardrail)
│   ├── observability.py       # Structured JSON logging, PII redaction & OpenTelemetry
│   ├── parser.py              # CSV parsing & date timeline aggregator
│   ├── physiology.py          # EWMA math, zone calibrations, HR drift analysis
│   ├── optimizer.py           # Periodized Specificity Engine (3 options/day)
│   └── habits.py              # 60-day trailing habit analyzer
├── app.py                      # Interactive Streamlit Dashboard UI
├── eval/                       # Agent Regression Evaluation Suite
│   ├── eval_dataset.json      # Golden dataset test scenarios
│   └── eval_config.json       # ADK eval configuration
├── infra/                      # Infrastructure as Code (IaC)
│   └── terraform/             # Terraform Cloud Run definitions
│       ├── main.tf
│       ├── variables.tf
│       └── outputs.tf
├── tests/                      # Unit & Integration Test Suite
│   ├── test_parser.py
│   ├── test_physiology.py
│   ├── test_optimizer.py
│   └── test_adk_agent.py
├── Dockerfile                  # Production Cloud Run container specification
├── deploy.sh                   # Cloud Run deployment script
├── requirements.txt            # Python dependencies
└── sample_workouts.csv         # Sample multi-sport activity dataset
```

---

## 🚀 Quick Start & Verification

### Run Automated Unit & ADK Tests
```bash
python3 -m unittest discover tests
```

Output:
```
.............
----------------------------------------------------------------------
Ran 13 tests in 0.295s

OK
```

### Run ADK Playground
```bash
agents-cli playground
```

---

## 📄 License

Apache License 2.0. Developed for the Google AI in 5 Days Assessment.
