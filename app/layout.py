from datetime import datetime

import dash_mantine_components as dmc
from dash import dcc, html

from .constants import (
    C_AMBER, C_BLUE, C_CYAN, C_ORANGE, C_PURPLE, C_TEAL,
    CHART_H, CHORD_HTML, _BUBBLE_BTN_ON, _FONT_FAMILY,
)
from .data import (
    DIAGNOSIS_OPTIONS, HAS_AGE, HAS_GENDER,
    KPI_ED, KPI_LOS, KPI_PP, KPI_READMIT, KPI_TOTAL,
)
from .figures import (
    fig_bottleneck, fig_bubble, fig_days_readmit, fig_ed_box,
    fig_ed_dual, fig_heatmap, fig_icd_complexity, fig_los_bar,
    fig_pareto, fig_pp_impact, fig_rq3, fig_transfer_readmit,
)

# ── Layout-only style constants ───────────────────────────────────
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

_LAST_REFRESH = datetime.now().strftime('%d %b %Y, %H:%M')


# ── UI component helpers ──────────────────────────────────────────
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
                    [html.Span(icon, style={'fontSize': '18px', 'lineHeight': '1'})],
                    style={
                        'width': '36px', 'height': '36px', 'borderRadius': '10px',
                        'background': bg, 'display': 'flex', 'alignItems': 'center',
                        'justifyContent': 'center', 'flexShrink': '0',
                    },
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
    colors = {
        'blue':   ('#EFF6FF', '#1D4ED8', '#BFDBFE'),
        'orange': ('#FFF7ED', '#C2410C', '#FED7AA'),
        'green':  ('#F0FDF4', '#15803D', '#BBF7D0'),
    }
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


# ── App layout ────────────────────────────────────────────────────
def register_layout(app):
    app.layout = dmc.MantineProvider(
        html.Div(
            [
                # Header
                html.Div(
                    html.Div(
                        [
                            html.Div(
                                [
                                    html.Div('🏥', style={
                                        'fontSize': '28px', 'lineHeight': '1',
                                        'marginRight': '14px',
                                        'filter': 'drop-shadow(0 2px 4px rgba(0,0,0,.3))',
                                    }),
                                    html.Div([
                                        html.Div(
                                            'PATIENT FLOW & READMISSION ANALYTICS',
                                            style={
                                                'fontFamily': _FONT_FAMILY,
                                                'fontSize': '15px', 'fontWeight': '800',
                                                'color': '#FFFFFF', 'letterSpacing': '.06em',
                                                'lineHeight': '1.2',
                                            },
                                        ),
                                        html.Div(
                                            'MIMIC-IV Clinical Dataset  ·  Hospital Operations Intelligence',
                                            style={
                                                'fontFamily': _FONT_FAMILY,
                                                'fontSize': '10px', 'fontWeight': '400',
                                                'color': 'rgba(255,255,255,.55)',
                                                'letterSpacing': '.04em', 'marginTop': '2px',
                                            },
                                        ),
                                    ]),
                                ],
                                style={'display': 'flex', 'alignItems': 'center'},
                            ),
                            html.Div([
                                html.Div([
                                    html.Span(style={
                                        'width': '7px', 'height': '7px', 'borderRadius': '50%',
                                        'background': '#4ADE80', 'display': 'inline-block',
                                        'marginRight': '6px', 'flexShrink': '0',
                                        'boxShadow': '0 0 6px #4ADE80',
                                    }),
                                    html.Span(f'Live  ·  {_LAST_REFRESH}',
                                              style={'fontSize': '10px',
                                                     'color': 'rgba(255,255,255,.6)',
                                                     'fontFamily': _FONT_FAMILY}),
                                ], style={'display': 'flex', 'alignItems': 'center'}),
                            ]),
                        ],
                        style={
                            'maxWidth': '1600px', 'margin': '0 auto',
                            'display': 'flex', 'alignItems': 'center',
                            'justifyContent': 'space-between', 'padding': '0 20px',
                        },
                    ),
                    style={
                        'background': 'linear-gradient(135deg, #0A1628 0%, #0D2A5E 60%, #0F4C81 100%)',
                        'padding': '18px 0',
                        'borderBottom': '1px solid rgba(255,255,255,.08)',
                        'boxShadow': '0 4px 20px rgba(10,22,40,.4)',
                        'marginBottom': '16px',
                    },
                ),

                html.Div(
                    [
                        dcc.Store(id='bubble-size-on', data=True),

                        # KPI row
                        dmc.Grid(
                            [
                                kpi_card('Total Admissions',   'kpi-total',   KPI_TOTAL,
                                         '📋', '#EFF6FF', C_BLUE,   C_BLUE),
                                kpi_card('Median / Avg LOS',   'kpi-los',     KPI_LOS,
                                         '🛏️', '#F0FDF4', C_TEAL,   C_TEAL),
                                kpi_card('30-Day Readmission', 'kpi-readmit', KPI_READMIT,
                                         '🔁', '#FFF1F0', C_ORANGE, C_ORANGE),
                                kpi_card('Avg ED Boarding',    'kpi-ed',      KPI_ED,
                                         '⏱️', '#FFFBEB', C_AMBER,  C_AMBER),
                                kpi_card('Ping-Pong Rate',     'kpi-pp',      KPI_PP,
                                         '🏓', '#F5F3FF', C_PURPLE, C_PURPLE),
                            ],
                            gutter='sm', mb='md',
                        ),

                        # Filter bar
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
                                                html.Div(
                                                    [
                                                        html.Div('DIAGNOSIS (ICD)', style={
                                                            'fontSize': '9px', 'fontWeight': '700',
                                                            'color': '#64748B', 'letterSpacing': '.06em',
                                                            'marginBottom': '6px', 'fontFamily': _FONT_FAMILY,
                                                        }),
                                                        dcc.Dropdown(
                                                            id='diagnosis-dropdown',
                                                            options=DIAGNOSIS_OPTIONS,
                                                            value='all', clearable=False,
                                                            style={'fontSize': '12px', 'minWidth': '220px'},
                                                        ),
                                                    ],
                                                    style={'flex': '0 0 230px'},
                                                ),
                                                html.Div(
                                                    [
                                                        html.Div('AGE GROUP', style={
                                                            'fontSize': '9px', 'fontWeight': '700',
                                                            'color': '#64748B', 'letterSpacing': '.06em',
                                                            'marginBottom': '6px', 'fontFamily': _FONT_FAMILY,
                                                        }),
                                                        dcc.RangeSlider(
                                                            id='age-slider', min=1, max=120,
                                                            value=[1, 120],
                                                            marks={1: '1', 20: '20', 40: '40',
                                                                   60: '60', 80: '80', 100: '100', 120: '120'},
                                                            tooltip={"placement": "bottom", "always_visible": True},
                                                            step=1, disabled=not HAS_AGE,
                                                        ),
                                                    ],
                                                    style={'flex': '1', 'minWidth': '220px'},
                                                ),
                                                html.Div(
                                                    [
                                                        html.Div('GENDER', style={
                                                            'fontSize': '9px', 'fontWeight': '700',
                                                            'color': '#64748B', 'letterSpacing': '.06em',
                                                            'marginBottom': '6px', 'fontFamily': _FONT_FAMILY,
                                                        }),
                                                        dcc.Dropdown(
                                                            id='gender-dropdown',
                                                            options=[
                                                                {'label': 'All Genders', 'value': 'all'},
                                                                {'label': 'Male',        'value': 'M'},
                                                                {'label': 'Female',      'value': 'F'},
                                                            ],
                                                            value='all', clearable=False,
                                                            disabled=not HAS_GENDER,
                                                            style={'fontSize': '12px', 'minWidth': '130px'},
                                                        ),
                                                    ],
                                                    style={'flex': '0 0 140px'},
                                                ),
                                                html.Div(
                                                    [
                                                        html.Div(' ', style={
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
                                'padding': '16px 20px', 'marginBottom': '16px',
                                'background': '#FAFBFF', 'borderLeft': '4px solid #C7D2FE',
                            },
                        ),

                        # Tabs
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
                                    style={'borderBottom': '2px solid #EEF2F7', 'gap': '4px'},
                                ),

                                # Overview tab
                                dmc.TabsPanel(
                                    dmc.Grid(
                                        [
                                            dmc.GridCol(
                                                dmc.Stack(
                                                    [
                                                        html.Div(
                                                            [
                                                                html.Div('Macro-Level Patient Flow',
                                                                         style=_CHART_TITLE_STYLE),
                                                                html.Iframe(
                                                                    srcDoc=CHORD_HTML,
                                                                    style={'width': '100%', 'height': '520px',
                                                                           'border': 'none'},
                                                                ),
                                                            ],
                                                            style={
                                                                **_CARD_STYLE, 'padding': '16px',
                                                                'borderTop': f'3px solid {C_BLUE}',
                                                            },
                                                        ),
                                                    ],
                                                    gap='sm',
                                                ),
                                                span=5,
                                            ),
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
                                                            style={**_CARD_STYLE,
                                                                   'borderTop': f'3px solid {C_CYAN}',
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

                                # RQ1 tab
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
                                                    gcol('graph-heatmap', fig_heatmap,   6, C_BLUE),
                                                    gcol('graph-pp-rq1',  fig_pp_impact, 6, C_PURPLE),
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

                                # RQ2 tab
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

                                # RQ3 tab
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
                                                    gcol('graph-pareto',         fig_pareto,         6, C_TEAL),
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

                        # Footer
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
                'Tabs': {'styles': {'tab': {'fontFamily': _FONT_FAMILY, 'fontWeight': '600'}}}
            },
        },
        forceColorScheme='light',
    )
