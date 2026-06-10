VD="#0D2B1A"; VM="#1A5C36"; VC="#4CAF72"
BG="#F5F2EC"; BGE="#E8E3D8"; TX="#1A1A18"; TL="#6B6B60"
VR="#C0392B"; AM="#D4A017"

FONT_TITLE_PAGE  = "2.6rem"
FONT_SUBTITLE    = "1.15rem"
FONT_CARD_TITLE  = "1rem"
FONT_CARD_DESC   = "0.9rem"
FONT_KPI_LABEL   = "0.82rem"
FONT_KPI_VALUE   = "2.4rem"
FONT_KPI_SUB     = "0.85rem"
FONT_AXIS        = 14
FONT_LEGEND      = 13
FONT_TICK        = 13
FONT_HOVER       = 14
FONT_ANNOT       = 13
BAR_WIDTH        = 0.65

LAYOUT_BASE = dict(
    paper_bgcolor="white",
    plot_bgcolor="white",
    font=dict(family="DM Sans", size=FONT_AXIS, color=TX),
    margin=dict(l=10, r=10, t=10, b=10),
    legend=dict(font=dict(size=FONT_LEGEND)),
    hoverlabel=dict(font_size=FONT_HOVER, font_family="DM Sans"),
    xaxis=dict(
        gridcolor=BGE,
        tickfont=dict(size=FONT_TICK),
        title_font=dict(size=FONT_AXIS)
    ),
    yaxis=dict(
        gridcolor=BGE,
        tickformat=",.0f",
        tickfont=dict(size=FONT_TICK),
        title_font=dict(size=FONT_AXIS)
    ),
)

def apply_layout(fig, height=340, **kwargs):
    layout = {**LAYOUT_BASE, "height": height, **kwargs}
    fig.update_layout(**layout)
    return fig

def card_title_style():
    return {
        "fontFamily":"DM Sans","fontSize":FONT_CARD_TITLE,
        "fontWeight":"600","color":TX,
        "letterSpacing":"0.05em","textTransform":"uppercase","marginBottom":"6px"
    }

def card_desc_style():
    return {
        "fontFamily":"DM Sans","fontSize":FONT_CARD_DESC,
        "color":TL,"marginBottom":"14px"
    }

def card_style():
    return {
        "background":"white","border":f"1px solid {BGE}",
        "borderRadius":"8px","padding":"24px","flex":"1"
    }

def kpi(titulo, valor, sub, cor):
    sinal = "+" if valor > 0 else ""
    from dash import html
    return html.Div([
        html.P(titulo, style={
            "fontFamily":"DM Sans","fontSize":FONT_KPI_LABEL,"color":TL,
            "marginBottom":"6px","letterSpacing":"0.1em",
            "textTransform":"uppercase","fontWeight":"600"
        }),
        html.H3(f"{sinal}{valor:,.0f}", style={
            "fontFamily":"DM Serif Display","fontSize":FONT_KPI_VALUE,
            "color":cor,"margin":"0 0 4px 0","lineHeight":"1"
        }),
        html.P(sub, style={
            "fontFamily":"DM Sans","fontSize":FONT_KPI_SUB,"color":TL,"margin":"0"
        })
    ], style={
        "background":"white","border":f"1px solid {BGE}",
        "borderTop":f"4px solid {cor}","borderRadius":"8px",
        "padding":"22px 26px","flex":"1","minWidth":"160px"
    })
