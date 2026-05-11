import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .constants import (
    CHART_H, CHART_MARGIN, CHART_MARGIN_CB, TARGET_ORDER,
    UNIT_MAP, UNIT_MAP_DETAIL, _FONT_FAMILY, _base_layout,
    C_BLUE, C_TEAL, C_ORANGE, C_AMBER, C_PURPLE, C_CYAN,
)
from .data import df, dfc_ed, pp_df


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
    fig.update_yaxes(title_text='Total Patients',       secondary_y=False,
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
    fig.update_yaxes(title_text='Total Bed Days', secondary_y=False,
                     title_font=dict(size=10, color='#607D8B'))
    fig.update_yaxes(title_text='Cumulative %',   secondary_y=True,
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
            'Normal Patient':      '#29B6F6',
            'Readmitted ≤30 Days': '#EF5350',
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
    readmit['next_in']         = pd.to_datetime(readmit['next_in'],  errors='coerce')
    readmit['adm_out']         = pd.to_datetime(readmit['adm_out'],  errors='coerce')
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
    groups = ['ED', 'ED Obs', 'ICU', 'Medicine', 'Surgery / Procedural', 'Specialist Ward', 'Maternity']
    matrix = [
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
    fig = make_subplots(rows=1, cols=2, column_widths=[0.6, 0.4], horizontal_spacing=0.10)
    fig.add_trace(go.Bar(
        name='Inflow', y=groups, x=inflow, orientation='h',
        marker=dict(color=bar_colors, opacity=0.85, line_width=0),
        hovertemplate='<b>%{y}</b><br>Inflow: %{x:,}<extra></extra>',
    ), row=1, col=1)
    fig.add_trace(go.Bar(
        name='Outflow', y=groups, x=[-v for v in outflow], orientation='h',
        marker=dict(color=bar_colors, opacity=0.40, line_width=0, pattern_shape='/'),
        hovertemplate='<b>%{y}</b><br>Outflow: %{customdata:,}<extra></extra>',
        customdata=outflow,
    ), row=1, col=1)
    fig.add_trace(go.Bar(
        name='Net Flow', y=groups, x=net, orientation='h',
        showlegend=False,
        marker=dict(color=net_colors, opacity=0.85, line_width=0),
        hovertemplate='<b>%{y}</b><br>Net: %{x:+,}<extra></extra>',
    ), row=1, col=2)
    fig.add_vline(x=0, line_width=1, line_color='#90A4AE', row=1, col=2)
    fig.update_layout(
        font=dict(family=_FONT_FAMILY, size=10, color='#455A64'),
        paper_bgcolor='#FFFFFF', plot_bgcolor='#F8FBFF',
        height=230, margin=dict(l=10, r=10, t=32, b=8),
        barmode='overlay', bargap=0.3,
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


# ── Pre-built figures (computed once at startup) ──────────────────
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
