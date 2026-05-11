# Patient Flow & Readmission Analytics Dashboard

> An interactive clinical analytics dashboard built on the MIMIC-IV dataset, exploring patient transfer pathways, ED boarding bottlenecks, and 30-day readmission drivers across a large academic medical centre.

---

## Course Information

This project is submitted as part of the coursework for:

**ELEMENTARY DATA LITERACY 2301266**  
Department of Computer Science, Faculty of Science  
Chulalongkorn University

---

## Overview

Hospital operations generate complex, high-dimensional data that is difficult to interpret through static reports alone. This dashboard transforms raw MIMIC-IV clinical event data into interactive visual narratives centred on three research questions:

| # | Research Question |
|---|-------------------|
| **RQ1** | Are complex or ping-pong transfer pathways significantly correlated with the likelihood of patients becoming high-frequency readmissions (Top 5% Frequent Flyers)? |
| **RQ2** | How do system bottlenecks such as emergency room boarding times impact the time to readmission and the rate of patients who need to be readmitted within 30 days? |
| **RQ3** | Considering ICD diagnoses in conjunction with the patient journey sequence, which ICD group is the primary factor in driving readmissions and consuming the most hospital bed resources? |

---

## Dataset

**MIMIC-IV (Medical Information Mart for Intensive Care IV)** is a large, freely available database of de-identified health-related data from patients admitted to Beth Israel Deaconess Medical Center (BIDMC), Boston, MA.

> **Important — Data Privacy Notice:** The original MIMIC-IV dataset requires credentialing via [PhysioNet](https://physionet.org/content/mimiciv/) and is governed by a data use agreement. Raw patient data files are **excluded from this repository** via `.gitignore`. The repository ships with fully **synthetic dummy data** (`app/data/dummy/`) that mirrors the schema and statistical properties of the real dataset, enabling the dashboard to run end-to-end without access to the original data.

### Tables Used

| Parquet File | Source Tables | Key Columns |
|---|---|---|
| `transfers_dummy.parquet` | `transfers` | `subject_id`, `hadm_id`, `intime`, `outtime`, `careunit` |
| `diagnoses_dummy.parquet` | `diagnoses_icd` + `d_icd_diagnoses` | `hadm_id`, `icd_code`, `long_title` |
| `adm_dummy.parquet` | `admissions` + `patients` | `hadm_id`, `admittime`, `edregtime`, `edouttime`, `anchor_age`, `gender` |

---

## Key Features

### Dashboard Tabs

**Overview**
- Interactive chord diagram showing macro-level patient flow between ward groups
- Readmission rate vs. average LOS bubble/scatter chart
- Ping-pong transfer impact on 30-day readmission

**RQ1 — Pathways & Frequent Flyers**
- Ping-pong transition heatmap (ward-to-ward bounce patterns)
- Readmission rate by number of transfers (complexity gradient)

**RQ2 — ED Boarding Bottlenecks**
- ED boarding time vs. 30-day readmission rate (dual-axis)
- Days until readmission by ED boarding bin (box plots)
- ED boarding distribution by admitting unit & readmission status
- Average boarding hours by destination ward

**RQ3 — ICD & Bed Resources**
- Pareto chart of bed days by diagnosis
- ICD × journey complexity readmission heatmap
- Top 10 journey paths leading to readmission
- Average LOS by diagnosis & complexity

### Interactive Filters (applied globally)
- **Diagnosis** — filter by ICD long title (top 50 diagnoses)
- **Age group** — range slider (1–120)
- **Gender** — All / Male / Female
- **Frequent Flyers** — isolate patients in the top 5% transfer-count percentile

---

## Technical Stack

| Layer | Technology |
|---|---|
| Framework | [Dash 2.14](https://dash.plotly.com/) + [Dash Mantine Components 0.12](https://www.dash-mantine-components.com/) |
| Visualisation | [Plotly 5.18](https://plotly.com/python/) + [D3.js 7](https://d3js.org/) (chord diagram) |
| Data processing | [DuckDB 0.9](https://duckdb.org/) (in-process SQL), [Pandas 2.1](https://pandas.pydata.org/) |
| Data format | [Apache Parquet](https://parquet.apache.org/) via PyArrow |
| Production server | [Gunicorn 21.2](https://gunicorn.org/) |
| Containerisation | [Docker](https://www.docker.com/) |

---

## Project Structure

```
mimic_portfolio/
├── app/
│   ├── __init__.py          # package marker
│   ├── main.py              # Dash app init + Gunicorn entry point
│   ├── data.py              # data loading, SQL queries, KPI helpers
│   ├── constants.py         # design system, unit mappings, chord diagram data
│   ├── figures.py           # all chart-builder functions + pre-built figures
│   ├── layout.py            # app.layout definition
│   ├── callbacks.py         # all @app.callback functions
│   └── data/
│       └── dummy/
│           ├── adm_dummy.parquet
│           ├── diagnoses_dummy.parquet
│           └── transfers_dummy.parquet
├── scripts/
│   └── generate_dummy_data.py   # one-time script to regenerate synthetic data
├── .dockerignore
├── .gitignore
├── Dockerfile
└── requirements.txt
```

### Module Responsibilities

```
data.py ──────────────────► constants.py
    │                             │
    └──────────► figures.py ◄─────┘
                    │
                    ▼
    main.py ──► layout.py
       │        callbacks.py
       └──────────────┘
           (registers with app instance)
```

---

## Running Locally

### Prerequisites

- Python 3.11+
- pip

### Setup

```bash
# 1. Clone the repository
git clone https://github.com/<your-username>/mimic_portfolio.git
cd mimic_portfolio

# 2. Create and activate a virtual environment
python -m venv venv
# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. (Optional) Regenerate dummy data
python scripts/generate_dummy_data.py

# 5. Run the development server
python -m app.main
```

The dashboard will be available at `http://localhost:8050`.

---

## Running with Docker

```bash
# Build the image
docker build -t mimic-dashboard .

# Run the container
docker run -p 8050:8050 mimic-dashboard
```

---

## Deploying to Render.com

1. Push this repository to GitHub.
2. On Render.com, create a new **Web Service** and connect your repository.
3. Render will detect the `Dockerfile` automatically and build the container.
4. Set the environment variable `PORT` if needed (Render injects it by default).
5. The app will be live at `https://<your-service>.onrender.com`.

The Gunicorn command used inside the container:

```
gunicorn --workers=2 --bind 0.0.0.0:${PORT:-8050} app.main:server
```

---

## Data Pipeline

```
Parquet files (dummy / real MIMIC-IV)
        │
        ▼
  DuckDB (in-process SQL)
        │
   ┌────┴─────────────────────┐
   │  processed_data          │  ← patient journey + readmission logic
   │  ping_pong_data          │  ← bounce-back transfer detection
   └────┬─────────────────────┘
        │  pandas DataFrames
        ▼
  Plotly figures  →  Dash layout  →  Browser
```

### Core SQL Logic

| Concept | Implementation |
|---|---|
| **Care unit normalisation** | `REGEXP_REPLACE` + `CASE WHEN` to map raw careunit strings to 7 ward groups |
| **Patient journey** | `STRING_AGG(unit, ' → ' ORDER BY intime)` per admission |
| **ED boarding time** | `DATEDIFF('hour', first ED intime, first non-ED intime)` |
| **30-day readmission** | `LEAD(adm_in) OVER (PARTITION BY subject_id ORDER BY adm_in)` |
| **Ping-pong detection** | Return to same unit within 48 h using `LEAD(..., 2)` window |

---

## Design Decisions

| Decision | Rationale |
|---|---|
| **Parquet over CSV** | ~10× faster reads, ~5× smaller files, schema enforcement |
| **DuckDB over pandas** | Complex window functions (LEAD, PARTITION BY) are cleaner in SQL; DuckDB reads Parquet natively |
| **Module split** | Single-responsibility principle — each file has one concern, making the codebase easier to navigate and extend |
| **Pre-built figures** | All 12 charts are rendered at startup; callbacks only re-render on filter change, keeping interaction snappy |
| **Synthetic dummy data** | Allows public GitHub hosting without violating the MIMIC-IV data use agreement |

---

## Acknowledgements

- **MIMIC-IV dataset** — Johnson, A., Bulgarelli, L., Shen, L., Gayles, A., Shammout, A., Horng, S., Pollard, T., Huo, S., Bhatt, D., Moody, B., Gow, B., Wadje, T., Mark, R., & Roger, M. (2023). *MIMIC-IV* (version 2.2). PhysioNet. [https://doi.org/10.13026/6mm1-ek67](https://doi.org/10.13026/6mm1-ek67)
- **D3.js chord diagram** — Mike Bostock & Observable contributors
- **Dash & Plotly** — Plotly Technologies Inc.
