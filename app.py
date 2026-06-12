# app.py — Arquivo principal do dashboard.
# Cria a aplicação Dash, monta a barra de navegação no topo
# e carrega automaticamente as páginas da pasta pages/.

import dash
from dash import dcc, html
import dash_bootstrap_components as dbc

# Cria a aplicação Dash.
# use_pages=True ativa o sistema de multipáginas (pasta pages/)
# external_stylesheets carrega o Bootstrap e as fontes do Google
app = dash.Dash(
    __name__,
    use_pages=True,
    external_stylesheets=[
        dbc.themes.BOOTSTRAP,
        "https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:opsz,wght@9..40,300;9..40,400;9..40,500;9..40,600&display=swap"
    ],
    suppress_callback_exceptions=True
)

# Estilo visual dos links do menu de navegação
NAV_LINK = {
    "color": "#8FB89A", "textDecoration": "none",
    "fontFamily": "DM Sans", "fontSize": "0.82rem",
    "fontWeight": "500", "letterSpacing": "0.08em",
    "textTransform": "uppercase", "padding": "4px 0",
    "borderBottom": "2px solid transparent",
    "transition": "color 0.2s"
}

# Layout geral da aplicação: barra de navegação fixa no topo
# + área onde o conteúdo de cada página é renderizado
app.layout = html.Div([
    html.Nav([
        html.Div([
            html.Div([
                html.Span("CAGED", style={
                    "fontFamily": "DM Serif Display", "fontSize": "1.35rem",
                    "color": "#E8F5E3", "letterSpacing": "0.05em"
                }),
                html.Span(" 2020–2026", style={
                    "fontSize": "0.82rem", "color": "#5A9A6A",
                    "marginLeft": "6px", "fontFamily": "DM Sans"
                }),
            ], style={"display": "flex", "alignItems": "baseline"}),

            # Links que levam para cada página do dashboard
            html.Div([
                dcc.Link("Visão Geral",  href="/",           style={**NAV_LINK, "marginRight": "28px"}),
                dcc.Link("Regional",     href="/regional",    style={**NAV_LINK, "marginRight": "28px"}),
                dcc.Link("Setorial",     href="/setorial",    style={**NAV_LINK, "marginRight": "28px"}),
                dcc.Link("Pandemia",     href="/pandemia",    style=NAV_LINK),
            ], style={"display": "flex", "alignItems": "center"})
        ], style={
            "maxWidth": "1400px", "margin": "0 auto", "padding": "0 32px",
            "display": "flex", "justifyContent": "space-between",
            "alignItems": "center", "height": "58px"
        })
    ], style={
        "background": "#0D2B1A", "borderBottom": "1px solid #1A3D24",
        "position": "sticky", "top": "0", "zIndex": "100"
    }),
    # page_container é onde o Dash insere o conteúdo da página atual
    html.Div(dash.page_container,
             style={"background": "#F5F2EC", "minHeight": "calc(100vh - 58px)"})
], style={"background": "#F5F2EC", "margin": "0"})

# Inicia o servidor local na porta 8050 (http://localhost:8050)
if __name__ == "__main__":
    app.run(debug=True, port=8050)
