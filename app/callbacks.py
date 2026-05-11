import pandas as pd
from dash import Input, Output, State

from .constants import _BUBBLE_BTN_OFF, _BUBBLE_BTN_ON
from .data import HAS_AGE, HAS_GENDER, df, pp_df
from .data import _los_label
from .figures import (
    empty_fig,
    make_bottleneck_ward,
    make_bubble,
    make_ed_boarding_box,
    make_ed_boarding_dual,
    make_heatmap,
    make_los_bar,
    make_pareto,
    make_pingpong_impact,
    make_rq1_transfer_readmit,
    make_rq2_days_to_readmit,
    make_rq3_icd_complexity,
    make_rq3_journey,
)


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


def register_callbacks(app):
    @app.callback(
        Output('kpi-total',              'children'),
        Output('kpi-los',                'children'),
        Output('kpi-readmit',            'children'),
        Output('kpi-ed',                 'children'),
        Output('kpi-pp',                 'children'),
        Output('graph-pp-impact',        'figure'),
        Output('graph-heatmap',          'figure'),
        Output('graph-pp-rq1',           'figure'),
        Output('graph-transfer-readmit', 'figure'),
        Output('graph-ed-dual',          'figure'),
        Output('graph-days-readmit',     'figure'),
        Output('graph-ed-box',           'figure'),
        Output('graph-bottleneck',       'figure'),
        Output('graph-pareto',           'figure'),
        Output('graph-icd-complexity',   'figure'),
        Output('graph-rq3',              'figure'),
        Output('graph-los-bar',          'figure'),
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
        los     = _los_label(_df)                                   if 'los_days'         in _df else '—'
        readmit = (f"{_df.drop_duplicates(subset=['hadm_id'])['is_readmit'].mean()*100:.1f}%"
                   if 'is_readmit' in _df else '—')
        ed      = f"{_df['boarding_hrs_xfer'].mean():.1f} hrs"      if 'boarding_hrs_xfer' in _df else '—'
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
        Output('graph-bubble',           'figure'),
        Input('age-slider',              'value'),
        Input('gender-dropdown',         'value'),
        Input('diagnosis-dropdown',      'value'),
        Input('frequent-flyers-toggle',  'value'),
        Input('bubble-size-on',          'data'),
    )
    def update_bubble_graph(age_range, gender, diagnosis, ff, use_size):
        if df.empty:
            return empty_fig("No data")
        _df, _ = apply_filters(df, pp_df, age_range, gender, diagnosis, ff)
        if _df.empty:
            return empty_fig("No data for selected filters")
        return make_bubble(_df, use_size=bool(use_size))
