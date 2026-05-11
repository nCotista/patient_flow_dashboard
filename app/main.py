import os
from pathlib import Path
import dash
from dash import dcc, html, Input, Output, State
import dash_mantine_components as dmc
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
import duckdb
import json
from datetime import datetime

# ══════════════════════════════════════════════════════════════════
#  DATA LOADING
# ══════════════════════════════════════════════════════════════════
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
        dfc = pd.read_parquet(DATA_DIR / 'adm_dummy.parquet',
                              columns=['subject_id', 'hadm_id', 'admittime', 'edregtime', 'edouttime'])
        dfc['admittime']        = pd.to_datetime(dfc['admittime'])
        dfc['edouttime']        = pd.to_datetime(dfc['edouttime'])
        dfc['boarding_hrs_adm'] = (dfc['edouttime'] - dfc['admittime']).dt.total_seconds() / 3600
        dfc_ed = dfc.dropna(subset=['boarding_hrs_adm'])
    except Exception:
        dfc_ed = pd.DataFrame()
else:
    df = pp_df = dfc_ed = pd.DataFrame()


# ══════════════════════════════════════════════════════════════════
#  UNIT MAPPING
# ══════════════════════════════════════════════════════════════════
UNIT_MAP = {
    'Emergency Department': 'ED',      'Emergency Department Observation': 'ED Obs',
    'Observation': 'ED Obs',           'ICU': 'ICU',
    'Coronary Care Unit': 'ICU',       'Trauma SICU': 'ICU',
    'Medical': 'Medicine',             'Medicine': 'Medicine',
    'Surgery': 'Surgery / Procedural', 'Cardiac Surgery': 'Surgery / Procedural',
    'Thoracic Surgery': 'Surgery / Procedural', 'Vascular': 'Surgery / Procedural',
    'Transplant': 'Surgery / Procedural', 'PACU': 'Surgery / Procedural',
    'Cardiology': 'Specialist Ward',   'Hematology': 'Specialist Ward',
    'Neurology': 'Specialist Ward',    'Oncology': 'Specialist Ward',
    'Psychiatry': 'Specialist Ward',   'Neuro Intermediate': 'Specialist Ward',
    'Neuro Stepdown': 'Specialist Ward', 'Surgical Intermediate': 'Specialist Ward',
    'Labor & Delivery': 'Maternity',   'Nursery': 'Maternity',
    'Obstetrics': 'Maternity',         'Obstetrics Antepartum': 'Maternity',
    'Obstetrics Postpartum': 'Maternity',
}

UNIT_MAP_DETAIL = {
    'Emergency Department': 'ED',      'Emergency Department Observation': 'ED Obs',
    'Observation': 'ED Obs',           'ICU': 'ICU',
    'Coronary Care Unit': 'ICU',       'Trauma SICU': 'ICU',
    'Medical': 'Medicine',             'Medicine': 'Medicine',
    'Surgery': 'Surgery / Procedural', 'Cardiac Surgery': 'Surgery / Procedural',
    'Thoracic Surgery': 'Surgery / Procedural', 'Vascular': 'Surgery / Procedural',
    'Transplant': 'Surgery / Procedural', 'PACU': 'Surgery / Procedural',
    'Cardiology': 'Cardiology',        'Hematology': 'Hematology',
    'Neurology': 'Neurology',          'Oncology': 'Oncology',
    'Psychiatry': 'Psychiatry',        'Neuro Intermediate': 'Neuro Intermediate',
    'Neuro Stepdown': 'Neuro Stepdown', 'Surgical Intermediate': 'Surgical Intermediate',
    'Labor & Delivery': 'Maternity',   'Nursery': 'Maternity',
    'Obstetrics': 'Maternity',         'Obstetrics Antepartum': 'Maternity',
    'Obstetrics Postpartum': 'Maternity',
}

TARGET_ORDER = ['ED', 'ED Obs', 'ICU', 'Medicine', 'Surgery / Procedural', 'Specialist Ward', 'Maternity']


# ══════════════════════════════════════════════════════════════════
#  DESIGN SYSTEM
# ══════════════════════════════════════════════════════════════════
# Primary palette
C_NAVY   = '#0D1B3E'
C_BLUE   = '#1565C0'
C_TEAL   = '#00695C'
C_ORANGE = '#BF360C'
C_AMBER  = '#E65100'
C_PURPLE = '#4527A0'
C_CYAN   = '#006064'

# KPI accent backgrounds (light tints)
KPI_BG   = ['#E3F2FD', '#E0F2F1', '#FBE9E7', '#FFF3E0', '#EDE7F6']
KPI_FG   = [C_BLUE,    C_TEAL,    C_ORANGE,  C_AMBER,   C_PURPLE]

CHART_H      = 360
CHART_MARGIN = dict(l=10, r=20, t=52, b=20)
CHART_MARGIN_CB = dict(l=10, r=72, t=52, b=20)

_FONT_FAMILY = 'Inter, "Segoe UI", system-ui, -apple-system, sans-serif'

_BUBBLE_BTN_BASE = {
    'position': 'absolute', 'top': '10px', 'right': '12px', 'zIndex': '10',
    'borderRadius': '20px', 'padding': '4px 12px',
    'fontSize': '10px', 'fontWeight': '700',
    'cursor': 'pointer', 'fontFamily': _FONT_FAMILY,
    'letterSpacing': '.04em',
}
_BUBBLE_BTN_ON  = {**_BUBBLE_BTN_BASE, 'background': C_CYAN, 'color': 'white',
                   'border': f'1.5px solid {C_CYAN}', 'boxShadow': '0 2px 6px rgba(0,96,100,.3)'}
_BUBBLE_BTN_OFF = {**_BUBBLE_BTN_BASE, 'background': '#F8FAFC', 'color': '#607D8B',
                   'border': '1.5px solid #B0BEC5', 'boxShadow': '0 1px 3px rgba(0,0,0,.08)'}

def _base_layout(title='', margin=None, hovermode='x unified', colorbar=False, **extra):
    m = (CHART_MARGIN_CB if colorbar else CHART_MARGIN) if margin is None else margin
    return dict(
        font=dict(family=_FONT_FAMILY, size=11, color='#455A64'),
        paper_bgcolor='#FFFFFF',
        plot_bgcolor='#F8FBFF',
        title=dict(
            text=f'<b>{title}</b>' if title else '',
            font=dict(size=13, color='#0D1B3E', family=_FONT_FAMILY),
            pad=dict(b=8),
        ),
        xaxis=dict(
            gridcolor='#EEF2F7', linecolor='#CFD8DC', showgrid=True,
            zeroline=False, tickfont=dict(size=10, color='#607D8B'),
            title_font=dict(size=10, color='#607D8B'),
        ),
        yaxis=dict(
            gridcolor='#EEF2F7', linecolor='#CFD8DC', showgrid=True,
            zeroline=False, tickfont=dict(size=10, color='#607D8B'),
            title_font=dict(size=10, color='#607D8B'),
        ),
        legend=dict(
            bgcolor='rgba(255,255,255,0.96)', bordercolor='#E8EEF4',
            borderwidth=1, font=dict(size=10, color='#546E7A'),
            orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1,
        ),
        hoverlabel=dict(
            bgcolor='#1E2A3A', font_color='#ECF0F1',
            bordercolor='#2C3E50', font_size=11, font_family=_FONT_FAMILY,
        ),
        hovermode=hovermode,
        margin=m,
        height=CHART_H,
        **extra,
    )


# ══════════════════════════════════════════════════════════════════
#  KPI CALCULATIONS
# ══════════════════════════════════════════════════════════════════
def _los_label(source_df):
    dedup = source_df.drop_duplicates(subset=['hadm_id'])['los_days'].dropna()
    dedup = dedup[dedup.between(0, 365)]
    if dedup.empty:
        return '—'
    return f"Med {dedup.median():.1f} / Avg {dedup.mean():.1f} d"


if not df.empty:
    KPI_TOTAL   = f"{df['hadm_id'].nunique():,}"
    KPI_LOS     = _los_label(df) if 'los_days' in df else '—'
    KPI_READMIT = (f"{df.drop_duplicates(subset=['hadm_id'])['is_readmit'].mean()*100:.1f}%"
                   if 'is_readmit' in df else '—')
    KPI_ED      = f"{df['boarding_hrs_xfer'].mean():.1f} hrs" if 'boarding_hrs_xfer' in df else '—'
    if not pp_df.empty:
        _pp_hadm = pp_df[pp_df['is_pingpong'] == 1]['hadm_id'].nunique()
        KPI_PP   = f"{_pp_hadm / df['hadm_id'].nunique() * 100:.1f}%"
    else:
        KPI_PP = '—'
else:
    KPI_TOTAL = KPI_LOS = KPI_READMIT = KPI_ED = KPI_PP = '—'


# ══════════════════════════════════════════════════════════════════
#  GRAPH BUILDERS
# ══════════════════════════════════════════════════════════════════
def empty_fig(msg="No data available"):
    fig = go.Figure()
    fig.add_annotation(
        text=f'<span style="font-size:32px">📊</span><br><br><span style="color:#90A4AE">{msg}</span>',
        xref='paper', yref='paper', x=0.5, y=0.5,
        showarrow=False, font=dict(size=13, family=_FONT_FAMILY),
        align='center',
    )
    fig.update_layout(**_base_layout())
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    return fig


def make_heatmap(_pp=None):
    _pp = pp_df if _pp is None else _pp
    if _pp.empty:
        return empty_fig("Ping-Pong Heatmap — No Data")
    _pp = _pp.copy()
    _pp['from_group'] = _pp['from_unit'].map(UNIT_MAP).fillna('Other')
    _pp['to_group']   = _pp['to_unit'].map(UNIT_MAP).fillna('Other')
    filt = _pp[(_pp['from_group'] != 'Other') & (_pp['to_group'] != 'Other')]
    grp  = filt.groupby(['from_group', 'to_group']).agg(
        pingpong_count=('is_pingpong', 'sum')).reset_index()
    hm   = grp.pivot(index='from_group', columns='to_group',
                     values='pingpong_count').fillna(0)
    hm   = hm.reindex(index=TARGET_ORDER, columns=TARGET_ORDER, fill_value=0)
    fig  = px.imshow(
        hm, text_auto=True, aspect='auto',
        color_continuous_scale=[[0, '#F0F7FF'], [0.4, '#5C9BD6'], [1, '#0D3B6E']],
    )
    fig.update_layout(
        **_base_layout('Ping-Pong Transition Heatmap', hovermode='closest', colorbar=True),
        xaxis_title='To Ward', yaxis_title='From Ward',
        xaxis_tickangle=-30,
        coloraxis_colorbar=dict(
            title=dict(text='Cases', font=dict(size=10)), thickness=12,
            tickfont=dict(size=9), outlinewidth=0,
        ),
    )
    return fig


def make_los_bar(_df=None):
    _df = df if _df is None else _df
    if _df.empty:
        return empty_fig("Avg LOS by Diagnosis — No Data")
    top_dx = _df['diagnosis'].value_counts().head(8).index
    agg = (_df[_df['diagnosis'].isin(top_dx)]
           .groupby(['diagnosis', 'complexity'])['los_days']
           .mean().reset_index()
           .rename(columns={'los_days': 'avg_los_days'}))
    fig = px.bar(
        agg, x='diagnosis', y='avg_los_days', color='complexity',
        barmode='group', text_auto='.1f',
        color_discrete_map={'Simple (1-2)': '#1565C0', 'Complex (3+)': '#E65100'},
    )
    fig.update_traces(marker_line_width=0, textfont_size=9)
    fig.update_layout(
        **_base_layout('Avg LOS by Top Diagnoses & Journey Complexity'),
        xaxis_title='Diagnosis', yaxis_title='Avg LOS (Days)',
        xaxis_tickangle=-30,
    )
    fig.update_layout(legend=dict(orientation='h', yanchor='bottom', y=1.02,
                                  xanchor='right', x=1, title_text='Complexity',
                                  font=dict(size=10)))
    return fig


def make_ed_boarding_dual(_df=None):
    _df = df if _df is None else _df
    if _df.empty:
        return empty_fig("ED Boarding vs Readmission — No Data")
    _df = _df.drop_duplicates(subset=['hadm_id']).copy()
    _df = _df.dropna(subset=['boarding_hrs_xfer', 'is_readmit'])
    _df = _df[(_df['boarding_hrs_xfer'] >= 0) & (_df['boarding_hrs_xfer'] <= 48)]
    bins   = [0, 4, 8, 12, 24, 48]
    labels = ['0–4 hrs', '4–8 hrs', '8–12 hrs', '12–24 hrs', '24–48 hrs']
    _df['bin'] = pd.cut(_df['boarding_hrs_xfer'], bins=bins, labels=labels, include_lowest=True)
    stats  = _df.groupby('bin', observed=True).agg(
        Total=('hadm_id', 'count'), Rate=('is_readmit', 'mean')).reset_index()
    stats['Rate'] *= 100
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(
        x=stats['bin'], y=stats['Total'], name='Patient Volume',
        marker=dict(color='#42A5F5', line_width=0), opacity=0.85,
        hovertemplate='<b>%{x}</b><br>Volume: %{y:,}<extra></extra>',
    ), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=stats['bin'], y=stats['Rate'], name='Readmission Rate (%)',
        mode='lines+markers',
        line=dict(color='#EF5350', width=2.5),
        marker=dict(size=8, color='#EF5350', line=dict(color='white', width=1.5)),
        hovertemplate='<b>%{x}</b><br>Readmit Rate: %{y:.1f}%<extra></extra>',
    ), secondary_y=True)
    base = _base_layout('ED Boarding Time vs. 30-Day Readmission Rate', hovermode='x unified')
    fig.update_layout(**base)
    fig.update_yaxes(title_text='Total Patients',      secondary_y=False,
                     title_font=dict(size=10, color='#607D8B'))
    fig.update_yaxes(title_text='Readmission Rate (%)', secondary_y=True,
                     title_font=dict(size=10, color='#607D8B'), showgrid=False)
    return fig


def make_ed_boarding_box(_df=None):
    _df = df if _df is None else _df
    if _df.empty:
        return empty_fig("ED Boarding Distribution — No Data")
    _df = _df.dropna(subset=['boarding_hrs_xfer']).copy()
    _df = _df[(_df['boarding_hrs_xfer'] >= 0) & (_df['boarding_hrs_xfer'] <= 48)]
    _df['entry_group'] = _df['entry_unit'].map(UNIT_MAP).fillna('Other')
    top_units = ['ICU', 'Medicine', 'Surgery / Procedural', 'Specialist Ward']
    _df = _df[_df['entry_group'].isin(top_units)].copy()
    _df['Readmission Status'] = _df['is_readmit'].map({1: 'Readmitted', 0: 'Not Readmitted'})
    fig = px.box(
        _df, x='entry_group', y='boarding_hrs_xfer', color='Readmission Status',
        labels={'boarding_hrs_xfer': 'ED Boarding (hrs)', 'entry_group': 'Admitted To'},
        color_discrete_map={'Readmitted': '#EF5350', 'Not Readmitted': '#42A5F5'},
        notched=True,
    )
    fig.update_traces(marker_size=3, line_width=1.5)
    fig.update_layout(
        **_base_layout('ED Boarding Distribution by Unit & Readmission Status',
                       hovermode='closest'),
    )
    fig.update_layout(legend=dict(orientation='h', yanchor='bottom', y=1.02,
                                  xanchor='right', x=1, font=dict(size=10)))
    return fig


def make_pareto(_df=None):
    _df = df if _df is None else _df
    if _df.empty:
        return empty_fig("Pareto Chart — No Data")
    pareto = (_df.groupby('diagnosis')['los_days'].sum()
              .sort_values(ascending=False).reset_index())
    pareto['cum_perc'] = 100 * pareto['los_days'].cumsum() / pareto['los_days'].sum()
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(
        x=pareto['diagnosis'].head(15), y=pareto['los_days'].head(15),
        name='Bed Days',
        marker=dict(
            color=pareto['los_days'].head(15),
            colorscale=[[0, '#90CAF9'], [1, '#0D3B6E']],
            line_width=0,
        ),
        hovertemplate='<b>%{x}</b><br>Bed Days: %{y:,.0f}<extra></extra>',
    ), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=pareto['diagnosis'].head(15), y=pareto['cum_perc'].head(15),
        name='Cumulative %', mode='lines+markers',
        line=dict(color='#FF7043', width=2.5),
        marker=dict(size=6, color='#FF7043', line=dict(color='white', width=1.5)),
        hovertemplate='Cumulative: %{y:.1f}%<extra></extra>',
    ), secondary_y=True)
    base = _base_layout('Pareto: Bed Days by Diagnosis', hovermode='x unified')
    fig.update_layout(**base, xaxis_tickangle=-30)
    fig.update_yaxes(title_text='Total Bed Days',  secondary_y=False,
                     title_font=dict(size=10, color='#607D8B'))
    fig.update_yaxes(title_text='Cumulative %',    secondary_y=True,
                     title_font=dict(size=10, color='#607D8B'),
                     range=[0, 105], showgrid=False)
    return fig


def make_bubble(_df=None, use_size=True):
    _df = df if _df is None else _df
    if _df.empty:
        return empty_fig("Readmit vs LOS — No Data")
    bubble = _df.groupby('diagnosis').agg(
        readmit_rate=('is_readmit', 'mean'),
        avg_los=('los_days', 'mean'),
        total_transfers=('trans_count', 'sum'),
        n_admissions=('hadm_id', 'nunique'),
    ).reset_index()
    bubble = (bubble[bubble['n_admissions'] >= 5]
              .sort_values('n_admissions', ascending=False)
              .head(30))
    scatter_kwargs = dict(
        x='readmit_rate', y='avg_los',
        color='readmit_rate',
        color_continuous_scale=[[0, '#4FC3F7'], [0.5, '#1565C0'], [1, '#B71C1C']],
        hover_name='diagnosis',
        labels={'readmit_rate': 'Readmit Rate', 'avg_los': 'Avg LOS (Days)',
                'total_transfers': 'Total Transfers'},
    )
    if use_size:
        scatter_kwargs.update(size='total_transfers', size_max=40)
    fig = px.scatter(bubble, **scatter_kwargs)
    marker_extra = {} if use_size else {'size': 10}
    fig.update_traces(
        marker=dict(line=dict(color='white', width=1), opacity=0.85, **marker_extra),
        hovertemplate='<b>%{hovertext}</b><br>Readmit Rate: %{x:.1%}<br>Avg LOS: %{y:.1f} d<extra></extra>',
    )
    title = ('Readmit Rate vs Avg LOS — Bubble Size = Total Transfers' if use_size
             else 'Readmit Rate vs Avg LOS — Scatter View')
    fig.update_layout(
        **_base_layout(title, hovermode='closest', colorbar=True),
        showlegend=False,
        coloraxis_colorbar=dict(
            title=dict(text='Readmit', font=dict(size=10)), thickness=12,
            tickfont=dict(size=9), outlinewidth=0,
            tickformat='.0%',
        ),
    )
    return fig


def make_pingpong_impact(_df=None, _pp=None):
    _df = df if _df is None else _df
    _pp = pp_df if _pp is None else _pp
    if _df.empty or _pp.empty:
        return empty_fig("Ping-Pong Impact — No Data")
    admission_pp = _pp.groupby('hadm_id')['is_pingpong'].max().reset_index()
    admission_pp.rename(columns={'is_pingpong': 'has_pingpong'}, inplace=True)
    merged = pd.merge(_df, admission_pp, on='hadm_id', how='inner')
    merged['Ping-Pong Status'] = merged['has_pingpong'].map(
        {0: 'No Ping-Pong', 1: 'Experienced Ping-Pong'})
    merged['Readmit Status'] = merged['is_readmit'].map(
        {0: 'Normal Patient', 1: 'Readmitted ≤30 Days'})
    comp = merged.groupby(['Ping-Pong Status', 'Readmit Status']).size().reset_index(name='Count')
    comp['Percentage'] = comp.groupby('Ping-Pong Status')['Count'].transform(
        lambda x: x / x.sum() * 100)
    fig = px.bar(
        comp, x='Ping-Pong Status', y='Percentage', color='Readmit Status',
        text=comp['Percentage'].apply(lambda x: f'{x:.1f}%'),
        color_discrete_map={
            'Normal Patient':       '#29B6F6',
            'Readmitted ≤30 Days':  '#EF5350',
        },
        barmode='stack',
    )
    fig.update_traces(textfont_size=11, textposition='inside', marker_line_width=0)
    fig.update_layout(
        **_base_layout('Ping-Pong Impact on 30-Day Readmission Rates'),
        yaxis_title='% of Patients', xaxis_title='',
    )
    fig.update_layout(legend=dict(orientation='h', yanchor='bottom', y=1.02,
                                  xanchor='right', x=1, font=dict(size=10)))
    return fig


def make_rq3_journey(_df=None):
    _df = df if _df is None else _df
    if _df.empty:
        return empty_fig("Top 10 Readmission Journey Paths — No Data")
    journey_readmit = (_df[_df['is_readmit'] == 1]
                       .groupby('journey_seq').size()
                       .reset_index(name='count')
                       .sort_values('count', ascending=False).head(10)
                       .sort_values('count', ascending=True))
    n     = len(journey_readmit)
    scale = px.colors.sample_colorscale('Blues', [i / max(n - 1, 1) for i in range(n)])
    fig   = go.Figure(go.Bar(
        x=journey_readmit['count'],
        y=journey_readmit['journey_seq'],
        orientation='h',
        marker=dict(color=scale, line_width=0),
        hovertemplate='<b>%{y}</b><br>Cases: %{x:,}<extra></extra>',
    ))
    base = _base_layout('Top 10 Journey Paths Leading to 30-Day Readmission',
                        margin=dict(l=10, r=24, t=52, b=20), hovermode='y unified')
    fig.update_layout(**base)
    fig.update_yaxes(tickfont=dict(size=9))
    return fig


def make_bottleneck_ward(_df=None):
    _df = df if _df is None else _df
    if _df.empty and dfc_ed.empty:
        return empty_fig("Avg ED Boarding by Ward — No Data")
    if not dfc_ed.empty and not _df.empty:
        merged = pd.merge(
            dfc_ed[['hadm_id', 'boarding_hrs_adm']].rename(columns={'boarding_hrs_adm': '_bh'}),
            _df[['hadm_id', 'entry_unit']].drop_duplicates(), on='hadm_id', how='inner')
        merged['ward_group'] = merged['entry_unit'].map(UNIT_MAP_DETAIL).fillna('Other')
    elif not _df.empty:
        merged = _df.dropna(subset=['boarding_hrs_xfer', 'entry_unit']).copy()
        merged = merged.rename(columns={'boarding_hrs_xfer': '_bh'})
        merged['ward_group'] = merged['entry_unit'].map(UNIT_MAP_DETAIL).fillna('Other')
    else:
        return empty_fig("Avg ED Boarding by Ward — No Data")
    merged = merged[merged['ward_group'] != 'Other']
    ward_stats = (merged.groupby('ward_group')
                  .agg(avg_boarding=('_bh', 'mean'), patient_count=('hadm_id', 'count'))
                  .reset_index().sort_values('avg_boarding', ascending=False))
    fig = px.bar(
        ward_stats, x='ward_group', y='avg_boarding',
        color='avg_boarding', text_auto='.1f',
        labels={'avg_boarding': 'Avg Wait (hrs)', 'ward_group': 'Destination Ward'},
        color_continuous_scale=[[0, '#FFE0B2'], [0.5, '#FF8A65'], [1, '#BF360C']],
    )
    fig.update_traces(textfont_size=10, marker_line_width=0)
    fig.update_layout(
        **_base_layout('Avg Waittime for Boarding Hours by Destination Ward',
                       margin=CHART_MARGIN_CB, hovermode='closest', colorbar=True),
        xaxis_tickangle=-25,
        coloraxis_colorbar=dict(
            title=dict(text='Avg hrs', font=dict(size=10)), thickness=12,
            tickfont=dict(size=9), outlinewidth=0,
        ),
    )
    return fig


def make_rq1_transfer_readmit(_df=None):
    _df = df if _df is None else _df
    if _df.empty or 'trans_count' not in _df.columns:
        return empty_fig("Readmission Rate by Transfer Count — No Data")
    _df = _df.drop_duplicates(subset=['hadm_id']).copy()
    _df['transfer_group'] = _df['trans_count'].clip(upper=8).astype(str)
    _df.loc[_df['trans_count'] >= 8, 'transfer_group'] = '8+'
    order = [str(i) for i in range(1, 8)] + ['8+']
    stats = (_df.groupby('transfer_group')
               .agg(count=('hadm_id', 'count'), readmit_rate=('is_readmit', 'mean'))
               .reindex(order).dropna().reset_index())
    stats['readmit_rate'] *= 100
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(
        x=stats['transfer_group'], y=stats['count'], name='Patient Volume',
        marker=dict(
            color=list(range(len(stats))),
            colorscale=[[0, '#BBDEFB'], [1, '#1565C0']],
            line_width=0,
        ),
        opacity=0.85,
        hovertemplate='Transfers: <b>%{x}</b><br>Volume: %{y:,}<extra></extra>',
    ), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=stats['transfer_group'], y=stats['readmit_rate'],
        name='Readmission Rate (%)', mode='lines+markers',
        line=dict(color='#EF5350', width=2.5),
        marker=dict(size=8, color='#EF5350', line=dict(color='white', width=1.5)),
        hovertemplate='Readmit Rate: %{y:.1f}%<extra></extra>',
    ), secondary_y=True)
    base = _base_layout(
        'RQ1: Readmission Rate by Number of Transfers (Complexity Gradient)',
        hovermode='x unified',
    )
    fig.update_layout(**base, xaxis_title='Number of Transfers')
    fig.update_yaxes(title_text='Patient Volume', secondary_y=False,
                     title_font=dict(size=10, color='#607D8B'))
    fig.update_yaxes(title_text='Readmission Rate (%)', secondary_y=True,
                     title_font=dict(size=10, color='#607D8B'), showgrid=False)
    return fig


def make_rq2_days_to_readmit(_df=None):
    _df = df if _df is None else _df
    if _df.empty:
        return empty_fig("Days to Readmission — No Data")
    readmit = _df[_df['is_readmit'] == 1].copy()
    if readmit.empty:
        return empty_fig("Days to Readmission — No Data")
    readmit['next_in']        = pd.to_datetime(readmit['next_in'],  errors='coerce')
    readmit['adm_out']        = pd.to_datetime(readmit['adm_out'],  errors='coerce')
    readmit['days_to_readmit'] = (
        (readmit['next_in'] - readmit['adm_out']).dt.total_seconds() / 86400)
    readmit = readmit.dropna(subset=['days_to_readmit', 'boarding_hrs_xfer'])
    readmit = readmit[
        (readmit['days_to_readmit'] >= 0) & (readmit['days_to_readmit'] <= 30) &
        (readmit['boarding_hrs_xfer'] >= 0) & (readmit['boarding_hrs_xfer'] <= 48)]
    bins   = [0, 4, 8, 12, 24, 48]
    labels = ['0–4 hrs', '4–8 hrs', '8–12 hrs', '12–24 hrs', '24–48 hrs']
    readmit['boarding_bin'] = pd.cut(readmit['boarding_hrs_xfer'], bins=bins,
                                     labels=labels, include_lowest=True)
    fig = px.box(
        readmit, x='boarding_bin', y='days_to_readmit', color='boarding_bin',
        labels={'days_to_readmit': 'Days Until Readmission',
                'boarding_bin':    'ED Boarding Time'},
        color_discrete_sequence=['#E3F2FD', '#90CAF9', '#42A5F5', '#1565C0', '#0D3B6E'],
        notched=True,
    )
    fig.update_traces(marker_size=3, line_width=1.5, showlegend=False)
    fig.update_layout(
        **_base_layout('RQ2: Days Until Readmission by ED Boarding Time',
                       hovermode='closest'),
    )
    return fig


def make_rq3_icd_complexity(_df=None):
    _df = df if _df is None else _df
    if _df.empty or 'diagnosis' not in _df.columns or 'complexity' not in _df.columns:
        return empty_fig("ICD × Complexity Heatmap — No Data")
    sub    = _df.dropna(subset=['diagnosis', 'complexity']).copy()
    top_dx = sub['diagnosis'].value_counts().head(10).index
    sub    = sub[sub['diagnosis'].isin(top_dx)]
    pivot  = (sub.groupby(['diagnosis', 'complexity'])['is_readmit']
               .mean().unstack(fill_value=0) * 100)
    pivot.index = [d[:45] + '…' if len(d) > 45 else d for d in pivot.index]
    fig = px.imshow(
        pivot, text_auto='.1f', aspect='auto',
        color_continuous_scale=[[0, '#E8F5E9'], [0.4, '#FFCC02'], [1, '#C62828']],
        labels={'color': 'Readmit %'},
    )
    fig.update_layout(
        **_base_layout(
            'RQ3: Readmission Rate (%) — Top ICD Diagnoses × Journey Complexity',
            margin=dict(l=10, r=80, t=52, b=20), hovermode='closest', colorbar=True,
        ),
        xaxis_title='Journey Complexity', yaxis_title='',
        coloraxis_colorbar=dict(
            title=dict(text='Readmit %', font=dict(size=10)), thickness=12,
            tickfont=dict(size=9), outlinewidth=0,
        ),
    )
    fig.update_yaxes(tickfont=dict(size=9))
    return fig


def make_ward_flow_balance():
    """Static grouped bar: inflow vs outflow per ward from CHORD_MATRIX."""
    groups   = ['ED', 'ED Obs', 'ICU', 'Medicine', 'Surgery / Procedural', 'Specialist Ward', 'Maternity']
    matrix   = [
        [0,   447,  70,    437,   130,   72,   1],
        [0,     0, 2410, 14245,  3892, 1621,  33],
        [0,   802,    0, 35442, 22301, 12321, 276],
        [3,  5549, 13004,    0, 11748,  5206, 117],
        [2,  2090, 15362, 11285,    0,  3986, 190],
        [1,   874,  4122,  2742,  3238,    0,  12],
        [0,    13,   215,   109,   188,    27,   0],
    ]
    colors = {
        'ED': '#1565C0', 'ED Obs': '#29B6F6', 'ICU': '#BF360C',
        'Medicine': '#2E7D32', 'Surgery / Procedural': '#6A1B9A',
        'Specialist Ward': '#F57F17', 'Maternity': '#00695C',
    }
    n       = len(groups)
    inflow  = [sum(matrix[j][i] for j in range(n) if j != i) for i in range(n)]
    outflow = [sum(matrix[i][j] for j in range(n) if j != i) for i in range(n)]
    net     = [inflow[i] - outflow[i] for i in range(n)]

    bar_colors = [colors[g] for g in groups]
    net_colors = ['#2E7D32' if v > 0 else '#C62828' for v in net]

    fig = make_subplots(
        rows=1, cols=2,
        column_widths=[0.6, 0.4],
        horizontal_spacing=0.10,
    )
    # Left: grouped inflow/outflow bars
    fig.add_trace(go.Bar(
        name='Inflow', y=groups, x=inflow, orientation='h',
        marker=dict(color=bar_colors, opacity=0.85, line_width=0),
        hovertemplate='<b>%{y}</b><br>Inflow: %{x:,}<extra></extra>',
    ), row=1, col=1)
    fig.add_trace(go.Bar(
        name='Outflow', y=groups, x=[-v for v in outflow], orientation='h',
        marker=dict(color=bar_colors, opacity=0.40, line_width=0,
                    pattern_shape='/'),
        hovertemplate='<b>%{y}</b><br>Outflow: %{customdata:,}<extra></extra>',
        customdata=outflow,
    ), row=1, col=1)
    # Right: net flow diverging
    fig.add_trace(go.Bar(
        name='Net Flow', y=groups, x=net, orientation='h',
        showlegend=False,
        marker=dict(color=net_colors, opacity=0.85, line_width=0),
        hovertemplate='<b>%{y}</b><br>Net: %{x:+,}<extra></extra>',
    ), row=1, col=2)
    fig.add_vline(x=0, line_width=1, line_color='#90A4AE', row=1, col=2)

    h = 230
    fig.update_layout(
        font=dict(family=_FONT_FAMILY, size=10, color='#455A64'),
        paper_bgcolor='#FFFFFF', plot_bgcolor='#F8FBFF',
        height=h, margin=dict(l=10, r=10, t=32, b=8),
        barmode='overlay',
        bargap=0.3,
        legend=dict(orientation='h', y=1.12, x=0.3, font=dict(size=9),
                    bgcolor='rgba(0,0,0,0)'),
        hoverlabel=dict(bgcolor='#1E293B', font_color='white',
                        font_size=10, font_family=_FONT_FAMILY),
        annotations=[
            dict(text='<b>Inflow vs Outflow by Ward</b>', x=0.28, y=1.05,
                 xref='paper', yref='paper', showarrow=False,
                 font=dict(size=11, color='#0D1B3E', family=_FONT_FAMILY)),
            dict(text='<b>Net Flow (Inflow − Outflow)</b>', x=0.88, y=1.05,
                 xref='paper', yref='paper', showarrow=False,
                 font=dict(size=11, color='#0D1B3E', family=_FONT_FAMILY)),
        ],
    )
    fig.update_xaxes(showgrid=True, gridcolor='#EEF2F7', zeroline=True,
                     zerolinecolor='#CFD8DC', tickfont=dict(size=9))
    fig.update_yaxes(tickfont=dict(size=9, color='#546E7A'))
    return fig


# ── Pre-build all figures ─────────────────────────────────────────
fig_heatmap          = make_heatmap()
fig_los_bar          = make_los_bar()
fig_ed_dual          = make_ed_boarding_dual()
fig_ed_box           = make_ed_boarding_box()
fig_pareto           = make_pareto()
fig_bubble           = make_bubble()
fig_pp_impact        = make_pingpong_impact()
fig_rq3              = make_rq3_journey()
fig_bottleneck       = make_bottleneck_ward()
fig_transfer_readmit = make_rq1_transfer_readmit()
fig_days_readmit     = make_rq2_days_to_readmit()
fig_icd_complexity   = make_rq3_icd_complexity()


# ══════════════════════════════════════════════════════════════════
#  CHORD DIAGRAM HTML
# ══════════════════════════════════════════════════════════════════
CHORD_GROUPS = ['ED', 'ED Obs', 'ICU', 'Medicine',
                'Surgery / Procedural', 'Specialist Ward', 'Maternity']
CHORD_COLORS = {
    'ED':                  '#1565C0',
    'ED Obs':              '#29B6F6',
    'ICU':                 '#BF360C',
    'Medicine':            '#2E7D32',
    'Surgery / Procedural':'#6A1B9A',
    'Specialist Ward':     '#F57F17',
    'Maternity':           '#00695C',
}
CHORD_MATRIX = [
    [0,   447,  70,    437,   130,   72,   1],
    [0,     0, 2410, 14245,  3892, 1621,  33],
    [0,   802,    0, 35442, 22301, 12321, 276],
    [3,  5549, 13004,    0, 11748,  5206, 117],
    [2,  2090, 15362, 11285,    0,  3986, 190],
    [1,   874,  4122,  2742,  3238,    0,  12],
    [0,    13,   215,   109,   188,    27,   0],
]
total_t = sum(sum(r) for r in CHORD_MATRIX)
icu_in  = sum(CHORD_MATRIX[i][2] for i in range(7) if i != 2)
max_rib = max(CHORD_MATRIX[i][j] for i in range(7) for j in range(7) if i != j)

CHORD_HTML = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><style>
*{{box-sizing:border-box;margin:0;padding:0;}}
body{{font-family:'Inter','Segoe UI',sans-serif;background:#fff;padding:10px;}}
#mk{{display:grid;grid-template-columns:repeat(3,1fr);gap:6px;margin-bottom:10px;}}
.m{{background:linear-gradient(135deg,#F0F7FF,#E8F0FE);border-radius:8px;padding:8px 10px;
    border:1px solid #DBEAFE;transition:all .25s ease;}}
.m.ward{{background:linear-gradient(135deg,#F5F3FF,#EDE9FE);border-color:#C4B5FD;}}
.ml{{font-size:9px;color:#64748B;font-weight:600;letter-spacing:.05em;margin-bottom:3px;
     transition:color .2s;text-transform:uppercase;}}
.mv{{font-size:16px;font-weight:800;color:#0D1B3E;transition:color .2s;line-height:1.1;}}
.msub{{font-size:8px;color:#94A3B8;margin-top:2px;}}
#leg{{display:flex;flex-wrap:wrap;gap:4px;margin-bottom:8px;}}
.litem{{display:flex;align-items:center;gap:4px;cursor:pointer;padding:3px 8px;
        border-radius:20px;border:1.5px solid #E8EEF4;font-size:9px;color:#546E7A;
        background:#FAFBFF;transition:all .15s;user-select:none;}}
.litem:hover{{background:#EFF6FF;border-color:#BFDBFE;}}
.litem.active{{font-weight:700;border-width:1.5px;}}
#cw{{width:100%;display:flex;justify-content:center;}}
#tip{{display:none;position:fixed;background:#1E2A3A;color:#ECF0F1;border-radius:6px;
      padding:7px 11px;font-size:10px;pointer-events:none;z-index:999;
      box-shadow:0 4px 12px rgba(0,0,0,.3);line-height:1.7;}}
#hint{{font-size:8.5px;color:#94A3B8;text-align:center;margin-top:4px;letter-spacing:.03em;}}
</style></head><body>
<div id="mk">
  <div class="m" id="sc0">
    <div class="ml" id="sl0">TOTAL TRANSITIONS</div>
    <div class="mv" id="sv0">{round(total_t/1000)}k</div>
    <div class="msub" id="ss0">all wards combined</div>
  </div>
  <div class="m" id="sc1">
    <div class="ml" id="sl1">ICU INFLOW</div>
    <div class="mv" id="sv1" style="color:#BF360C">{round(icu_in/1000)}k</div>
    <div class="msub" id="ss1">from all other wards</div>
  </div>
  <div class="m" id="sc2">
    <div class="ml" id="sl2">LARGEST RIBBON</div>
    <div class="mv" id="sv2">{round(max_rib/1000)}k</div>
    <div class="msub" id="ss2">ICU → Medicine</div>
  </div>
</div>
<div id="leg"></div><div id="cw"></div>
<div id="hint">Click a ward segment to inspect its flow details</div>
<div id="tip"></div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"></script>
<script>
(function(){{
const G={json.dumps(CHORD_GROUPS)};
const M={json.dumps(CHORD_MATRIX)};
const C={json.dumps(CHORD_COLORS)};
const GTOT={total_t}, GICU={icu_in}, GMAX={max_rib};

function fmt(n){{return n>=1000?(n/1000).toFixed(0)+'k':n.toLocaleString();}}
function fmtFull(n){{return n.toLocaleString();}}

function updateStats(idx){{
  const cards=[0,1,2].map(i=>document.getElementById('sc'+i));
  if(idx===null){{
    cards.forEach(c=>c.classList.remove('ward'));
    document.getElementById('sl0').textContent='TOTAL TRANSITIONS';
    document.getElementById('sv0').textContent=fmt(GTOT);
    document.getElementById('sv0').style.color='#0D1B3E';
    document.getElementById('ss0').textContent='all wards combined';
    document.getElementById('sl1').textContent='ICU INFLOW';
    document.getElementById('sv1').textContent=fmt(GICU);
    document.getElementById('sv1').style.color='#BF360C';
    document.getElementById('ss1').textContent='from all other wards';
    document.getElementById('sl2').textContent='LARGEST RIBBON';
    document.getElementById('sv2').textContent=fmt(GMAX);
    document.getElementById('sv2').style.color='#0D1B3E';
    document.getElementById('ss2').textContent='ICU \u2192 Medicine';
    document.getElementById('hint').textContent='Click a ward segment to inspect its flow details';
    document.querySelectorAll('.litem').forEach(el=>el.classList.remove('active'));
  }} else {{
    const g=G[idx],col=C[g];
    const inflow=M.reduce((s,r,j)=>s+(j!==idx?r[idx]:0),0);
    const outflow=M[idx].reduce((s,v,j)=>s+(j!==idx?v:0),0);
    const net=inflow-outflow;
    const netCol=net>0?'#2E7D32':net<0?'#C62828':'#607D8B';
    const netSign=net>0?'+':'';
    // top destination
    let topDst=0,topDstIdx=-1;
    M[idx].forEach((v,j)=>{{if(j!==idx&&v>topDst){{topDst=v;topDstIdx=j;}}}});
    let topSrc=0,topSrcIdx=-1;
    M.forEach((r,j)=>{{if(j!==idx&&r[idx]>topSrc){{topSrc=r[idx];topSrcIdx=j;}}}});
    cards.forEach(c=>c.classList.add('ward'));
    document.getElementById('sl0').textContent=g.toUpperCase()+' INFLOW';
    document.getElementById('sv0').textContent=fmtFull(inflow);
    document.getElementById('sv0').style.color=col;
    document.getElementById('ss0').textContent=(topSrcIdx>=0?'top source: '+G[topSrcIdx]:'');
    document.getElementById('sl1').textContent=g.toUpperCase()+' OUTFLOW';
    document.getElementById('sv1').textContent=fmtFull(outflow);
    document.getElementById('sv1').style.color=col;
    document.getElementById('ss1').textContent=(topDstIdx>=0?'top dest: '+G[topDstIdx]:'');
    document.getElementById('sl2').textContent='NET FLOW';
    document.getElementById('sv2').textContent=netSign+fmtFull(net);
    document.getElementById('sv2').style.color=netCol;
    document.getElementById('ss2').textContent=net>0?'net receiver':'net distributor';
    document.getElementById('hint').textContent='Click the same segment again to reset';
    document.querySelectorAll('.litem').forEach((el,i)=>{{
      el.classList.toggle('active',i===idx);
      el.style.borderColor=i===idx?col:'#E8EEF4';
      el.style.background=i===idx?col+'18':'#FAFBFF';
      el.style.color=i===idx?col:'#546E7A';
    }});
  }}
}}

const items=G.map((g,i)=>
  `<span class="litem" id="li${{i}}" onclick="sel(${{i}})"
    style="border-color:#E8EEF4">
    <span style="width:8px;height:8px;border-radius:2px;background:${{C[g]}};flex-shrink:0"></span>
    ${{g}}</span>`).join('');
document.getElementById('leg').innerHTML=items;

const W=390,H=390,cx=W/2,cy=H/2,oR=150,iR=130;
let sel_idx=null;
const svg=d3.select('#cw').append('svg')
  .attr('viewBox',`0 0 ${{W}} ${{H}}`).attr('width','100%').style('max-width','390px');
const gEl=svg.append('g').attr('transform',`translate(${{cx}},${{cy}})`);
const chord=d3.chord().padAngle(0.022).sortSubgroups(d3.descending)(M);
const arc=d3.arc().innerRadius(iR).outerRadius(oR);
const rib=d3.ribbon().radius(iR-2);
const gG=gEl.append('g').selectAll('g').data(chord.groups).join('g');
gG.append('path').attr('d',arc)
  .attr('fill',d=>C[G[d.index]]).attr('stroke','white').attr('stroke-width',1)
  .style('cursor','pointer').style('filter','drop-shadow(0 1px 2px rgba(0,0,0,.15))')
  .on('mouseover',(e,d)=>{{
    const i=M.reduce((s,r,j)=>s+(j!==d.index?r[d.index]:0),0),
          o=M[d.index].reduce((s,v,j)=>s+(j!==d.index?v:0),0);
    tip(e,`<b>${{G[d.index]}}</b><br>In: ${{i.toLocaleString()}}  ·  Out: ${{o.toLocaleString()}}`)}})
  .on('mousemove',mv).on('mouseout',ht).on('click',(_,d)=>sel(d.index));
gG.append('text').each(d=>{{d.angle=(d.startAngle+d.endAngle)/2;}})
  .attr('dy','.35em')
  .attr('transform',d=>{{const r=oR+14;
    return `rotate(${{d.angle*180/Math.PI-90}}) translate(${{r}},0)${{d.angle>Math.PI?' rotate(180)':''}}`;
  }})
  .attr('text-anchor',d=>d.angle>Math.PI?'end':'start')
  .style('font-size','9px').style('fill','#37474F').style('font-weight','600')
  .text(d=>G[d.index]);
const ribs=gEl.append('g').attr('fill-opacity',.42)
  .selectAll('path').data(chord).join('path')
  .attr('d',rib).attr('fill',d=>C[G[d.source.index]]).attr('stroke','none')
  .style('cursor','pointer')
  .on('mouseover',function(e,d){{
    d3.select(this).attr('fill-opacity',.85);
    const s=G[d.source.index],t=G[d.target.index];
    tip(e,`<b>${{s}} \u2194 ${{t}}</b><br>${{s}} \u2192 ${{t}}: ${{M[d.source.index][d.target.index].toLocaleString()}}<br>${{t}} \u2192 ${{s}}: ${{M[d.target.index][d.source.index].toLocaleString()}}`)}})
  .on('mousemove',mv).on('mouseout',function(){{upd();ht();}});
function upd(){{ribs.attr('fill-opacity',d=>sel_idx===null?.42:
  (d.source.index===sel_idx||d.target.index===sel_idx)?.78:.05);}}
function sel(i){{
  sel_idx=(sel_idx===i)?null:i;
  upd();
  gG.selectAll('path').attr('opacity',d=>sel_idx===null?1:d.index===sel_idx?1:.22);
  updateStats(sel_idx);
}}
const T=document.getElementById('tip');
function tip(e,h){{T.innerHTML=h;T.style.display='block';mv(e);}}
function mv(e){{T.style.left=(e.clientX+14)+'px';T.style.top=(e.clientY-6)+'px';}}
function ht(){{T.style.display='none';}}
}})();
</script></body></html>"""


# ══════════════════════════════════════════════════════════════════
#  DASH APP
# ══════════════════════════════════════════════════════════════════
EXTERNAL_STYLESHEETS = [
    "https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap"
]

app = dash.Dash(
    __name__,
    title="Patient Flow & Readmission Analytics",
    external_stylesheets=EXTERNAL_STYLESHEETS,
    suppress_callback_exceptions=True,
)
server = app.server  # required for Gunicorn

HAS_AGE    = not df.empty and 'age'    in df.columns
HAS_GENDER = not df.empty and 'gender' in df.columns

if not df.empty and 'diagnosis' in df.columns:
    _top_dx = df['diagnosis'].dropna().value_counts().head(50).index.tolist()
    DIAGNOSIS_OPTIONS = [{'label': 'All Diagnoses', 'value': 'all'}] + [
        {'label': d[:60], 'value': d} for d in _top_dx
    ]
else:
    DIAGNOSIS_OPTIONS = [{'label': 'All Diagnoses', 'value': 'all'}]


def apply_filters(source_df, source_pp, age_range, gender, diagnosis, ff):
    _df = source_df.copy()
    _pp = source_pp.copy() if not source_pp.empty else source_pp
    if diagnosis and diagnosis != 'all' and 'diagnosis' in _df.columns:
        _df = _df[_df['diagnosis'] == diagnosis]
    if HAS_AGE and age_range and (age_range[0] > 1 or age_range[1] < 120):
        _df = _df[_df['age'].between(age_range[0], age_range[1])]
    if HAS_GENDER and gender and gender != 'all':
        _df = _df[_df['gender'].str.upper() == gender.upper()]
    if ff and 'ff' in ff and 'trans_count' in _df.columns:
        threshold = source_df['trans_count'].quantile(0.95)
        _df = _df[_df['trans_count'] >= threshold]
    if not _pp.empty and not _df.empty:
        _pp = _pp[_pp['hadm_id'].isin(_df['hadm_id'])]
    return _df, _pp


# ── Layout helpers ────────────────────────────────────────────────
_GRAPH_CONFIG = {'displayModeBar': False, 'responsive': True}

_CARD_STYLE = {
    'background': '#FFFFFF',
    'borderRadius': '12px',
    'boxShadow': '0 1px 4px rgba(13,27,62,.08), 0 4px 16px rgba(13,27,62,.06)',
    'overflow': 'hidden',
    'border': '1px solid #EEF2F7',
}

_CHART_TITLE_STYLE = {
    'fontSize': '11px',
    'fontWeight': '600',
    'color': '#64748B',
    'letterSpacing': '.02em',
    'marginBottom': '2px',
    'fontFamily': _FONT_FAMILY,
    'textTransform': 'uppercase',
}


def chart_card(graph_id, figure, border_color='#1565C0'):
    return html.Div(
        dcc.Graph(
            id=graph_id, figure=figure,
            config=_GRAPH_CONFIG,
            style={'height': f'{CHART_H}px'},
        ),
        style={**_CARD_STYLE, 'borderTop': f'3px solid {border_color}'},
    )


def gcol(graph_id, figure, span=6, border_color='#1565C0'):
    return dmc.GridCol(chart_card(graph_id, figure, border_color), span=span)


def kpi_card(label, kpi_id, value, icon, bg, fg, border):
    return dmc.GridCol(
        html.Div(
            [
                html.Div(
                    [
                        html.Span(icon, style={'fontSize': '18px', 'lineHeight': '1'}),
                    ],
                    style={
                        'width': '36px', 'height': '36px', 'borderRadius': '10px',
                        'background': bg, 'display': 'flex', 'alignItems': 'center',
                        'justifyContent': 'center', 'flexShrink': '0',
                    }
                ),
                html.Div(
                    [
                        html.Div(label, style={
                            'fontSize': '9px', 'fontWeight': '700', 'color': '#94A3B8',
                            'letterSpacing': '.08em', 'textTransform': 'uppercase',
                            'marginBottom': '2px', 'fontFamily': _FONT_FAMILY,
                        }),
                        html.Div(value, id=kpi_id, style={
                            'fontSize': '22px', 'fontWeight': '800', 'color': fg,
                            'lineHeight': '1.1', 'fontFamily': _FONT_FAMILY,
                        }),
                    ],
                ),
            ],
            style={
                'display': 'flex', 'alignItems': 'center', 'gap': '12px',
                'padding': '14px 16px',
                **_CARD_STYLE,
                'borderLeft': f'4px solid {border}',
            },
        ),
        span={'base': 6, 'sm': 4, 'lg': 'auto'},
    )


def rq_alert(text, color, question_num):
    colors = {'blue': ('#EFF6FF', '#1D4ED8', '#BFDBFE'),
              'orange': ('#FFF7ED', '#C2410C', '#FED7AA'),
              'green': ('#F0FDF4', '#15803D', '#BBF7D0')}
    bg, fg, border = colors.get(color, colors['blue'])
    return html.Div(
        [
            html.Span(f'RQ{question_num}',
                      style={'fontWeight': '800', 'color': fg,
                             'fontSize': '12px', 'marginRight': '8px',
                             'fontFamily': _FONT_FAMILY}),
            html.Span(text, style={'color': fg, 'fontSize': '12px',
                                   'fontFamily': _FONT_FAMILY, 'lineHeight': '1.5'}),
        ],
        style={
            'background': bg, 'border': f'1px solid {border}',
            'borderLeft': f'4px solid {fg}',
            'borderRadius': '8px', 'padding': '12px 16px',
        },
    )


# ══════════════════════════════════════════════════════════════════
#  LAYOUT
# ══════════════════════════════════════════════════════════════════
_LAST_REFRESH = datetime.now().strftime('%d %b %Y, %H:%M')

app.layout = dmc.MantineProvider(
    html.Div(
        [
            # ── Header ──────────────────────────────────────────────
            html.Div(
                html.Div(
                    [
                        # Left: icon + title block
                        html.Div(
                            [
                                html.Div(
                                    '🏥',
                                    style={
                                        'fontSize': '28px', 'lineHeight': '1',
                                        'marginRight': '14px',
                                        'filter': 'drop-shadow(0 2px 4px rgba(0,0,0,.3))',
                                    }
                                ),
                                html.Div(
                                    [
                                        html.Div(
                                            'PATIENT FLOW & READMISSION ANALYTICS',
                                            style={
                                                'fontFamily': _FONT_FAMILY,
                                                'fontSize': '15px', 'fontWeight': '800',
                                                'color': '#FFFFFF', 'letterSpacing': '.06em',
                                                'lineHeight': '1.2',
                                            }
                                        ),
                                        html.Div(
                                            'MIMIC-IV Clinical Dataset  ·  Hospital Operations Intelligence',
                                            style={
                                                'fontFamily': _FONT_FAMILY,
                                                'fontSize': '10px', 'fontWeight': '400',
                                                'color': 'rgba(255,255,255,.55)',
                                                'letterSpacing': '.04em',
                                                'marginTop': '2px',
                                            }
                                        ),
                                    ]
                                ),
                            ],
                            style={'display': 'flex', 'alignItems': 'center'},
                        ),
                        # Right: status badge
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.Span(style={
                                            'width': '7px', 'height': '7px', 'borderRadius': '50%',
                                            'background': '#4ADE80', 'display': 'inline-block',
                                            'marginRight': '6px', 'flexShrink': '0',
                                            'boxShadow': '0 0 6px #4ADE80',
                                        }),
                                        html.Span(f'Live  ·  {_LAST_REFRESH}',
                                                  style={'fontSize': '10px', 'color': 'rgba(255,255,255,.6)',
                                                         'fontFamily': _FONT_FAMILY}),
                                    ],
                                    style={'display': 'flex', 'alignItems': 'center'},
                                ),
                            ],
                        ),
                    ],
                    style={
                        'maxWidth': '1600px', 'margin': '0 auto',
                        'display': 'flex', 'alignItems': 'center',
                        'justifyContent': 'space-between',
                        'padding': '0 20px',
                    },
                ),
                style={
                    'background': 'linear-gradient(135deg, #0A1628 0%, #0D2A5E 60%, #0F4C81 100%)',
                    'padding': '18px 0',
                    'borderBottom': '1px solid rgba(255,255,255,.08)',
                    'boxShadow': '0 4px 20px rgba(10,22,40,.4)',
                    'marginBottom': '16px',
                }
            ),

            html.Div(
                [
                    dcc.Store(id='bubble-size-on', data=True),
                    # ── KPI Row ─────────────────────────────────────
                    dmc.Grid(
                        [
                            kpi_card('Total Admissions',      'kpi-total',   KPI_TOTAL,
                                     '📋', '#EFF6FF', C_BLUE,   C_BLUE),
                            kpi_card('Median / Avg LOS',      'kpi-los',     KPI_LOS,
                                     '🛏️', '#F0FDF4', C_TEAL,   C_TEAL),
                            kpi_card('30-Day Readmission',    'kpi-readmit', KPI_READMIT,
                                     '🔁', '#FFF1F0', C_ORANGE, C_ORANGE),
                            kpi_card('Avg ED Boarding',       'kpi-ed',      KPI_ED,
                                     '⏱️', '#FFFBEB', C_AMBER,  C_AMBER),
                            kpi_card('Ping-Pong Rate',        'kpi-pp',      KPI_PP,
                                     '🏓', '#F5F3FF', C_PURPLE, C_PURPLE),
                        ],
                        gutter='sm', mb='md',
                    ),

                    # ── Filter Bar ──────────────────────────────────
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Div('FILTERS', style={
                                        'fontSize': '9px', 'fontWeight': '700',
                                        'color': '#94A3B8', 'letterSpacing': '.1em',
                                        'marginBottom': '14px', 'fontFamily': _FONT_FAMILY,
                                    }),
                                    html.Div(
                                        [
                                            # Diagnosis
                                            html.Div(
                                                [
                                                    html.Div('DIAGNOSIS (ICD)', style={
                                                        'fontSize': '9px', 'fontWeight': '700',
                                                        'color': '#64748B', 'letterSpacing': '.06em',
                                                        'marginBottom': '6px',
                                                        'fontFamily': _FONT_FAMILY,
                                                    }),
                                                    dcc.Dropdown(
                                                        id='diagnosis-dropdown',
                                                        options=DIAGNOSIS_OPTIONS,
                                                        value='all',
                                                        clearable=False,
                                                        style={'fontSize': '12px', 'minWidth': '220px'},
                                                    ),
                                                ],
                                                style={'flex': '0 0 230px'},
                                            ),
                                            # Age
                                            html.Div(
                                                [
                                                    html.Div('AGE GROUP', style={
                                                        'fontSize': '9px', 'fontWeight': '700',
                                                        'color': '#64748B', 'letterSpacing': '.06em',
                                                        'marginBottom': '6px',
                                                        'fontFamily': _FONT_FAMILY,
                                                    }),
                                                    dcc.RangeSlider(
                                                        id='age-slider', min=1, max=120,
                                                        value=[1, 120],
                                                        marks={1: '1', 20: '20', 40: '40',
                                                               60: '60', 80: '80', 100: '100',
                                                               120: '120'},
                                                        tooltip={"placement": "bottom",
                                                                 "always_visible": True},
                                                        step=1, disabled=not HAS_AGE,
                                                    ),
                                                ],
                                                style={'flex': '1', 'minWidth': '220px'},
                                            ),
                                            # Gender
                                            html.Div(
                                                [
                                                    html.Div('GENDER', style={
                                                        'fontSize': '9px', 'fontWeight': '700',
                                                        'color': '#64748B', 'letterSpacing': '.06em',
                                                        'marginBottom': '6px',
                                                        'fontFamily': _FONT_FAMILY,
                                                    }),
                                                    dcc.Dropdown(
                                                        id='gender-dropdown',
                                                        options=[
                                                            {'label': 'All Genders', 'value': 'all'},
                                                            {'label': 'Male',        'value': 'M'},
                                                            {'label': 'Female',      'value': 'F'},
                                                        ],
                                                        value='all',
                                                        clearable=False,
                                                        disabled=not HAS_GENDER,
                                                        style={'fontSize': '12px', 'minWidth': '130px'},
                                                    ),
                                                ],
                                                style={'flex': '0 0 140px'},
                                            ),
                                            # Frequent flyers
                                            html.Div(
                                                [
                                                    html.Div('\u00a0', style={
                                                        'fontSize': '9px', 'marginBottom': '6px',
                                                    }),
                                                    dcc.Checklist(
                                                        id='frequent-flyers-toggle',
                                                        options=[{'label': '  Frequent Flyers (Top 5%)',
                                                                  'value': 'ff'}],
                                                        value=[],
                                                        style={
                                                            'fontSize': '12px',
                                                            'fontFamily': _FONT_FAMILY,
                                                            'color': '#374151',
                                                        },
                                                    ),
                                                ],
                                            ),
                                        ],
                                        style={
                                            'display': 'flex', 'flexWrap': 'wrap',
                                            'gap': '20px', 'alignItems': 'flex-start',
                                        },
                                    ),
                                ],
                                style={'flex': '1'},
                            ),
                        ],
                        style={
                            **_CARD_STYLE,
                            'padding': '16px 20px',
                            'marginBottom': '16px',
                            'background': '#FAFBFF',
                            'borderLeft': '4px solid #C7D2FE',
                        },
                    ),

                    # ── Tabs ────────────────────────────────────────
                    dmc.Tabs(
                        [
                            dmc.TabsList(
                                [
                                    dmc.TabsTab(
                                        html.Span([html.Span('📊  '), 'Overview'],
                                                  style={'fontFamily': _FONT_FAMILY,
                                                         'fontWeight': '600', 'fontSize': '12px'}),
                                        value='overview',
                                    ),
                                    dmc.TabsTab(
                                        html.Span([html.Span('🔀  '), 'RQ1 — Pathways & Frequent Flyers'],
                                                  style={'fontFamily': _FONT_FAMILY,
                                                         'fontWeight': '600', 'fontSize': '12px'}),
                                        value='rq1',
                                    ),
                                    dmc.TabsTab(
                                        html.Span([html.Span('🚨  '), 'RQ2 — ED Boarding Bottlenecks'],
                                                  style={'fontFamily': _FONT_FAMILY,
                                                         'fontWeight': '600', 'fontSize': '12px'}),
                                        value='rq2',
                                    ),
                                    dmc.TabsTab(
                                        html.Span([html.Span('🏥  '), 'RQ3 — ICD & Bed Resources'],
                                                  style={'fontFamily': _FONT_FAMILY,
                                                         'fontWeight': '600', 'fontSize': '12px'}),
                                        value='rq3',
                                    ),
                                ],
                                mb='md',
                                style={
                                    'borderBottom': '2px solid #EEF2F7',
                                    'gap': '4px',
                                },
                            ),

                            # ── Overview ────────────────────────────
                            dmc.TabsPanel(
                                dmc.Grid(
                                    [
                                        # Left column: chord + ward flow balance
                                        dmc.GridCol(
                                            dmc.Stack(
                                                [
                                                    # Chord diagram card
                                                    html.Div(
                                                        [
                                                            html.Div(
                                                                'Macro-Level Patient Flow',
                                                                style=_CHART_TITLE_STYLE,
                                                            ),
                                                            html.Iframe(
                                                                srcDoc=CHORD_HTML,
                                                                style={
                                                                    'width': '100%',
                                                                    'height': '520px',
                                                                    'border': 'none',
                                                                },
                                                            ),
                                                        ],
                                                        style={
                                                            **_CARD_STYLE,
                                                            'padding': '16px',
                                                            'borderTop': f'3px solid {C_BLUE}',
                                                        },
                                                    ),
                                                ],
                                                gap='sm',
                                            ),
                                            span=5,
                                        ),
                                        # Right column: bubble + pp impact
                                        dmc.GridCol(
                                            dmc.Stack(
                                                [
                                                    html.Div(
                                        [
                                            html.Button(
                                                '⬤ Bubble',
                                                id='bubble-size-btn',
                                                n_clicks=0,
                                                style=_BUBBLE_BTN_ON,
                                            ),
                                            dcc.Graph(
                                                id='graph-bubble', figure=fig_bubble,
                                                config=_GRAPH_CONFIG,
                                                style={'height': f'{CHART_H}px'},
                                            ),
                                        ],
                                        style={**_CARD_STYLE, 'borderTop': f'3px solid {C_CYAN}',
                                               'position': 'relative'},
                                    ),
                                                    chart_card('graph-pp-impact', fig_pp_impact, C_PURPLE),
                                                ],
                                                gap='sm',
                                            ),
                                            span=7,
                                        ),
                                    ],
                                    gutter='sm',
                                ),
                                value='overview', pt='sm',
                            ),

                            # ── RQ1 ─────────────────────────────────
                            dmc.TabsPanel(
                                dmc.Stack(
                                    [
                                        rq_alert(
                                            'Are complex or ping-pong transfer pathways significantly '
                                            'correlated with the likelihood of patients becoming '
                                            'high-frequency readmissions (Top 5% Frequent Flyers)?',
                                            'blue', 1,
                                        ),
                                        dmc.Grid(
                                            [
                                                gcol('graph-heatmap',        fig_heatmap,        6, C_BLUE),
                                                gcol('graph-pp-rq1',         fig_pp_impact,      6, C_PURPLE),
                                            ],
                                            gutter='sm',
                                        ),
                                        dmc.Grid(
                                            [gcol('graph-transfer-readmit', fig_transfer_readmit, 12, C_ORANGE)],
                                            gutter='sm',
                                        ),
                                    ],
                                    gap='sm',
                                ),
                                value='rq1', pt='sm',
                            ),

                            # ── RQ2 ─────────────────────────────────
                            dmc.TabsPanel(
                                dmc.Stack(
                                    [
                                        rq_alert(
                                            'How do system bottlenecks such as emergency room boarding '
                                            'times impact the time to readmission and the rate of '
                                            'patients who need to be readmitted within 30 days?',
                                            'orange', 2,
                                        ),
                                        dmc.Grid(
                                            [
                                                gcol('graph-ed-dual',      fig_ed_dual,      6, C_AMBER),
                                                gcol('graph-days-readmit', fig_days_readmit, 6, C_ORANGE),
                                            ],
                                            gutter='sm',
                                        ),
                                        dmc.Grid(
                                            [
                                                gcol('graph-ed-box',     fig_ed_box,     6, C_BLUE),
                                                gcol('graph-bottleneck', fig_bottleneck, 6, C_AMBER),
                                            ],
                                            gutter='sm',
                                        ),
                                    ],
                                    gap='sm',
                                ),
                                value='rq2', pt='sm',
                            ),

                            # ── RQ3 ─────────────────────────────────
                            dmc.TabsPanel(
                                dmc.Stack(
                                    [
                                        rq_alert(
                                            'Considering ICD diagnoses in conjunction with the patient '
                                            'journey sequence, which ICD group is the primary factor in '
                                            'driving readmissions and consuming the most hospital bed resources?',
                                            'green', 3,
                                        ),
                                        dmc.Grid(
                                            [
                                                gcol('graph-pareto',        fig_pareto,        6, C_TEAL),
                                                gcol('graph-icd-complexity', fig_icd_complexity, 6, C_ORANGE),
                                            ],
                                            gutter='sm',
                                        ),
                                        dmc.Grid(
                                            [
                                                gcol('graph-rq3',     fig_rq3,     6, C_BLUE),
                                                gcol('graph-los-bar', fig_los_bar, 6, C_PURPLE),
                                            ],
                                            gutter='sm',
                                        ),
                                    ],
                                    gap='sm',
                                ),
                                value='rq3', pt='sm',
                            ),
                        ],
                        value='overview',
                        id='main-tabs',
                    ),

                    # ── Footer ──────────────────────────────────────
                    html.Div(
                        f'MIMIC-IV  ·  Patient Flow & Readmission Analytics Dashboard  ·  {_LAST_REFRESH}',
                        style={
                            'textAlign': 'center', 'fontSize': '10px',
                            'color': '#CBD5E1', 'padding': '20px 0 8px',
                            'fontFamily': _FONT_FAMILY, 'letterSpacing': '.04em',
                        },
                    ),
                ],
                style={'maxWidth': '1600px', 'margin': '0 auto', 'padding': '0 16px 16px'},
            ),
        ],
        style={
            'background': 'linear-gradient(180deg, #F0F4F8 0%, #F8FAFC 100%)',
            'minHeight': '100vh',
            'fontFamily': _FONT_FAMILY,
        },
    ),
    theme={
        'fontFamily': _FONT_FAMILY,
        'primaryColor': 'blue',
        'defaultRadius': 'md',
        'components': {
            'Tabs': {
                'styles': {
                    'tab': {'fontFamily': _FONT_FAMILY, 'fontWeight': '600'},
                }
            }
        },
    },
    forceColorScheme='light',
)


# ══════════════════════════════════════════════════════════════════
#  MASTER CALLBACK — filters → KPI + all 12 graphs
# ══════════════════════════════════════════════════════════════════
@app.callback(
    Output('kpi-total',             'children'),
    Output('kpi-los',               'children'),
    Output('kpi-readmit',           'children'),
    Output('kpi-ed',                'children'),
    Output('kpi-pp',                'children'),
    Output('graph-pp-impact',       'figure'),
    Output('graph-heatmap',         'figure'),
    Output('graph-pp-rq1',          'figure'),
    Output('graph-transfer-readmit','figure'),
    Output('graph-ed-dual',         'figure'),
    Output('graph-days-readmit',    'figure'),
    Output('graph-ed-box',          'figure'),
    Output('graph-bottleneck',      'figure'),
    Output('graph-pareto',          'figure'),
    Output('graph-icd-complexity',  'figure'),
    Output('graph-rq3',             'figure'),
    Output('graph-los-bar',         'figure'),
    Input('age-slider',              'value'),
    Input('gender-dropdown',         'value'),
    Input('diagnosis-dropdown',      'value'),
    Input('frequent-flyers-toggle',  'value'),
)
def update_all(age_range, gender, diagnosis, ff):
    _e = empty_fig("No data")
    if df.empty:
        return ('—',) * 5 + (_e,) * 12

    _df, _pp = apply_filters(df, pp_df, age_range, gender, diagnosis, ff)

    if _df.empty:
        _e2 = empty_fig("No data for selected filters")
        return ('0', '—', '—%', '— hrs', '—%') + (_e2,) * 12

    total   = f"{_df['hadm_id'].nunique():,}"
    los     = _los_label(_df)                            if 'los_days'         in _df else '—'
    readmit = (f"{_df.drop_duplicates(subset=['hadm_id'])['is_readmit'].mean()*100:.1f}%"
               if 'is_readmit' in _df else '—')
    ed      = f"{_df['boarding_hrs_xfer'].mean():.1f} hrs" if 'boarding_hrs_xfer' in _df else '—'
    if not _pp.empty:
        _pp_hadm = _pp[_pp['is_pingpong'] == 1]['hadm_id'].nunique()
        pp_rate  = f"{_pp_hadm / _df['hadm_id'].nunique() * 100:.1f}%"
    else:
        pp_rate = '—'

    pp_fig = make_pingpong_impact(_df, _pp)

    return (
        total, los, readmit, ed, pp_rate,
        pp_fig,
        make_heatmap(_pp),
        pp_fig,
        make_rq1_transfer_readmit(_df),
        make_ed_boarding_dual(_df),
        make_rq2_days_to_readmit(_df),
        make_ed_boarding_box(_df),
        make_bottleneck_ward(_df),
        make_pareto(_df),
        make_rq3_icd_complexity(_df),
        make_rq3_journey(_df),
        make_los_bar(_df),
    )


@app.callback(
    Output('bubble-size-on',  'data'),
    Output('bubble-size-btn', 'children'),
    Output('bubble-size-btn', 'style'),
    Input('bubble-size-btn',  'n_clicks'),
    State('bubble-size-on',   'data'),
    prevent_initial_call=True,
)
def toggle_bubble_size(_, is_on):
    new = not is_on
    return new, ('⬤ Bubble' if new else '◯ Scatter'), (_BUBBLE_BTN_ON if new else _BUBBLE_BTN_OFF)


@app.callback(
    Output('graph-bubble', 'figure'),
    Input('age-slider',             'value'),
    Input('gender-dropdown',        'value'),
    Input('diagnosis-dropdown',     'value'),
    Input('frequent-flyers-toggle', 'value'),
    Input('bubble-size-on',         'data'),
)
def update_bubble_graph(age_range, gender, diagnosis, ff, use_size):
    if df.empty:
        return empty_fig("No data")
    _df, _ = apply_filters(df, pp_df, age_range, gender, diagnosis, ff)
    if _df.empty:
        return empty_fig("No data for selected filters")
    return make_bubble(_df, use_size=bool(use_size))


if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=8050)
