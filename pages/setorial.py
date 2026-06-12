# pages/setorial.py — Página de análise por setor econômico (interativa).
# Tem filtros de período e de setores. Mostra a evolução anual de cada
# setor, o crescimento % entre 2020 e 2026 e um heatmap de sazonalidade.

import dash
from dash import dcc, html, callback, Input, Output
import plotly.graph_objects as go
import pandas as pd
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))  # permite importar o theme.py da raiz
from theme import *

dash.register_page(__name__, path="/setorial", name="Setorial")

# Tabelas agregadas usadas nesta página
DADOS = Path(__file__).parent.parent / "dados"
df_setor_ano = pd.read_parquet(DADOS/"agg_setor_ano.parquet")
df_cresc     = pd.read_parquet(DADOS/"agg_crescimento_setor.parquet")
df_mes_ano   = pd.read_parquet(DADOS/"agg_mes_ano.parquet")

SETORES = sorted(df_setor_ano["setor"].unique())
ANOS    = sorted([int(a) for a in df_setor_ano["ano"].unique()])
MESES   = {1:"Jan",2:"Fev",3:"Mar",4:"Abr",5:"Mai",6:"Jun",
           7:"Jul",8:"Ago",9:"Set",10:"Out",11:"Nov",12:"Dez"}

LABEL_STYLE = {"fontFamily":"DM Sans","fontSize":"0.85rem","fontWeight":"600","color":TL,
               "letterSpacing":"0.08em","textTransform":"uppercase","display":"block","marginBottom":"8px"}

# Paleta de cores para diferenciar as linhas de cada setor no gráfico
CORES_LINHA = [VC,"#2980B9","#8E44AD","#E67E22","#16A085",
               VR,"#F39C12","#1ABC9C","#D35400","#7F8C8D",
               "#2C3E50","#27AE60","#C0392B","#3498DB"]

# Layout da página: título, filtros e cards dos gráficos
# (os gráficos são preenchidos pelo callback abaixo)
layout = html.Div([html.Div([
    html.Div([
        html.H1("Análise Setorial", style={
            "fontFamily":"DM Serif Display","fontSize":FONT_TITLE_PAGE,"color":VD,"margin":"0 0 6px 0"}),
        html.P("Evolução do emprego por setor econômico",
            style={"fontFamily":"DM Sans","fontSize":FONT_SUBTITLE,"color":TL,"margin":"0"})
    ], style={"marginBottom":"28px","paddingTop":"32px"}),

    html.Div([
        html.Div([
            html.Label("Período", style=LABEL_STYLE),
            dcc.RangeSlider(id="s-ano", min=min(ANOS), max=max(ANOS), step=1,
                marks={a:str(a) for a in ANOS}, value=[min(ANOS), max(ANOS)],
                tooltip={"placement":"bottom"})
        ], style={"flex":"2","minWidth":"280px"}),
        html.Div([
            html.Label("Setores", style=LABEL_STYLE),
            dcc.Dropdown(id="s-setor",
                options=[{"label":s,"value":s} for s in SETORES],
                multi=True, placeholder="Todos",
                style={"fontFamily":"DM Sans","fontSize":"0.9rem"})
        ], style={"flex":"2","minWidth":"280px"}),
    ], style={"background":"white","border":f"1px solid {BGE}","borderRadius":"8px",
              "padding":"24px","display":"flex","gap":"32px","flexWrap":"wrap","marginBottom":"18px"}),

    html.Div([
        html.H3("Evolução anual do saldo por setor", style=card_title_style()),
        html.P("Selecione setores específicos para comparar trajetórias.", style=card_desc_style()),
        dcc.Graph(id="s-evolucao", config={"displayModeBar":False})
    ], style={**card_style(),"marginBottom":"18px"}),

    html.Div([
        html.Div([
            html.H3("Crescimento % por setor (2020 vs 2026)", style=card_title_style()),
            html.P("Verde = cresceu. Vermelho = regrediu em relação a 2020.", style=card_desc_style()),
            dcc.Graph(id="s-crescimento", config={"displayModeBar":False})
        ], style=card_style()),
        html.Div([
            html.H3("Sazonalidade — heatmap mês × ano", style=card_title_style()),
            html.P("Padrões sazonais do emprego formal. Dezembro concentra admissões no comércio.", style=card_desc_style()),
            dcc.Graph(id="s-heatmap", config={"displayModeBar":False})
        ], style=card_style()),
    ], style={"display":"flex","gap":"18px","flexWrap":"wrap","marginBottom":"48px"}),

], style={"maxWidth":"1400px","margin":"0 auto","padding":"0 36px"})
], style={"background":BG,"minHeight":"100vh"})

# Callback: refaz os 3 gráficos sempre que o usuário muda os filtros
@callback(
    Output("s-evolucao","figure"),
    Output("s-crescimento","figure"),
    Output("s-heatmap","figure"),
    Input("s-ano","value"),
    Input("s-setor","value"),
)
def atualizar(anos, setores):
    # Filtra pelo período e pelos setores escolhidos
    ano_min, ano_max = anos
    ds = df_setor_ano[(df_setor_ano["ano"]>=ano_min)&(df_setor_ano["ano"]<=ano_max)]
    if setores:
        ds = ds[ds["setor"].isin(setores)]

    # Gráfico de linhas: evolução anual do saldo de cada setor
    fig_ev = go.Figure()
    setores_plot = setores if setores else list(ds["setor"].unique())
    for idx, s in enumerate(setores_plot):
        df_s = ds[ds["setor"]==s].sort_values("ano")
        if len(df_s) == 0: continue
        fig_ev.add_scatter(
            x=df_s["ano"], y=df_s["saldo"], mode="lines+markers", name=s,
            line=dict(width=3, color=CORES_LINHA[idx % len(CORES_LINHA)]),
            marker=dict(size=9),
            hovertemplate=f"<b>{s}</b><br>%{{x}}: %{{y:,.0f}}<extra></extra>"
        )
    apply_layout(fig_ev, height=400,
        xaxis=dict(dtick=1, tickfont=dict(size=FONT_TICK), gridcolor=BGE),
        yaxis=dict(tickformat=",.0f", tickfont=dict(size=FONT_TICK), gridcolor=BGE),
        legend=dict(orientation="h", y=-0.22, x=0, font=dict(size=13)),
        hovermode="x unified"
    )

    # Barras horizontais: crescimento % de cada setor (2020 vs 2026)
    dc = df_cresc.copy()
    if setores: dc = dc[dc["setor"].isin(setores)]
    dc = dc.sort_values("variacao_pct")
    fig_cresc = go.Figure(go.Bar(
        x=dc["variacao_pct"], y=dc["setor"], orientation="h",
        marker_color=[VC if v>=0 else VR for v in dc["variacao_pct"]],
        hovertemplate="<b>%{y}</b><br>%{x:.1f}%<extra></extra>",
        text=[f"{v:+.1f}%" for v in dc["variacao_pct"]],
        textposition="outside", textfont=dict(size=13)
    ))
    apply_layout(fig_cresc, height=480,
        xaxis=dict(ticksuffix="%", tickfont=dict(size=FONT_TICK), gridcolor=BGE),
        yaxis=dict(tickfont=dict(size=13)),
        margin=dict(l=10,r=80,t=10,b=10)
    )

    # Heatmap mês × ano: mostra a sazonalidade do emprego formal
    dm = df_mes_ano[(df_mes_ano["ano"]>=ano_min)&(df_mes_ano["ano"]<=ano_max)].copy()
    dm["mes_nome"] = dm["mes"].map(MESES)
    pivot = dm.pivot_table(index="ano", columns="mes_nome", values="saldo", aggfunc="sum")
    ordem = [MESES[m] for m in range(1,13) if MESES[m] in pivot.columns]
    pivot = pivot[ordem]

    fig_heat = go.Figure(go.Heatmap(
        z=pivot.values, x=pivot.columns.tolist(),
        y=pivot.index.astype(str).tolist(),
        colorscale=[[0,VR],[0.5,BGE],[1,VM]], zmid=0,
        hovertemplate="Ano: %{y}<br>Mês: %{x}<br>Saldo: %{z:,.0f}<extra></extra>",
        colorbar=dict(title=dict(text="Saldo",font=dict(size=14)),
                      tickformat=",.0f", tickfont=dict(size=13))
    ))
    fig_heat.update_layout(paper_bgcolor="white", font=dict(family="DM Sans",size=14),
        margin=dict(l=10,r=80,t=10,b=10), height=480,
        xaxis=dict(tickfont=dict(size=14)),
        yaxis=dict(tickfont=dict(size=14))
    )
    return fig_ev, fig_cresc, fig_heat
