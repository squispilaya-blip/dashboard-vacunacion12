"""
app.py  —  Dashboard Coberturas de Vacunación
DIRESA Huancavelica 2026  |  Método PHVA-Deming
Publicar en: https://share.streamlit.io/
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
import os
import base64
from io import BytesIO

from data_loader import (
    load_coverage_data,
    get_regional_summary,
    get_ris_summary,
    get_phva_analysis,
    VACUNAS_INFO,
    apply_semaphore,
)
from map_renderer import render_colored_map, get_legend_html

# ─────────────────────────────────────────────
# CONFIGURACIÓN STREAMLIT
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Dashboard Vacunación – DIRESA Huancavelica 2026",
    page_icon="💉",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# CSS PERSONALIZADO
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* Fondo principal */
.stApp {
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 40%, #0f2027 100%);
    color: #e2e8f0;
}

/* Header principal */
.main-header {
    background: linear-gradient(135deg, #1a56db 0%, #1e40af 50%, #0ea5e9 100%);
    border-radius: 16px;
    padding: 24px 32px;
    margin-bottom: 20px;
    box-shadow: 0 8px 32px rgba(30,64,175,0.4);
    display: flex;
    align-items: center;
    justify-content: space-between;
}
.main-header h1 {
    color: white;
    font-size: 1.7rem;
    font-weight: 800;
    margin: 0;
    letter-spacing: -0.5px;
}
.main-header p {
    color: rgba(255,255,255,0.85);
    font-size: 0.88rem;
    margin: 4px 0 0;
}

/* Cards KPI */
.kpi-card {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 14px;
    padding: 16px 20px;
    text-align: center;
    backdrop-filter: blur(10px);
    transition: transform .2s, box-shadow .2s;
    margin-bottom: 10px;
}
.kpi-card:hover {
    transform: translateY(-3px);
    box-shadow: 0 12px 24px rgba(0,0,0,0.3);
}
.kpi-value {
    font-size: 2.2rem;
    font-weight: 800;
    line-height: 1;
    margin: 6px 0;
}
.kpi-label {
    font-size: 0.75rem;
    color: rgba(255,255,255,0.6);
    text-transform: uppercase;
    letter-spacing: 0.8px;
}
.kpi-sub {
    font-size: 0.82rem;
    color: rgba(255,255,255,0.5);
    margin-top: 4px;
}

/* Sección de título */
.section-title {
    font-size: 1.1rem;
    font-weight: 700;
    color: #7dd3fc;
    border-left: 4px solid #0ea5e9;
    padding-left: 12px;
    margin: 16px 0 12px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f172a 0%, #1e293b 100%) !important;
    border-right: 1px solid rgba(255,255,255,0.08);
}
[data-testid="stSidebar"] * {
    color: #e2e8f0 !important;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    background: rgba(255,255,255,0.04);
    border-radius: 12px;
    padding: 4px;
    gap: 4px;
}
.stTabs [data-baseweb="tab"] {
    color: rgba(255,255,255,0.6) !important;
    border-radius: 8px;
    font-weight: 600;
}
.stTabs [aria-selected="true"] {
    background: #1a56db !important;
    color: white !important;
}

/* Tablas */
.dataframe {
    font-size: 0.82rem !important;
}

/* Badge de semáforo */
.badge-critico    { background:#F44336; color:white; padding:3px 10px; border-radius:20px; font-size:0.75rem; font-weight:700; }
.badge-proceso    { background:#F59E0B; color:white; padding:3px 10px; border-radius:20px; font-size:0.75rem; font-weight:700; }
.badge-optimo     { background:#10B981; color:white; padding:3px 10px; border-radius:20px; font-size:0.75rem; font-weight:700; }

/* PHVA Cards */
.phva-card {
    border-radius: 14px;
    padding: 18px;
    margin-bottom: 12px;
    border-left: 5px solid;
}
.phva-p { background: rgba(59,130,246,0.12); border-color: #3b82f6; }
.phva-h { background: rgba(16,185,129,0.12); border-color: #10b981; }
.phva-v { background: rgba(245,158,11,0.12); border-color: #f59e0b; }
.phva-a { background: rgba(239,68,68,0.12);  border-color: #ef4444; }

.phva-title {
    font-size: 1rem;
    font-weight: 800;
    margin-bottom: 8px;
}

/* Alert boxes */
.alert-red    { background:rgba(239,68,68,.15);  border:1px solid rgba(239,68,68,.4);  border-radius:10px; padding:12px 16px; margin:6px 0; }
.alert-yellow { background:rgba(245,158,11,.15); border:1px solid rgba(245,158,11,.4); border-radius:10px; padding:12px 16px; margin:6px 0; }
.alert-green  { background:rgba(16,185,129,.15); border:1px solid rgba(16,185,129,.4); border-radius:10px; padding:12px 16px; margin:6px 0; }

/* Upload area */
[data-testid="stFileUploader"] {
    background: rgba(255,255,255,0.04) !important;
    border: 2px dashed rgba(255,255,255,0.2) !important;
    border-radius: 12px !important;
}

/* Divider */
hr { border-color: rgba(255,255,255,0.1) !important; }
</style>
""", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# FUNCIÓN: Gauge Chart Plotly
# ─────────────────────────────────────────────
def make_gauge(value: float, title: str, max_val: float = 25.0) -> go.Figure:
    sem = apply_semaphore(value)
    color = sem["color"]

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value,
        number={"suffix": "%", "font": {"size": 28, "color": "white"}},
        title={"text": title, "font": {"size": 11, "color": "#94a3b8"}},
        gauge={
            "axis": {"range": [0, max(max_val, value + 2)], "tickcolor": "#64748b",
                     "tickfont": {"color": "#94a3b8", "size": 10}},
            "bar": {"color": color, "thickness": 0.35},
            "bgcolor": "rgba(255,255,255,0.05)",
            "bordercolor": "rgba(255,255,255,0.1)",
            "steps": [
                {"range": [0, 20.0],  "color": "rgba(244,67,54,0.15)"},
                {"range": [20.0, 23.75], "color": "rgba(255,193,7,0.15)"},
                {"range": [23.75, max(max_val, value + 2)], "color": "rgba(76,175,80,0.15)"},
            ],
            "threshold": {
                "line": {"color": "white", "width": 2},
                "thickness": 0.9,
                "value": value,
            },
        },
    ))
    fig.update_layout(
        height=200, margin=dict(t=40, b=10, l=20, r=20),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "white"},
    )
    return fig


# ─────────────────────────────────────────────
# FUNCIÓN: Gráfico de barras por provincia
# ─────────────────────────────────────────────
def make_bar_chart(df_vac: pd.DataFrame, vacuna: str) -> go.Figure:
    df_sorted = df_vac.sort_values("cobertura_pct", ascending=True)
    colors = df_sorted["semaforo_color"].tolist()

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=df_sorted["provincia"],
        x=df_sorted["cobertura_pct"],
        orientation="h",
        marker_color=colors,
        marker_line_width=0,
        text=[f"  {v:.1f}%  ({int(vac)}/{int(m)})"
              for v, vac, m in zip(df_sorted["cobertura_pct"],
                                   df_sorted["vacunados"],
                                   df_sorted["meta"])],
        textposition="inside",
        textfont={"color": "white", "size": 12, "family": "Inter"},
        hovertemplate="<b>%{y}</b><br>Cobertura: %{x:.1f}%<extra></extra>",
    ))

    # Líneas de referencia semáforo
    for x, color, label in [(20.0, "#F44336", "20%"), (23.75, "#4CAF50", "23.75%")]:
        fig.add_vline(x=x, line_dash="dash", line_color=color,
                     annotation_text=label, annotation_font_color=color,
                     annotation_font_size=11)

    fig.update_layout(
        title=f"Cobertura por Provincia — {vacuna}",
        title_font={"size": 14, "color": "#7dd3fc"},
        xaxis=dict(title="% Cobertura", range=[0, max(df_vac["cobertura_pct"].max() * 1.15, 30)],
                   gridcolor="rgba(255,255,255,0.07)", color="#94a3b8"),
        yaxis=dict(color="#94a3b8"),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.02)",
        height=320,
        margin=dict(t=45, b=30, l=20, r=20),
        font={"color": "white", "family": "Inter"},
    )
    return fig


# ─────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="text-align:center; padding:16px 0 8px;">
        <div style="font-size:3rem;">💉</div>
        <div style="font-weight:800; font-size:1rem; color:#7dd3fc;">DIRESA HUANCAVELICA</div>
        <div style="font-size:0.8rem; color:#64748b;">Dashboard de Vacunación 2026</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 📂 Cargar Datos")
    uploaded_file = st.file_uploader(
        "Subir Excel de Coberturas",
        type=["xlsx", "xls"],
        help="Sube el archivo extendido con los datos de vacunados para actualizar el dashboard.",
    )

    st.markdown("---")
    st.markdown("### 💉 Vacuna a Visualizar")
    vacuna_sel = st.selectbox(
        "Seleccionar vacuna:",
        list(VACUNAS_INFO.keys()),
        index=0,
    )

    st.markdown("---")
    st.markdown("### 🚦 Semáforo de Cobertura")
    st.markdown(get_legend_html([]), unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("""
    <div style="text-align:center; font-size:0.72rem; color:#475569; padding-top:8px;">
        Metodología <b>PHVA-Deming</b><br>
        DIRESA Huancavelica © 2026<br>
        <span style="color:#1a56db;">🔗 share.streamlit.io</span>
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────
# CARGA DE DATOS
# ─────────────────────────────────────────────
DEFAULT_FILE = "COBERTURAS INMUNIZACIONES POR PROVINCIA- EXPOSICION SVA SARAMPION MINSA.xlsx"

@st.cache_data(show_spinner=False)
def cached_load(file_bytes: bytes, file_name: str):
    return load_coverage_data(BytesIO(file_bytes))

if uploaded_file is not None:
    with st.spinner("⏳ Procesando datos..."):
        df = cached_load(uploaded_file.read(), uploaded_file.name)
    st.success(f"✅ Archivo cargado: **{uploaded_file.name}**")
elif os.path.exists(DEFAULT_FILE):
    with st.spinner("⏳ Cargando datos base..."):
        df = load_coverage_data(DEFAULT_FILE)
else:
    st.error("⚠️ No se encontró el archivo de coberturas. Por favor sube el Excel desde el sidebar.")
    st.stop()

# ─────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────
fecha_hoy = datetime.now().strftime("%d de %B de %Y — %H:%M")
st.markdown(f"""
<div class="main-header">
    <div>
        <h1>🏥 Dashboard Coberturas de Vacunación</h1>
        <p>Región Huancavelica · DIRESA 2026 · Metodología PHVA-Deming</p>
    </div>
    <div style="text-align:right;">
        <div style="font-size:1.5rem;">📅</div>
        <div style="color:rgba(255,255,255,0.8); font-size:0.82rem;">{fecha_hoy}</div>
        <div style="color:rgba(255,255,255,0.5); font-size:0.75rem;">Semana Epidemiológica 2026</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# KPI CARDS REGIONALES (6 vacunas)
# ─────────────────────────────────────────────
st.markdown('<div class="section-title">📊 Indicadores Regionales por Vacuna</div>', unsafe_allow_html=True)

regional = get_regional_summary(df)
cols_kpi = st.columns(6)

VACUNA_ICONS = {
    "3° Dosis IPV":          "💊",
    "3° Dosis Pentavalente": "💉",
    "1° Ref DPT":            "🩺",
    "2° Ref DPT":            "🔬",
    "1° Dosis SPR":          "🌡️",
    "2° Dosis SPR":          "🛡️",
}

for i, (_, row) in enumerate(regional.iterrows()):
    sem = apply_semaphore(row["cobertura_pct"])
    with cols_kpi[i]:
        icon = VACUNA_ICONS.get(row["vacuna"], "💉")
        st.markdown(f"""
        <div class="kpi-card" style="border-top: 3px solid {sem['color']};">
            <div style="font-size:1.6rem;">{icon}</div>
            <div class="kpi-label">{row['vacuna']}</div>
            <div class="kpi-value" style="color:{sem['color']};">{row['cobertura_pct']:.1f}%</div>
            <div class="kpi-sub">{int(row['vacunados'])} / {int(row['meta'])}</div>
            <div style="margin-top:6px;">
                <span class="badge-{'critico' if sem['label']=='Crítico' else 'proceso' if sem['label']=='En Proceso' else 'optimo'}">
                    {sem['label']}
                </span>
            </div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# TABS PRINCIPALES
# ─────────────────────────────────────────────
tab_mapa, tab_ris, tab_phva = st.tabs([
    "🗺️ Mapa de Cobertura",
    "📋 Resumen por Provincia / RIS",
    "🔄 Resumen Ejecutivo PHVA",
])


# ═══════════════════════════════════════════
# TAB 1 — MAPA
# ═══════════════════════════════════════════
with tab_mapa:
    col_map, col_info = st.columns([1, 1])

    with col_map:
        st.markdown(f'<div class="section-title">🗺️ {vacuna_sel} — Huancavelica por Provincias</div>',
                    unsafe_allow_html=True)

        map_path = DEFAULT_FILE.replace(
            "COBERTURAS INMUNIZACIONES POR PROVINCIA- EXPOSICION SVA SARAMPION MINSA.xlsx",
            "mapa-departamento-huancavelica-provincias.png",
        )
        if not os.path.exists(map_path):
            map_path = "mapa-departamento-huancavelica-provincias.png"

        with st.spinner("🎨 Generando mapa..."):
            map_bytes = render_colored_map(df, vacuna_sel, map_path)

        st.image(map_bytes, caption=f"Cobertura {vacuna_sel} · DIRESA Huancavelica 2026",
                 use_container_width=True)

    with col_info:
        st.markdown(f'<div class="section-title">📊 Detalle por Provincia</div>', unsafe_allow_html=True)

        df_vac = df[df["vacuna"] == vacuna_sel].copy()

        # Barchart
        st.plotly_chart(make_bar_chart(df_vac, vacuna_sel),
                       use_container_width=True, config={"displayModeBar": False})

        # Tabla de datos
        st.markdown("**📋 Datos de la tabla:**")
        df_display = df_vac[["provincia", "vacunados", "meta", "cobertura_pct", "semaforo_label"]].copy()
        df_display.columns = ["Provincia", "Vacunados", "Meta", "Cobertura %", "Estado"]
        df_display = df_display.sort_values("Cobertura %", ascending=False)

        def color_estado(val):
            colors_map = {"Crítico": "background-color:#7f1d1d; color:#fca5a5",
                          "En Proceso": "background-color:#78350f; color:#fcd34d",
                          "Óptimo": "background-color:#064e3b; color:#6ee7b7"}
            return colors_map.get(val, "")

        styled = df_display.style.map(color_estado, subset=["Estado"])\
            .format({"Cobertura %": "{:.2f}%"})\
            .set_properties(**{"font-size": "12px"})
        st.dataframe(styled, use_container_width=True, height=280)

    # Gauges de todas las vacunas al pie del mapa
    st.markdown('<div class="section-title">⏱️ Velocímetros — Todas las Vacunas (Región)</div>',
                unsafe_allow_html=True)
    gcols = st.columns(6)
    for i, (_, row) in enumerate(regional.iterrows()):
        with gcols[i]:
            vacuna_short = row['vacuna'].replace("° Dosis", "°D").replace("° Ref", "°Ref").replace("° Ref", "°R")
            st.plotly_chart(
                make_gauge(row["cobertura_pct"], row["vacuna"]),
                use_container_width=True,
                config={"displayModeBar": False},
            )


# ═══════════════════════════════════════════
# TAB 2 — RESUMEN POR RIS / PROVINCIA
# ═══════════════════════════════════════════
with tab_ris:
    st.markdown('<div class="section-title">📋 Resumen de Coberturas por RIS / Provincia</div>',
                unsafe_allow_html=True)

    pivot = get_ris_summary(df)

    # Formato con colores
    VACUNAS_LIST = list(VACUNAS_INFO.keys())

    def style_cell(val):
        if pd.isna(val):
            return ""
        sem = apply_semaphore(float(val))
        bg = sem["color"] + "33"  # transparencia
        return f"background-color:{bg}; color:white; font-weight:600;"

    styled_pivot = pivot.style.map(style_cell, subset=VACUNAS_LIST)\
        .format({v: "{:.2f}%" for v in VACUNAS_LIST})\
        .set_properties(**{"font-size": "12px", "text-align": "center"})

    st.dataframe(styled_pivot, use_container_width=True, height=350)

    st.markdown("<br>", unsafe_allow_html=True)

    # Heatmap de cobertura
    st.markdown('<div class="section-title">🌡️ Mapa de Calor — Coberturas por Provincia y Vacuna</div>',
                unsafe_allow_html=True)

    heat_data = pivot.set_index("provincia")[VACUNAS_LIST]
    fig_heat = go.Figure(go.Heatmap(
        z=heat_data.values,
        x=[v.replace("° Dosis ", "°D ").replace("° Ref ", "°Ref ") for v in heat_data.columns],
        y=heat_data.index.tolist(),
        colorscale=[
            [0.0,  "#F44336"],
            [0.35, "#FF7043"],
            [0.5,  "#FFC107"],
            [0.65, "#8BC34A"],
            [1.0,  "#4CAF50"],
        ],
        zmin=0, zmax=30,
        text=[[f"{v:.1f}%" for v in row] for row in heat_data.values],
        texttemplate="%{text}",
        textfont={"size": 12, "color": "white"},
        hovertemplate="<b>%{y}</b><br>%{x}<br>Cobertura: %{z:.1f}%<extra></extra>",
    ))
    fig_heat.update_layout(
        height=380,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "white", "family": "Inter"},
        xaxis=dict(color="#94a3b8"),
        yaxis=dict(color="#94a3b8"),
        margin=dict(t=20, b=20, l=20, r=20),
    )
    st.plotly_chart(fig_heat, use_container_width=True, config={"displayModeBar": False})

    # Resumen estadístico
    st.markdown('<div class="section-title">📈 Estadísticas por Vacuna</div>', unsafe_allow_html=True)

    stats_data = []
    for vac in VACUNAS_LIST:
        df_v = df[df["vacuna"] == vac]
        total_vac = df_v["vacunados"].sum()
        total_meta = df_v["meta"].sum()
        pct = round(total_vac / total_meta * 100, 2) if total_meta > 0 else 0
        sem = apply_semaphore(pct)
        prov_max = df_v.loc[df_v["cobertura_pct"].idxmax(), "provincia"]
        prov_min = df_v.loc[df_v["cobertura_pct"].idxmin(), "provincia"]
        stats_data.append({
            "Vacuna": vac,
            "Total Vacunados": f"{int(total_vac):,}",
            "Meta Total": f"{int(total_meta):,}",
            "Cobertura Regional": f"{pct:.2f}%",
            "Estado": sem["label"],
            "Mejor Provincia": prov_max,
            "Provincia más Baja": prov_min,
        })

    df_stats = pd.DataFrame(stats_data)
    st.dataframe(df_stats, use_container_width=True, hide_index=True)


# ═══════════════════════════════════════════
# TAB 3 — RESUMEN EJECUTIVO PHVA
# ═══════════════════════════════════════════
with tab_phva:
    phva = get_phva_analysis(df)
    sem_gen = apply_semaphore(phva["cobertura_gral"])

    st.markdown(f"""
    <div style="background:linear-gradient(135deg,rgba(26,86,219,.25),rgba(14,165,233,.15));
                border-radius:16px; padding:20px 28px; margin-bottom:20px;
                border:1px solid rgba(14,165,233,.3);">
        <div style="display:flex; justify-content:space-between; align-items:center;">
            <div>
                <div style="font-size:0.85rem; color:#7dd3fc; font-weight:600; text-transform:uppercase; letter-spacing:1px;">
                    RESUMEN EJECUTIVO — DIRESA HUANCAVELICA 2026
                </div>
                <div style="font-size:1.1rem; font-weight:700; margin-top:4px;">
                    Coberturas de Vacunación — Metodología PHVA Deming
                </div>
                <div style="font-size:0.8rem; color:#64748b; margin-top:2px;">
                    Fecha de análisis: {phva['fecha_analisis']}
                </div>
            </div>
            <div style="text-align:center;">
                <div style="font-size:3rem; font-weight:900; color:{sem_gen['color']}; line-height:1;">
                    {phva['cobertura_gral']:.1f}%
                </div>
                <div style="font-size:0.8rem; color:#94a3b8;">Cobertura General</div>
                <div style="margin-top:4px;">
                    <span class="badge-{'critico' if sem_gen['label']=='Crítico' else 'proceso' if sem_gen['label']=='En Proceso' else 'optimo'}">
                        {sem_gen['label']}
                    </span>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── PLANIFICAR ──────────────────────────────
    st.markdown("""
    <div class="phva-card phva-p">
        <div class="phva-title" style="color:#93c5fd;">🔵 PLANIFICAR (P) — Plan de Vacunación 2026</div>
    """, unsafe_allow_html=True)

    col_p1, col_p2, col_p3 = st.columns(3)
    with col_p1:
        st.metric("🎯 Meta Total Regional", f"{phva['total_meta']:,}", help="Suma de todas las metas por vacuna y provincia")
    with col_p2:
        st.metric("💉 Total Vacunados", f"{phva['total_vacunados']:,}", help="Total de dosis aplicadas")
    with col_p3:
        st.metric("📉 Brecha Pendiente", f"{phva['brecha_total']:,}", delta=f"-{phva['brecha_total']:,}", delta_color="inverse")

    st.markdown(f"""
        <p style="color:#cbd5e1; font-size:0.88rem; margin-top:10px;">
        La región Huancavelica tiene programadas <strong>{phva['total_meta']:,}</strong> dosis para 6 biológicos
        (IPV, Pentavalente, SPR 1°/2° dosis, DPT 1°/2° refuerzo) en las 7 provincias.
        La meta se basa en el <em>archivo de metas físicas ESRI 2026</em>.
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ── HACER ──────────────────────────────────
    st.markdown("""
    <div class="phva-card phva-h">
        <div class="phva-title" style="color:#6ee7b7;">🟢 HACER (H) — Ejecución de la Vacunación</div>
    """, unsafe_allow_html=True)

    fig_exec = go.Figure()
    for _, row_v in phva["por_vacuna"].iterrows():
        sem_v = apply_semaphore(row_v["cobertura_pct"])
        fig_exec.add_trace(go.Bar(
            name=row_v["vacuna"],
            x=[row_v["vacuna"].replace("° Dosis ", "°D ").replace("° Ref ", "°Ref ")],
            y=[row_v["vacunados"]],
            marker_color=sem_v["color"],
            text=[f"{int(row_v['vacunados']):,}"],
            textposition="outside",
            textfont={"color": "white"},
        ))
        fig_exec.add_trace(go.Bar(
            name=f"Meta — {row_v['vacuna']}",
            x=[row_v["vacuna"].replace("° Dosis ", "°D ").replace("° Ref ", "°Ref ")],
            y=[row_v["meta"]],
            marker_color="rgba(255,255,255,0.1)",
            marker_line_color="rgba(255,255,255,0.3)",
            marker_line_width=1,
            showlegend=False,
        ))

    fig_exec.update_layout(
        barmode="overlay",
        height=280,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(255,255,255,0.02)",
        font={"color": "white", "family": "Inter"},
        showlegend=False,
        margin=dict(t=10, b=30, l=20, r=20),
        xaxis=dict(color="#94a3b8", gridcolor="rgba(255,255,255,0.05)"),
        yaxis=dict(color="#94a3b8", gridcolor="rgba(255,255,255,0.05)", title="Dosis"),
    )
    st.plotly_chart(fig_exec, use_container_width=True, config={"displayModeBar": False})
    st.markdown("</div>", unsafe_allow_html=True)

    # ── VERIFICAR ──────────────────────────────
    st.markdown("""
    <div class="phva-card phva-v">
        <div class="phva-title" style="color:#fcd34d;">🟡 VERIFICAR (V) — Análisis de Coberturas</div>
    """, unsafe_allow_html=True)

    col_v1, col_v2 = st.columns(2)
    with col_v1:
        st.markdown("**🏆 Mejor desempeño:**")
        st.markdown(f"""
        <div class="alert-green">
            <b>{phva['vacuna_mas_alta']}</b> alcanzó <b style="color:#6ee7b7;">{phva['pct_mas_alta']:.2f}%</b> de cobertura regional.
        </div>
        """, unsafe_allow_html=True)

    with col_v2:
        st.markdown("**⚠️ Menor cobertura:**")
        st.markdown(f"""
        <div class="alert-red">
            <b>{phva['vacuna_mas_baja']}</b> presenta solo <b style="color:#fca5a5;">{phva['pct_mas_baja']:.2f}%</b> de cobertura regional.
        </div>
        """, unsafe_allow_html=True)

    # Provincias por semáforo
    col_v3, col_v4, col_v5 = st.columns(3)
    with col_v3:
        st.markdown("**🔴 Provincias en Estado Crítico:**")
        if phva["provincias_criticas"]:
            for p in phva["provincias_criticas"]:
                st.markdown(f'<span class="badge-critico">⚠️ {p}</span>&nbsp;', unsafe_allow_html=True)
        else:
            st.markdown("✅ Ninguna")

    with col_v4:
        st.markdown("**🟡 Provincias En Proceso:**")
        if phva["provincias_en_proceso"]:
            for p in phva["provincias_en_proceso"]:
                st.markdown(f'<span class="badge-proceso">⚡ {p}</span>&nbsp;', unsafe_allow_html=True)
        else:
            st.markdown("✅ Ninguna")

    with col_v5:
        st.markdown("**🟢 Provincias en Estado Óptimo:**")
        if phva["provincias_optimas"]:
            for p in phva["provincias_optimas"]:
                st.markdown(f'<span class="badge-optimo">✅ {p}</span>&nbsp;', unsafe_allow_html=True)
        else:
            st.markdown("⚠️ Ninguna aún")

    st.markdown("</div>", unsafe_allow_html=True)

    # ── ACTUAR ─────────────────────────────────
    st.markdown("""
    <div class="phva-card phva-a">
        <div class="phva-title" style="color:#fca5a5;">🔴 ACTUAR (A) — Plan de Mejora y Recomendaciones</div>
    """, unsafe_allow_html=True)

    recomendaciones = []

    if phva["provincias_criticas"]:
        recomendaciones.append({
            "tipo": "alert-red",
            "emoji": "🚨",
            "titulo": "Intervención Urgente",
            "texto": (
                f"Las provincias <b>{', '.join(phva['provincias_criticas'])}</b> presentan cobertura "
                f"menor al 20%. Se recomienda: activación de brigadas móviles de vacunación, "
                f"seguimiento nominado casa a casa, coordinación con gobiernos locales y "
                f"campañas de comunicación social intensivas."
            ),
        })

    if phva["provincias_en_proceso"]:
        recomendaciones.append({
            "tipo": "alert-yellow",
            "emoji": "⚡",
            "titulo": "Fortalecimiento Requerido",
            "texto": (
                f"Las provincias <b>{', '.join(phva['provincias_en_proceso'])}</b> están en proceso "
                f"(20–23.75%). Se recomienda: reforzar jornadas de vacunación, actualizar el "
                f"padrón nominado y monitoreo semanal de avance."
            ),
        })

    if phva["provincias_optimas"]:
        recomendaciones.append({
            "tipo": "alert-green",
            "emoji": "💪",
            "titulo": "Mantener y Mejorar",
            "texto": (
                f"Las provincias <b>{', '.join(phva['provincias_optimas'])}</b> han alcanzado la meta. "
                f"Se recomienda: mantener cadena de frío, actualizar registros, buscar "
                f"no vacunados y replicar buenas prácticas en otras provincias."
            ),
        })

    recomendaciones.append({
        "tipo": "alert-yellow",
        "emoji": "📋",
        "titulo": "Recomendación General — Ciclo PHVA",
        "texto": (
            f"Actualizar semanalmente el archivo extendido de coberturas. "
            f"Revisar en reuniones de análisis de situación (ASIS) el avance por semana epidemiológica. "
            f"La vacuna con menor avance es <b>{phva['vacuna_mas_baja']}</b> "
            f"({phva['pct_mas_baja']:.2f}%) — priorizar en próximo plan de acción."
        ),
    })

    for r in recomendaciones:
        st.markdown(f"""
        <div class="{r['tipo']}" style="margin:10px 0;">
            <b>{r['emoji']} {r['titulo']}:</b><br>
            <span style="font-size:0.88rem;">{r['texto']}</span>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)

    # ── Tabla final consolidada ─────────────────
    st.markdown('<div class="section-title">📄 Cuadro Consolidado PHVA por Vacuna</div>', unsafe_allow_html=True)

    phva_table = []
    for _, row_v in phva["por_vacuna"].iterrows():
        sem_v = apply_semaphore(row_v["cobertura_pct"])
        brecha = int(row_v["meta"]) - int(row_v["vacunados"])
        accion = "Intervención Urgente" if sem_v["label"] == "Crítico" else \
                 "Fortalecer Vacunación" if sem_v["label"] == "En Proceso" else \
                 "Consolidar Logros"
        phva_table.append({
            "Biológico":       row_v["vacuna"],
            "Meta (P)":        f"{int(row_v['meta']):,}",
            "Vacunados (H)":   f"{int(row_v['vacunados']):,}",
            "Cobertura (V)":   f"{row_v['cobertura_pct']:.2f}%",
            "Brecha (V)":      f"{brecha:,}",
            "Estado":          sem_v["label"],
            "Acción (A)":      accion,
        })

    df_phva_final = pd.DataFrame(phva_table)
    st.dataframe(df_phva_final, use_container_width=True, hide_index=True)

    # Footer del PHVA
    st.markdown("""
    <div style="text-align:center; margin-top:24px; padding:16px;
                background:rgba(255,255,255,0.03); border-radius:12px;
                border:1px solid rgba(255,255,255,0.07);">
        <div style="font-size:0.85rem; color:#64748b;">
            <b style="color:#7dd3fc;">DIRESA HUANCAVELICA</b> · Estrategia Sanitaria de Inmunizaciones 2026<br>
            Metodología: Ciclo PHVA-Deming (Planificar · Hacer · Verificar · Actuar)<br>
            Publicado en: <b>share.streamlit.io</b> · Actualización automática al subir nuevo Excel
        </div>
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────
st.markdown("---")
st.markdown("""
<div style="display:flex; justify-content:space-between; align-items:center;
            padding:10px 0; font-size:0.75rem; color:#475569;">
    <div>💉 <b>DIRESA Huancavelica</b> · Estrategia Sanitaria de Inmunizaciones · 2026</div>
    <div>Metodología PHVA-Deming · Publicado en <b>Streamlit Cloud</b></div>
    <div>Vacunas: IPV · Pentavalente · SPR · DPT</div>
</div>
""", unsafe_allow_html=True)
