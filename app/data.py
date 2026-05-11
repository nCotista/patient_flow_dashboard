from pathlib import Path

import duckdb
import pandas as pd

DATA_DIR = Path(__file__).parent / "data" / "dummy"
con = duckdb.connect()

try:
    _p = lambda f: (DATA_DIR / f).as_posix()
    con.execute(f"CREATE TABLE transfers AS SELECT * FROM read_parquet('{_p('transfers_dummy.parquet')}')")
    con.execute(f"CREATE TABLE diagnoses AS SELECT * FROM read_parquet('{_p('diagnoses_dummy.parquet')}')")
    con.execute(f"CREATE TABLE adm      AS SELECT * FROM read_parquet('{_p('adm_dummy.parquet')}')")
    DATA_LOADED = True
    print("✓ Data loaded")
except Exception as e:
    print(f"[WARN] Data not found: {e}")
    DATA_LOADED = False

if DATA_LOADED:
    con.execute("""
        CREATE TABLE IF NOT EXISTS processed_data AS
        WITH clean_t AS (
            SELECT subject_id, hadm_id, intime, outtime,
                CASE WHEN lower(careunit) LIKE '%intensive care unit%' THEN 'ICU'
                    ELSE regexp_replace(regexp_replace(
                        split_part(regexp_replace(careunit, '\\s*\\(.*?\\)', '', 'g'), '/', 1),
                        '\\b[Mm]ed\\b', 'Medical', 'g'), '\\s+', ' ', 'g')
                END as unit
            FROM transfers
        ),
        journey_agg AS (
            SELECT subject_id, hadm_id,
                MIN(intime) as adm_in, MAX(outtime) as adm_out,
                COUNT(*) as trans_count,
                string_agg(unit, ' → ' ORDER BY intime) as journey_seq,
                FIRST(unit) as entry_unit
            FROM clean_t GROUP BY 1, 2
        ),
        boarding AS (
            SELECT hadm_id,
                DATEDIFF('hour',
                    MIN(CASE WHEN unit LIKE '%Emergency%' THEN intime END),
                    MIN(CASE WHEN unit NOT LIKE '%Emergency%' THEN intime END)
                ) as boarding_hrs_xfer
            FROM clean_t GROUP BY 1
        ),
        readmit_logic AS (
            SELECT j.*, b.boarding_hrs_xfer,
                LEAD(j.adm_in) OVER (PARTITION BY j.subject_id ORDER BY j.adm_in) as next_in,
                CASE WHEN DATEDIFF('day', j.adm_out,
                    LEAD(j.adm_in) OVER (PARTITION BY j.subject_id ORDER BY j.adm_in)) <= 30
                THEN 1 ELSE 0 END as is_readmit
            FROM journey_agg j LEFT JOIN boarding b ON j.hadm_id = b.hadm_id
        )
        SELECT r.*, dx.long_title as diagnosis,
               DATEDIFF('day', r.adm_in, r.adm_out) as los_days,
               CASE WHEN r.trans_count <= 2 THEN 'Simple (1-2)' ELSE 'Complex (3+)' END as complexity,
               ap.anchor_age as age, ap.gender as gender
        FROM readmit_logic r
        LEFT JOIN diagnoses dx ON r.hadm_id = dx.hadm_id
        LEFT JOIN adm ap ON r.hadm_id = ap.hadm_id
    """)
    df = con.execute("SELECT * FROM processed_data").df()

    con.execute("""
        CREATE TABLE IF NOT EXISTS ping_pong_data AS
        WITH clean_t AS (
            SELECT subject_id, hadm_id, intime, outtime,
                CASE WHEN lower(careunit) LIKE '%intensive care unit%' THEN 'ICU'
                    ELSE regexp_replace(regexp_replace(
                        split_part(regexp_replace(careunit, '\\s*\\(.*?\\)', '', 'g'), '/', 1),
                        '\\b[Mm]ed\\b', 'Medical', 'g'), '\\s+', ' ', 'g')
                END as unit
            FROM transfers
        ),
        seq AS (
            SELECT hadm_id, unit as current_unit, outtime as current_out,
                LEAD(unit,1) OVER(PARTITION BY hadm_id ORDER BY intime) as next_unit,
                LEAD(unit,2) OVER(PARTITION BY hadm_id ORDER BY intime) as return_unit,
                LEAD(intime,2) OVER(PARTITION BY hadm_id ORDER BY intime) as return_in
            FROM clean_t
        )
        SELECT hadm_id, current_unit as from_unit, next_unit as to_unit,
            CASE WHEN current_unit = return_unit
                AND DATEDIFF('hour', current_out, return_in) <= 48 THEN 1 ELSE 0
            END as is_pingpong
        FROM seq
        WHERE next_unit IS NOT NULL AND current_unit != next_unit
    """)
    pp_df = con.execute("SELECT * FROM ping_pong_data").df()

    try:
        dfc = pd.read_parquet(
            DATA_DIR / "adm_dummy.parquet",
            columns=["subject_id", "hadm_id", "admittime", "edregtime", "edouttime"],
        )
        dfc["admittime"]        = pd.to_datetime(dfc["admittime"])
        dfc["edouttime"]        = pd.to_datetime(dfc["edouttime"])
        dfc["boarding_hrs_adm"] = (dfc["edouttime"] - dfc["admittime"]).dt.total_seconds() / 3600
        dfc_ed = dfc.dropna(subset=["boarding_hrs_adm"])
    except Exception:
        dfc_ed = pd.DataFrame()
else:
    df = pp_df = dfc_ed = pd.DataFrame()


# ── KPI helpers ───────────────────────────────────────────────────
def _los_label(source_df: pd.DataFrame) -> str:
    dedup = source_df.drop_duplicates(subset=["hadm_id"])["los_days"].dropna()
    dedup = dedup[dedup.between(0, 365)]
    if dedup.empty:
        return "—"
    return f"Med {dedup.median():.1f} / Avg {dedup.mean():.1f} d"


if not df.empty:
    KPI_TOTAL   = f"{df['hadm_id'].nunique():,}"
    KPI_LOS     = _los_label(df) if "los_days" in df else "—"
    KPI_READMIT = (
        f"{df.drop_duplicates(subset=['hadm_id'])['is_readmit'].mean() * 100:.1f}%"
        if "is_readmit" in df else "—"
    )
    KPI_ED = f"{df['boarding_hrs_xfer'].mean():.1f} hrs" if "boarding_hrs_xfer" in df else "—"
    if not pp_df.empty:
        _pp_hadm = pp_df[pp_df["is_pingpong"] == 1]["hadm_id"].nunique()
        KPI_PP   = f"{_pp_hadm / df['hadm_id'].nunique() * 100:.1f}%"
    else:
        KPI_PP = "—"
else:
    KPI_TOTAL = KPI_LOS = KPI_READMIT = KPI_ED = KPI_PP = "—"

HAS_AGE    = not df.empty and "age"    in df.columns
HAS_GENDER = not df.empty and "gender" in df.columns

if not df.empty and "diagnosis" in df.columns:
    _top_dx = df["diagnosis"].dropna().value_counts().head(50).index.tolist()
    DIAGNOSIS_OPTIONS = [{"label": "All Diagnoses", "value": "all"}] + [
        {"label": d[:60], "value": d} for d in _top_dx
    ]
else:
    DIAGNOSIS_OPTIONS = [{"label": "All Diagnoses", "value": "all"}]
