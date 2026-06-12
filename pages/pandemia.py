# pages/pandemia.py — Página focada no impacto da pandemia.
# Mostra o "zoom" no período 2019–2022, o impacto por setor em cada
# fase histórica (heatmap), a comparação regional e a recuperação
# setorial entre 2020, 2021 e 2022.

import dash
from dash import dcc, html
import plotly.graph_objects as go
import pandas as pd
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))  # permite importar o theme.py da raiz
from theme import *

dash.register_page(__name__, path="/pandemia", name="Pandemia")

# Tabelas agregadas usadas nesta página
DADOS = Path(__file__).parent.parent / "dados"
df_mensal    = pd.read_parquet(DADOS/"agg_saldo_mensal.parquet").sort_values("ano_mes")
df_fase      = pd.read_parquet(DADOS/"agg_saldo_fase.parquet")
df_setor_ano = pd.read_parquet(DADOS/"agg_setor_ano.parquet")
df_uf        = pd.read_parquet(DADOS/"agg_saldo_uf.parquet")

MESES_NOME = {1:"Jan",2:"Fev",3:"Mar",4:"Abr",5:"Mai",6:"Jun",
              7:"Jul",8:"Ago",9:"Set",10:"Out",11:"Nov",12:"Dez"}
ORDEM_FASES = ["Pandemia aguda","Pandemia inicial","Pandemia tardia",
               "Recuperação","Normalização","Expansão pós-pandemia"]
CORES_FASES = {
    "Pandemia aguda":VR, "Pandemia inicial":"#E74C3C",
    "Pandemia (2020)":VR,
    "Pandemia tardia":AM, "Recuperação":"#F0B429",
    "Normalização":VC, "Expansão pós-pandemia":VM,
}
ORDEM_FASES_REG = ["Pandemia (2020)", "Pandemia tardia", "Recuperação", "Normalização", "Expansão pós-pandemia"]

# Números dos KPIs: saldo durante e depois da pandemia, melhor e pior mês
saldo_pandemia = int(df_mensal[df_mensal["ano"].isin([2020,2021])]["saldo"].sum())
saldo_pos_pan  = int(df_mensal[df_mensal["ano"].isin([2022,2023,2024,2025,2026])]["saldo"].sum())
melhor = df_mensal.loc[df_mensal["saldo"].idxmax()]
pior   = df_mensal.loc[df_mensal["saldo"].idxmin()]

# Gráfico "zoom": saldo mensal só do período 2019–2022,
# com uma seta destacando o pior mês (abril/2020)
df_pan = df_mensal[df_mensal["ano"].isin([2019,2020,2021,2022])].copy()
fig_zoom = go.Figure()
fig_zoom.add_bar(
    x=df_pan["ano_mes"].astype(str), y=df_pan["saldo"],
    marker_color=[VC if v>=0 else VR for v in df_pan["saldo"]],
    hovertemplate="<b>%{x}</b><br>%{y:,.0f}<extra></extra>"
)
fig_zoom.add_annotation(
    x="2020-04-01", y=int(df_pan["saldo"].min())*0.7,
    text=f"Pior mês: {MESES_NOME[int(pior['mes'])]}/{int(pior['ano'])}<br>{int(pior['saldo']):,.0f}",
    showarrow=True, arrowhead=2, arrowcolor=VR, arrowwidth=2,
    font=dict(color=VR, size=14, family="DM Sans"),
    bgcolor="white", bordercolor=VR, borderwidth=1.5
)
apply_layout(fig_zoom, height=340,
    xaxis=dict(tickangle=-45, tickfont=dict(size=FONT_TICK), gridcolor=BGE),
    yaxis=dict(tickformat=",.0f", tickfont=dict(size=FONT_TICK), gridcolor=BGE)
)

# Heatmap setor × fase: vermelho = perdeu empregos, verde = ganhou
pivot_fase = df_fase.pivot_table(index="setor", columns="fase_pandemia", values="saldo", aggfunc="sum")
cols_ord = [f for f in ORDEM_FASES if f in pivot_fase.columns]
pivot_fase = pivot_fase[cols_ord]
fig_heat = go.Figure(go.Heatmap(
    z=pivot_fase.values, x=pivot_fase.columns.tolist(), y=pivot_fase.index.tolist(),
    colorscale=[[0,VR],[0.5,BGE],[1,VM]], zmid=0,
    hovertemplate="<b>%{y}</b><br>%{x}<br>%{z:,.0f}<extra></extra>",
    colorbar=dict(title=dict(text="Saldo",font=dict(size=14)),
                  tickformat=",.0f", tickfont=dict(size=13))
))
fig_heat.update_layout(paper_bgcolor="white", font=dict(family="DM Sans",size=14),
    margin=dict(l=10,r=80,t=10,b=10), height=460,
    xaxis=dict(tickangle=-20, tickfont=dict(size=13)),
    yaxis=dict(tickfont=dict(size=13))
)

# Barras agrupadas comparando cada setor em 2020, 2021 e 2022
df_comp = df_setor_ano[df_setor_ano["ano"].isin([2020,2021,2022])].copy()
CORES_ANO = {2020:VR, 2021:AM, 2022:VC}
fig_comp = go.Figure()
for ano in [2020,2021,2022]:
    df_a = df_comp[df_comp["ano"]==ano].sort_values("saldo")
    fig_comp.add_bar(
        name=str(ano), x=df_a["saldo"], y=df_a["setor"],
        orientation="h", marker_color=CORES_ANO[ano],
        hovertemplate=f"<b>%{{y}}</b><br>{ano}: %{{x:,.0f}}<extra></extra>"
    )
apply_layout(fig_comp, height=520, barmode="group",
    xaxis=dict(tickformat=",.0f", tickfont=dict(size=FONT_TICK), gridcolor=BGE),
    yaxis=dict(tickfont=dict(size=13)),
    legend=dict(orientation="h", y=1.04, x=0, font=dict(size=14))
)

# Saldo por região em cada fase: agrupa as UFs por região
# e classifica cada ano em uma fase histórica
REGIOES_UF = {
    "Norte":["AC","AM","AP","PA","RO","RR","TO"],
    "Nordeste":["AL","BA","CE","MA","PB","PE","PI","RN","SE"],
    "Sudeste":["ES","MG","RJ","SP"],
    "Sul":["PR","RS","SC"],
    "Centro-Oeste":["DF","GO","MS","MT"],
}
UF_REGIAO = {u:r for r,ufs in REGIOES_UF.items() for u in ufs}
df_ur = df_uf.copy()
df_ur["regiao"] = df_ur["sigla_uf"].map(UF_REGIAO)
df_ur["fase"] = df_ur["ano"].map({
    2020: "Pandemia (2020)",
    2021: "Pandemia tardia",
    2022: "Recuperação",
    2023: "Normalização",
}).fillna("Expansão pós-pandemia")
df_reg = df_ur.groupby(["regiao","fase"])["saldo"].sum().reset_index()
fig_reg = go.Figure()
for fase in ORDEM_FASES_REG:
    df_f = df_reg[df_reg["fase"]==fase]
    if len(df_f)==0: continue
    fig_reg.add_bar(
        name=fase, x=df_f["regiao"], y=df_f["saldo"],
        marker_color=CORES_FASES.get(fase, VC),
        hovertemplate=f"<b>%{{x}}</b><br>{fase}: %{{y:,.0f}}<extra></extra>"
    )
apply_layout(fig_reg, height=360, barmode="group",
    xaxis=dict(tickfont=dict(size=14), gridcolor=BGE),
    yaxis=dict(tickformat=",.0f", tickfont=dict(size=FONT_TICK), gridcolor=BGE),
    legend=dict(orientation="h", y=-0.28, x=0, font=dict(size=12))
)

# Layout da página: título, KPIs e os cards com os gráficos
layout = html.Div([html.Div([
    html.Div([
        html.H1("Pandemia & Recuperação", style={
            "fontFamily":"DM Serif Display","fontSize":FONT_TITLE_PAGE,"color":VD,"margin":"0 0 6px 0"}),
        html.P("Do colapso de 2020 à expansão histórica de 2025–2026",
            style={"fontFamily":"DM Sans","fontSize":FONT_SUBTITLE,"color":TL,"margin":"0"})
    ], style={"marginBottom":"28px","paddingTop":"32px"}),

    html.Div([
        kpi("Saldo pandemia", saldo_pandemia, "2020 + 2021", VR),
        kpi("Saldo pós-pandemia", saldo_pos_pan, "2022–2026", VC),
        kpi("Pior mês", int(pior["saldo"]),
            f"{MESES_NOME[int(pior['mes'])]}/{int(pior['ano'])}", VR),
        kpi("Melhor mês", int(melhor["saldo"]),
            f"{MESES_NOME[int(melhor['mes'])]}/{int(melhor['ano'])}", VC),
        kpi("Saldo líquido", saldo_pos_pan+saldo_pandemia, "2020–2026", VM),
    ], style={"display":"flex","gap":"16px","flexWrap":"wrap","marginBottom":"24px"}),

    html.Div([
        html.H3("Zoom: impacto imediato da pandemia (2019–2022)", style=card_title_style()),
        html.P("Abril/2020 foi o pior mês da série histórica do Novo CAGED.", style=card_desc_style()),
        dcc.Graph(figure=fig_zoom, config={"displayModeBar":False})
    ], style={**card_style(),"marginBottom":"18px"}),

    html.Div([
        html.Div([
            html.H3("Impacto por setor em cada fase histórica", style=card_title_style()),
            html.P("Quais setores sofreram mais e quais lideraram a recuperação.", style=card_desc_style()),
            dcc.Graph(figure=fig_heat, config={"displayModeBar":False})
        ], style={**card_style(),"flex":"3"}),
        html.Div([
            html.H3("Saldo por região por fase", style=card_title_style()),
            html.P("Comparação regional ao longo das fases históricas.", style=card_desc_style()),
            dcc.Graph(figure=fig_reg, config={"displayModeBar":False})
        ], style={**card_style(),"flex":"2"}),
    ], style={"display":"flex","gap":"18px","flexWrap":"wrap","marginBottom":"18px"}),

    html.Div([
        html.H3("Recuperação por setor — 2020 vs 2021 vs 2022", style=card_title_style()),
        html.P("Veja como cada setor se comportou no ano da pandemia, na transição e na recuperação.", style=card_desc_style()),
        dcc.Graph(figure=fig_comp, config={"displayModeBar":False})
    ], style={**card_style(),"marginBottom":"48px"}),

], style={"maxWidth":"1400px","margin":"0 auto","padding":"0 36px"})
], style={"background":BG,"minHeight":"100vh"})
