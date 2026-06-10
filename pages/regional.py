import dash
from dash import dcc, html, callback, Input, Output
import plotly.graph_objects as go
import pandas as pd
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from theme import *

dash.register_page(__name__, path="/regional", name="Regional")

DADOS = Path(__file__).parent.parent / "dados"
df_uf  = pd.read_parquet(DADOS/"agg_saldo_uf.parquet")
df_mun = pd.read_parquet(DADOS/"agg_municipios.parquet")

REGIOES_UF = {
    "Norte":       ["AC","AM","AP","PA","RO","RR","TO"],
    "Nordeste":    ["AL","BA","CE","MA","PB","PE","PI","RN","SE"],
    "Sudeste":     ["ES","MG","RJ","SP"],
    "Sul":         ["PR","RS","SC"],
    "Centro-Oeste":["DF","GO","MS","MT"],
}
ANOS = sorted([int(a) for a in df_uf["ano"].unique()])

LABEL_STYLE = {"fontFamily":"DM Sans","fontSize":"0.85rem","fontWeight":"600","color":TL,
               "letterSpacing":"0.08em","textTransform":"uppercase","display":"block","marginBottom":"8px"}
DROP_STYLE  = {"fontFamily":"DM Sans","fontSize":"0.9rem"}

layout = html.Div([html.Div([
    html.Div([
        html.H1("Análise Regional", style={
            "fontFamily":"DM Serif Display","fontSize":FONT_TITLE_PAGE,"color":VD,"margin":"0 0 6px 0"}),
        html.P("Explore o emprego formal por estado e município",
            style={"fontFamily":"DM Sans","fontSize":FONT_SUBTITLE,"color":TL,"margin":"0"})
    ], style={"marginBottom":"28px","paddingTop":"32px"}),

    html.Div([
        html.Div([
            html.Label("Período", style=LABEL_STYLE),
            dcc.RangeSlider(id="r-ano", min=min(ANOS), max=max(ANOS), step=1,
                marks={a:str(a) for a in ANOS}, value=[min(ANOS), max(ANOS)],
                tooltip={"placement":"bottom"})
        ], style={"flex":"2","minWidth":"280px"}),
        html.Div([
            html.Label("Região", style=LABEL_STYLE),
            dcc.Dropdown(id="r-regiao",
                options=[{"label":r,"value":r} for r in REGIOES_UF],
                multi=True, placeholder="Todas", style=DROP_STYLE)
        ], style={"flex":"1","minWidth":"180px"}),
        html.Div([
            html.Label("Estado (ou clique no mapa)", style=LABEL_STYLE),
            dcc.Dropdown(id="r-uf",
                options=[{"label":u,"value":u} for u in sorted(df_uf["sigla_uf"].unique())],
                placeholder="Selecione", style=DROP_STYLE)
        ], style={"flex":"1","minWidth":"180px"}),
    ], style={"background":"white","border":f"1px solid {BGE}","borderRadius":"8px",
              "padding":"24px","display":"flex","gap":"32px","flexWrap":"wrap","marginBottom":"18px"}),

    html.Div([
        html.Div([
            html.H3("Mapa interativo — clique em um estado para detalhar", style=card_title_style()),
            html.P("O mapa reflete o período selecionado acima.", style=card_desc_style()),
            dcc.Graph(id="r-mapa", config={"displayModeBar":False})
        ], style={**card_style(),"flex":"3"}),
        html.Div([
            html.H3("Ranking por estado", style=card_title_style()),
            html.P("Maiores saldos positivos e negativos.", style=card_desc_style()),
            dcc.Graph(id="r-ranking-uf", config={"displayModeBar":False})
        ], style={**card_style(),"flex":"2"}),
    ], style={"display":"flex","gap":"18px","flexWrap":"wrap","marginBottom":"18px"}),

    html.Div([
        html.Div([
            html.H3("Top 10 — maiores criadores de emprego", style=card_title_style()),
            html.P("Municípios com maior saldo positivo no período.", style=card_desc_style()),
            dcc.Graph(id="r-top-mun-pos", config={"displayModeBar":False})
        ], style=card_style()),
        html.Div([
            html.H3("Top 10 — maiores destruidores de emprego", style=card_title_style()),
            html.P("Municípios com maior saldo negativo no período.", style=card_desc_style()),
            dcc.Graph(id="r-top-mun-neg", config={"displayModeBar":False})
        ], style=card_style()),
    ], style={"display":"flex","gap":"18px","flexWrap":"wrap","marginBottom":"48px"}),

], style={"maxWidth":"1400px","margin":"0 auto","padding":"0 36px"})
], style={"background":BG,"minHeight":"100vh"})

@callback(
    Output("r-mapa","figure"), Output("r-ranking-uf","figure"),
    Output("r-top-mun-pos","figure"), Output("r-top-mun-neg","figure"),
    Output("r-uf","value"),
    Input("r-ano","value"), Input("r-regiao","value"),
    Input("r-mapa","clickData"), Input("r-uf","value"),
)
def atualizar(anos, regioes, click, uf_sel):
    ano_min, ano_max = anos
    if click and click.get("points"):
        uf_sel = click["points"][0].get("location", uf_sel)

    du = df_uf[(df_uf["ano"]>=ano_min)&(df_uf["ano"]<=ano_max)]
    if regioes:
        ufs_f = [u for r in regioes for u in REGIOES_UF.get(r,[])]
        du = du[du["sigla_uf"].isin(ufs_f)]
    du_tot = du.groupby("sigla_uf")["saldo"].sum().reset_index()

    fig_mapa = go.Figure(go.Choropleth(
        geojson="https://raw.githubusercontent.com/codeforamerica/click_that_hood/master/public/data/brazil-states.geojson",
        locations=du_tot["sigla_uf"], z=du_tot["saldo"],
        featureidkey="properties.sigla",
        colorscale=[[0,VR],[0.5,BG],[1,VM]], zmid=0,
        text=du_tot["sigla_uf"],
        hovertemplate="<b>%{text}</b><br>Saldo: %{z:,.0f}<extra></extra>",
        colorbar=dict(title=dict(text="Saldo",font=dict(size=14)),
                      tickformat=",.0f", tickfont=dict(size=13), len=0.85)
    ))
    fig_mapa.update_geos(fitbounds="locations", visible=False, bgcolor="rgba(0,0,0,0)")
    fig_mapa.update_layout(paper_bgcolor="white", margin=dict(l=0,r=70,t=0,b=0), height=500,
        font=dict(family="DM Sans", size=14))

    du_rank = du_tot.sort_values("saldo")
    fig_rank = go.Figure(go.Bar(
        x=du_rank["saldo"], y=du_rank["sigla_uf"], orientation="h",
        marker_color=[VC if v>=0 else VR for v in du_rank["saldo"]],
        hovertemplate="<b>%{y}</b><br>%{x:,.0f}<extra></extra>"
    ))
    apply_layout(fig_rank, height=500,
        xaxis=dict(tickformat=",.0f", tickfont=dict(size=FONT_TICK), gridcolor=BGE),
        yaxis=dict(tickfont=dict(size=13))
    )

    dm = df_mun[(df_mun["ano"]>=ano_min)&(df_mun["ano"]<=ano_max)]
    dm = dm.groupby(["nome_municipio","sigla_uf","regiao"])["saldo"].sum().reset_index()
    if uf_sel:
        dm = dm[dm["sigla_uf"]==uf_sel]
    elif regioes:
        ufs_f = [u for r in regioes for u in REGIOES_UF.get(r,[])]
        dm = dm[dm["sigla_uf"].isin(ufs_f)]

    def bar_mun(df, cor):
        fig = go.Figure(go.Bar(
            x=df["saldo"], y=df["nome_municipio"]+" ("+df["sigla_uf"]+")",
            orientation="h", marker_color=cor,
            hovertemplate="<b>%{y}</b><br>%{x:,.0f}<extra></extra>"
        ))
        apply_layout(fig, height=360,
            xaxis=dict(tickformat=",.0f", tickfont=dict(size=FONT_TICK), gridcolor=BGE),
            yaxis=dict(tickfont=dict(size=13))
        )
        return fig

    return (fig_mapa, fig_rank,
            bar_mun(dm.nlargest(10,"saldo").sort_values("saldo"), VC),
            bar_mun(dm.nsmallest(10,"saldo").sort_values("saldo",ascending=False), VR),
            uf_sel)
