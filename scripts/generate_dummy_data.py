"""Run once to generate synthetic parquet files for the demo."""
import random
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

random.seed(42)
np.random.seed(42)

OUTPUT_DIR = Path(__file__).parent / "app" / "data" / "dummy"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CAREUNITS = [
    "Emergency Department",
    "Emergency Department Observation",
    "Coronary Care Unit",
    "Trauma SICU",
    "Medicine",
    "Surgery",
    "Cardiac Surgery",
    "Thoracic Surgery",
    "Cardiology",
    "Neurology",
    "Oncology",
    "Psychiatry",
    "Neuro Intermediate",
    "Surgical Intermediate",
    "Labor & Delivery",
    "Obstetrics Antepartum",
    "Obstetrics Postpartum",
]

DIAGNOSES = [
    ("I21.9",   "Acute myocardial infarction, unspecified"),
    ("J18.9",   "Pneumonia, unspecified organism"),
    ("N39.0",   "Urinary tract infection, site not specified"),
    ("I50.9",   "Heart failure, unspecified"),
    ("E11.9",   "Type 2 diabetes mellitus without complications"),
    ("J44.1",   "Chronic obstructive pulmonary disease with acute exacerbation"),
    ("A41.9",   "Sepsis, unspecified organism"),
    ("K92.1",   "Melena"),
    ("I63.9",   "Cerebral infarction, unspecified"),
    ("S72.001A", "Fracture of unspecified part of neck of right femur, initial encounter"),
    ("K35.80",  "Other and unspecified acute appendicitis without abscess"),
    ("N18.3",   "Chronic kidney disease, stage 3 (moderate)"),
    ("I48.91",  "Unspecified atrial fibrillation"),
    ("G40.909", "Epilepsy, unspecified, not intractable, without status epilepticus"),
    ("C34.90",  "Malignant neoplasm of unspecified part of unspecified bronchus and lung"),
    ("Z51.11",  "Encounter for antineoplastic chemotherapy"),
    ("I10",     "Essential (primary) hypertension"),
    ("K70.30",  "Alcoholic cirrhosis of liver without ascites"),
    ("M54.5",   "Low back pain"),
    ("R07.9",   "Chest pain, unspecified"),
]

N_PATIENTS   = 200
N_ADMISSIONS = 400

subjects = list(range(10_000_001, 10_000_001 + N_PATIENTS))
ages    = np.random.randint(18, 90, N_PATIENTS)
genders = np.random.choice(["M", "F"], N_PATIENTS)
patient_info = {s: {"age": int(a), "gender": g} for s, a, g in zip(subjects, ages, genders)}

records_transfers: list[dict] = []
records_diagnoses: list[dict] = []
records_adm:       list[dict] = []

hadm_id  = 20_000_001
base_dt  = datetime(2021, 1, 1)

for _ in range(N_ADMISSIONS):
    subj = random.choice(subjects)
    hid  = hadm_id
    hadm_id += 1

    admit_time = base_dt + timedelta(
        days=random.randint(0, 700), hours=random.randint(0, 23)
    )

    has_ed  = random.random() < 0.55
    ed_reg  = admit_time - timedelta(hours=random.uniform(1, 6)) if has_ed else None
    ed_out  = admit_time + timedelta(hours=random.uniform(0.5, 4)) if has_ed else None

    # Build care journey
    n_tx = random.randint(1, 6)
    journey: list[str] = []
    if has_ed:
        journey.append("Emergency Department")

    main_units = random.choices(
        ["Medicine", "Surgery", "Cardiac Surgery", "Neurology",
         "Cardiology", "Coronary Care Unit", "Oncology", "Psychiatry"],
        weights=[30, 18, 10, 10, 10, 8, 7, 7],
        k=max(1, n_tx - len(journey)),
    )
    journey.extend(main_units)

    # Occasionally add a step-down  /  intermediate unit
    if random.random() < 0.25:
        journey.append(random.choice(["Neuro Intermediate", "Surgical Intermediate"]))

    t_in = admit_time
    for unit in journey:
        t_out = t_in + timedelta(hours=random.uniform(4, 96))
        records_transfers.append({
            "subject_id": subj,
            "hadm_id":    hid,
            "intime":     t_in,
            "outtime":    t_out,
            "careunit":   unit,
        })
        t_in = t_out

    # 1–3 diagnoses per admission
    for icd, title in random.sample(DIAGNOSES, random.randint(1, 3)):
        records_diagnoses.append({
            "hadm_id":    hid,
            "icd_code":   icd,
            "long_title": title,
        })

    records_adm.append({
        "subject_id":  subj,
        "hadm_id":     hid,
        "admittime":   admit_time,
        "edregtime":   ed_reg,
        "edouttime":   ed_out,
        "anchor_age":  patient_info[subj]["age"],
        "gender":      patient_info[subj]["gender"],
    })

df_t = pd.DataFrame(records_transfers)
df_d = pd.DataFrame(records_diagnoses)
df_a = pd.DataFrame(records_adm)

df_t.to_parquet(OUTPUT_DIR / "transfers_dummy.parquet",  index=False)
df_d.to_parquet(OUTPUT_DIR / "diagnoses_dummy.parquet",  index=False)
df_a.to_parquet(OUTPUT_DIR / "adm_dummy.parquet",        index=False)

print(f"✓ transfers : {len(df_t):,} rows → transfers_dummy.parquet")
print(f"✓ diagnoses : {len(df_d):,} rows → diagnoses_dummy.parquet")
print(f"✓ admissions: {len(df_a):,} rows → adm_dummy.parquet")
print(f"  Saved to  : {OUTPUT_DIR}")
