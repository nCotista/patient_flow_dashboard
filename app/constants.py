import json

# ── External assets ───────────────────────────────────────────────
EXTERNAL_STYLESHEETS = [
    "https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap"
]

# ── Unit mapping ──────────────────────────────────────────────────
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

# ── Colour palette ────────────────────────────────────────────────
C_NAVY   = '#0D1B3E'
C_BLUE   = '#1565C0'
C_TEAL   = '#00695C'
C_ORANGE = '#BF360C'
C_AMBER  = '#E65100'
C_PURPLE = '#4527A0'
C_CYAN   = '#006064'

KPI_BG = ['#E3F2FD', '#E0F2F1', '#FBE9E7', '#FFF3E0', '#EDE7F6']
KPI_FG = [C_BLUE,    C_TEAL,    C_ORANGE,  C_AMBER,   C_PURPLE]

# ── Chart defaults ────────────────────────────────────────────────
CHART_H      = 360
CHART_MARGIN    = dict(l=10, r=20, t=52, b=20)
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


# ── Chord diagram data ────────────────────────────────────────────
CHORD_GROUPS = ['ED', 'ED Obs', 'ICU', 'Medicine',
                'Surgery / Procedural', 'Specialist Ward', 'Maternity']
CHORD_COLORS = {
    'ED':                   '#1565C0',
    'ED Obs':               '#29B6F6',
    'ICU':                  '#BF360C',
    'Medicine':             '#2E7D32',
    'Surgery / Procedural': '#6A1B9A',
    'Specialist Ward':      '#F57F17',
    'Maternity':            '#00695C',
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
    document.getElementById('ss2').textContent='ICU → Medicine';
    document.getElementById('hint').textContent='Click a ward segment to inspect its flow details';
    document.querySelectorAll('.litem').forEach(el=>el.classList.remove('active'));
  }} else {{
    const g=G[idx],col=C[g];
    const inflow=M.reduce((s,r,j)=>s+(j!==idx?r[idx]:0),0);
    const outflow=M[idx].reduce((s,v,j)=>s+(j!==idx?v:0),0);
    const net=inflow-outflow;
    const netCol=net>0?'#2E7D32':net<0?'#C62828':'#607D8B';
    const netSign=net>0?'+':'';
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
    tip(e,`<b>${{s}} ↔ ${{t}}</b><br>${{s}} → ${{t}}: ${{M[d.source.index][d.target.index].toLocaleString()}}<br>${{t}} → ${{s}}: ${{M[d.target.index][d.source.index].toLocaleString()}}`)}})
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
