"""
charts.py
Componentes Plotly y HTML para el dashboard de vacunación DIRESA Huancavelica.
"""
import pandas as pd
import plotly.graph_objects as go
from data_loader import SEMAFORO_CONFIG, THRESHOLDS, assign_semaforo


def build_gauge(value: float, title: str) -> go.Figure:
    """Gauge (velocímetro) de cobertura departamental."""
    sem = assign_semaforo(value)
    color = SEMAFORO_CONFIG[sem]["color"]

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        number={"suffix": "%", "font": {"size": 32, "color": "#1e293b", "family": "Inter"}},
        title={"text": title, "font": {"size": 11, "color": "#64748b"}},
        gauge={
            "axis": {
                "range": [0, 60],
                "tickcolor": "#94a3b8",
                "tickfont": {"color": "#94a3b8", "size": 9},
                "tickvals": [0, THRESHOLDS["amarillo"], THRESHOLDS["verde"], 60],
                "ticktext": ["0%", f"{THRESHOLDS['amarillo']}%",
                             f"{THRESHOLDS['verde']}%", "60%"],
            },
            "bar": {"color": color, "thickness": 0.28},
            "bgcolor": "#f8fafc",
            "bordercolor": "#e2e8f0",
            "borderwidth": 1,
            "steps": [
                {"range": [0, THRESHOLDS["amarillo"]],
                 "color": "rgba(239,68,68,0.12)"},
                {"range": [THRESHOLDS["amarillo"], THRESHOLDS["verde"]],
                 "color": "rgba(245,158,11,0.12)"},
                {"range": [THRESHOLDS["verde"], 60],
                 "color": "rgba(34,197,94,0.12)"},
            ],
            "threshold": {
                "line": {"color": color, "width": 3},
                "thickness": 0.85,
                "value": value,
            },
        },
    ))
    fig.update_layout(
        height=220,
        margin=dict(t=50, b=5, l=20, r=20),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font={"family": "Inter"},
    )
    return fig


def build_bar_chart(df_vacuna: pd.DataFrame, vacuna_name: str) -> go.Figure:
    """Gráfico de barras horizontales por provincia."""
    df = df_vacuna.sort_values("cobertura_pct", ascending=True)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=df["provincia"],
        x=df["cobertura_pct"],
        orientation="h",
        marker_color=df["sem_color"].tolist(),
        marker_line_width=0,
        text=[f"  {v:.1f}%  ({int(d):,}/{int(m):,})"
              for v, d, m in zip(df["cobertura_pct"], df["dosis"], df["meta"])],
        textposition="inside",
        textfont={"color": "white", "size": 12, "family": "Inter"},
        hovertemplate="<b>%{y}</b><br>Cobertura: %{x:.1f}%<extra></extra>",
    ))

    for thresh, color, label in [
        (THRESHOLDS["amarillo"], "#ef4444",
         f"Crítico ≤{THRESHOLDS['amarillo']-0.1:.1f}%"),
        (THRESHOLDS["verde"], "#22c55e",
         f"Logrado ≥{THRESHOLDS['verde']}%"),
    ]:
        fig.add_vline(
            x=thresh, line_dash="dash", line_color=color, line_width=1.5,
            annotation_text=label,
            annotation_font_color=color,
            annotation_font_size=10,
            annotation_position="top right",
        )

    max_x = max(df["cobertura_pct"].max() * 1.25, 50) if not df.empty else 50
    fig.update_layout(
        title=dict(text=f"Cobertura por Provincia — {vacuna_name}",
                   font=dict(size=13, color="#1e3a5f")),
        xaxis=dict(title="% Cobertura", range=[0, max_x],
                   gridcolor="#f1f5f9", color="#64748b"),
        yaxis=dict(color="#475569"),
        paper_bgcolor="white",
        plot_bgcolor="#fafafa",
        height=300,
        margin=dict(t=50, b=30, l=10, r=20),
        font={"family": "Inter"},
    )
    return fig


def build_heatmap(df: pd.DataFrame) -> go.Figure:
    """Heatmap de coberturas: filas=provincia, columnas=vacuna."""
    import numpy as np
    pivot = df.pivot_table(
        index="provincia", columns="vacuna",
        values="cobertura_pct", aggfunc="first"
    ).fillna(0)  # reemplazar NaN con 0 para evitar errores de formato

    z_vals = pivot.values.tolist()
    # Texto seguro: si el valor es 0 o nan mostrar "—", si no el porcentaje
    text_vals = [
        [f"{v:.1f}%" if v > 0 else "—" for v in row]
        for row in z_vals
    ]

    fig = go.Figure(go.Heatmap(
        z=z_vals,
        x=pivot.columns.tolist(),
        y=pivot.index.tolist(),
        colorscale=[
            [0.0,  "#ef4444"],
            [0.35, "#f59e0b"],
            [0.65, "#22c55e"],
            [1.0,  "#15803d"],
        ],
        zmin=0, zmax=60,
        text=text_vals,
        texttemplate="%{text}",
        textfont={"size": 11, "color": "white"},
        hovertemplate="<b>%{y}</b> | %{x}<br>Cobertura: %{z:.1f}%<extra></extra>",
        colorbar=dict(
            title=dict(text="Cobert. %", font=dict(color="#475569")),
            thickness=12,
            tickfont=dict(color="#475569"),
        ),
    ))
    fig.update_layout(
        height=350,
        paper_bgcolor="white",
        plot_bgcolor="white",
        font={"family": "Inter", "color": "#1e293b"},
        xaxis=dict(color="#475569", tickangle=-30),
        yaxis=dict(color="#475569"),
        margin=dict(t=20, b=80, l=10, r=20),
    )
    return fig


def build_semaforo_html(n_verde: int, n_amarillo: int, n_rojo: int) -> str:
    total = n_verde + n_amarillo + n_rojo or 1
    rows = [
        ("#22c55e", f"≥ {THRESHOLDS['verde']}%",
         "Logrado", n_verde),
        ("#f59e0b",
         f"{THRESHOLDS['amarillo']}–{THRESHOLDS['verde']-0.1:.1f}%",
         "En Proceso", n_amarillo),
        ("#ef4444", f"≤ {THRESHOLDS['amarillo']-0.1:.1f}%",
         "Crítico", n_rojo),
    ]
    items = ""
    for color, rango, label, n in rows:
        pct_bar = n / total * 100
        items += f"""
        <div style="display:flex;align-items:center;gap:10px;padding:9px 0;
                    border-bottom:1px solid #f1f5f9;">
            <div style="width:12px;height:12px;border-radius:50%;
                        background:{color};flex-shrink:0;"></div>
            <div style="font-size:11px;font-weight:600;color:{color};
                        min-width:125px;">{rango}</div>
            <div style="flex:1;height:6px;background:#f1f5f9;
                        border-radius:3px;overflow:hidden;">
                <div style="width:{pct_bar:.0f}%;height:100%;
                            background:{color};border-radius:3px;"></div>
            </div>
            <div style="font-size:13px;font-weight:800;color:{color};
                        min-width:55px;text-align:right;">{n} prov.</div>
        </div>"""
    return f'<div style="font-family:Inter,sans-serif;">{items}</div>'


def build_vaccine_card_html(vacuna: str, cobertura_pct: float,
                            dosis: int, meta: int,
                            sem_color: str, sem_label: str,
                            sem_bg: str) -> str:
    return f"""
    <div style="background:white;border-radius:12px;padding:14px 10px;
                border:1.5px solid {sem_color}33;
                box-shadow:0 2px 8px rgba(0,0,0,.07);text-align:center;">
        <div style="font-size:9.5px;font-weight:700;letter-spacing:1.5px;
                    color:#64748b;text-transform:uppercase;margin-bottom:8px;
                    line-height:1.3;">{vacuna}</div>
        <div style="font-size:26px;font-weight:800;color:{sem_color};line-height:1;">
            {cobertura_pct:.1f}%
        </div>
        <div style="font-size:10px;color:#94a3b8;margin:4px 0 8px;">
            {int(dosis):,} / {int(meta):,} dosis
        </div>
        <div style="display:inline-block;padding:3px 10px;border-radius:20px;
                    background:{sem_bg};color:{sem_color};font-size:9.5px;
                    font-weight:700;border:1px solid {sem_color}55;">
            {sem_label}
        </div>
    </div>"""
