import dash
from dash import dcc, html
import plotly.graph_objects as go
import pandas as pd
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from theme import *

dash.register_page(__name__, path="/", name="Visão Geral")

DADOS = Path(__file__).parent.parent / "dados"
df_mensal = pd.read_parquet(DADOS/"agg_saldo_mensal.parquet").sort_values("ano_mes")
df_uf     = pd.read_parquet(DADOS/"agg_saldo_uf.parquet")
df_setor  = pd.read_parquet(DADOS/"agg_setor_ano.parquet")
df_fase   = pd.read_parquet(DADOS/"agg_saldo_fase.parquet")

MESES_NOME = {1:"Jan",2:"Fev",3:"Mar",4:"Abr",5:"Mai",6:"Jun",
              7:"Jul",8:"Ago",9:"Set",10:"Out",11:"Nov",12:"Dez"}
ORDEM_FASES = ["Pandemia aguda","Pandemia inicial","Pandemia tardia",
               "Recuperação","Normalização","Expansão pós-pandemia"]

saldo_total = int(df_mensal["saldo"].sum())
saldo_2020  = int(df_mensal[df_mensal["ano"]==2020]["saldo"].sum())
saldo_2026  = int(df_mensal[df_mensal["ano"]==2026]["saldo"].sum())
melhor = df_mensal.loc[df_mensal["saldo"].idxmax()]
pior   = df_mensal.loc[df_mensal["saldo"].idxmin()]

fig_tend = go.Figure()
fig_tend.add_bar(
    x=df_mensal["ano_mes"].astype(str), y=df_mensal["saldo"],
    marker_color=[VC if v>=0 else VR for v in df_mensal["saldo"]],
    name="Saldo mensal",
    hovertemplate="<b>%{x}</b><br>Saldo: %{y:,.0f}<extra></extra>"
)
if "media_movel_3m" in df_mensal.columns:
    fig_tend.add_scatter(
        x=df_mensal["ano_mes"].astype(str), y=df_mensal["media_movel_3m"],
        mode="lines", line=dict(color=VD, width=3, dash="dot"),
        name="Média móvel 3m"
    )
fig_tend.add_annotation(
    x="2020-04-01", y=df_mensal["saldo"].min()*0.75,
    text="◀ Pandemia Abr/2020", showarrow=False,
    font=dict(color=AM, size=14, family="DM Sans"), xanchor="left"
)
apply_layout(fig_tend, height=340,
    xaxis=dict(tickangle=-45, nticks=20, tickfont=dict(size=FONT_TICK), gridcolor=BGE),
    yaxis=dict(tickformat=",.0f", tickfont=dict(size=FONT_TICK), gridcolor=BGE),
    legend=dict(orientation="h", y=1.08, x=0, font=dict(size=FONT_LEGEND)),
    hovermode="x unified"
)

df_uf_tot = df_uf.groupby("sigla_uf")["saldo"].sum().reset_index()
fig_mapa = go.Figure(go.Choropleth(
    geojson="https://raw.githubusercontent.com/codeforamerica/click_that_hood/master/public/data/brazil-states.geojson",
    locations=df_uf_tot["sigla_uf"], z=df_uf_tot["saldo"],
    featureidkey="properties.sigla",
    colorscale=[[0,VR],[0.5,BG],[1,VM]], zmid=0,
    text=df_uf_tot["sigla_uf"],
    hovertemplate="<b>%{text}</b><br>Saldo: %{z:,.0f}<extra></extra>",
    colorbar=dict(title=dict(text="Saldo",font=dict(size=14)),
                  tickformat=",.0f", tickfont=dict(size=13), len=0.85, x=1.01)
))
fig_mapa.update_geos(fitbounds="locations", visible=False, bgcolor="rgba(0,0,0,0)")
fig_mapa.update_layout(paper_bgcolor="white", margin=dict(l=0,r=70,t=0,b=0), height=420,
    font=dict(family="DM Sans", size=14))

df_s = df_setor.groupby("setor")["saldo"].sum().reset_index().sort_values("saldo")
fig_set = go.Figure(go.Bar(
    x=df_s["saldo"], y=df_s["setor"], orientation="h",
    marker_color=[VC if v>=0 else VR for v in df_s["saldo"]],
    hovertemplate="<b>%{y}</b><br>%{x:,.0f}<extra></extra>"
))
apply_layout(fig_set, height=460,
    xaxis=dict(tickformat=",.0f", tickfont=dict(size=FONT_TICK), gridcolor=BGE),
    yaxis=dict(tickfont=dict(size=13))
)

df_f = df_fase.groupby("fase_pandemia")["saldo"].sum().reset_index()
df_f["fase_pandemia"] = pd.Categorical(df_f["fase_pandemia"], categories=ORDEM_FASES, ordered=True)
df_f = df_f.sort_values("fase_pandemia")
fig_fase = go.Figure(go.Bar(
    x=df_f["fase_pandemia"].astype(str), y=df_f["saldo"],
    marker_color=[VC if v>=0 else VR for v in df_f["saldo"]],
    hovertemplate="<b>%{x}</b><br>%{y:,.0f}<extra></extra>"
))
apply_layout(fig_fase, height=300,
    xaxis=dict(tickangle=-15, tickfont=dict(size=13), gridcolor=BGE),
    yaxis=dict(tickformat=",.0f", tickfont=dict(size=FONT_TICK), gridcolor=BGE)
)

def card(titulo, desc, fig, height=None):
    return html.Div([
        html.H3(titulo, style=card_title_style()),
        html.P(desc, style=card_desc_style()),
        dcc.Graph(figure=fig, config={"displayModeBar":False},
                  style={"height":height} if height else {})
    ], style=card_style())

layout = html.Div([html.Div([
    html.Div([
        html.H1("Mercado de Trabalho Formal no Brasil", style={
            "fontFamily":"DM Serif Display","fontSize":FONT_TITLE_PAGE,"color":VD,"margin":"0 0 6px 0"}),
        html.P("Impacto da pandemia e recuperação do emprego formal — 2020 a 2026",
            style={"fontFamily":"DM Sans","fontSize":FONT_SUBTITLE,"color":TL,"margin":"0"})
    ], style={"marginBottom":"32px","paddingTop":"32px"}),

    html.Div([
        kpi("Saldo 2020–2026", saldo_total, "admissões − desligamentos", VM),
        kpi("Saldo em 2020", saldo_2020, "ano da pandemia", VR),
        kpi("Saldo em 2026", saldo_2026, "até abril/2026", VC),
        kpi("Melhor mês", int(melhor["saldo"]),
            f"{MESES_NOME[int(melhor['mes'])]}/{int(melhor['ano'])}", VC),
        kpi("Pior mês", int(pior["saldo"]),
            f"{MESES_NOME[int(pior['mes'])]}/{int(pior['ano'])}", VR),
    ], style={"display":"flex","gap":"16px","flexWrap":"wrap","marginBottom":"24px"}),

    html.Div([card(
        "Saldo mensal de empregos formais (2020–2026)",
        "Verde = saldo positivo. Vermelho = mais demissões. Pontilhado = média móvel 3 meses.",
        fig_tend)], style={"marginBottom":"18px"}),

    html.Div([
        html.Div([
            html.H3("Saldo acumulado por UF (2020–2026)", style=card_title_style()),
            html.P("Verde = saldo positivo. Vermelho = saldo negativo no período.", style=card_desc_style()),
            dcc.Graph(figure=fig_mapa, config={"displayModeBar":False})
        ], style={**card_style(),"flex":"3"}),
        html.Div([card(
            "Saldo por fase histórica",
            "Apenas a pandemia aguda (Jan–Jun/2020) resultou em saldo negativo.",
            fig_fase)], style={"flex":"2","display":"flex"})
    ], style={"display":"flex","gap":"18px","flexWrap":"wrap","marginBottom":"18px"}),

    html.Div([card(
        "Saldo acumulado por setor econômico (2020–2026)",
        "Comércio e Serviços Administrativos lideraram a criação de empregos formais.",
        fig_set)], style={"marginBottom":"48px"}),

], style={"maxWidth":"1400px","margin":"0 auto","padding":"0 36px"})
], style={"background":BG,"minHeight":"100vh"})
