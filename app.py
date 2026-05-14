"""
app.py — Dashboard Coberturas de Vacunación DIRESA Huancavelica 2026
Publicar en: https://share.streamlit.io/
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
from pathlib import Path

from data_loader import (
    load_excel, get_vaccine_summary, get_pivot,
    assign_semaforo, SEMAFORO_CONFIG, THRESHOLDS,
)
from map_renderer import render_colored_map, get_legend_html
from charts import (
    build_gauge, build_bar_chart, build_heatmap,
    build_semaforo_html, build_vaccine_card_html,
)
from export_utils import export_png, export_pdf

# ── Configuración Streamlit ───────────────────────────────────────────────
st.set_page_config(
    page_title="Dashboard Vacunación — DIRESA Huancavelica",
    page_icon="💉",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif !important; }
.stApp { background: #f1f5f9; }

.main-header {
    background: linear-gradient(135deg, #1e3a5f 0%, #1d4ed8 55%, #0ea5e9 100%);
    border-radius: 16px; padding: 22px 32px; margin-bottom: 18px;
    box-shadow: 0 8px 32px rgba(30,58,95,0.25);
    display: flex; align-items: center; justify-content: space-between;
    position: relative; overflow: hidden;
}
.main-header::after {
    content: ''; position: absolute; bottom: 0; left: 0; right: 0; height: 3px;
    background: linear-gradient(90deg,#38bdf8,#60a5fa,#818cf8,#a78bfa);
}
.main-header h1 {
    color: white; font-size: 1.45rem; font-weight: 800; margin: 0; letter-spacing: -0.3px;
}
.main-header p { color: rgba(255,255,255,.75); font-size: 0.8rem; margin: 3px 0 0; }

.section-title {
    font-size: 0.73rem; font-weight: 700; letter-spacing: 2px;
    text-transform: uppercase; color: #64748b;
    display: flex; align-items: center; gap: 8px; margin: 14px 0 10px;
}
.section-title::before {
    content: ''; width: 3px; height: 13px;
    background: #1d4ed8; border-radius: 2px; display: block;
}

.kpi-card {
    background: white; border-radius: 12px; padding: 14px 10px;
    text-align: center; box-shadow: 0 1px 4px rgba(0,0,0,.07);
    border: 1px solid #e2e8f0; margin-bottom: 8px;
}
.kpi-value { font-size: 1.8rem; font-weight: 800; line-height: 1; margin: 5px 0; }
.kpi-label {
    font-size: 0.68rem; font-weight: 700; letter-spacing: 1.5px;
    color: #94a3b8; text-transform: uppercase;
}

.live-dot {
    display: inline-block; width: 8px; height: 8px; border-radius: 50%;
    background: #4ade80; box-shadow: 0 0 6px #4ade80;
    animation: blink 2.5s ease infinite;
}
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:.3} }

[data-testid="stSidebar"] {
    background: linear-gradient(180deg,#0f172a 0%,#1e293b 100%) !important;
    border-right: 1px solid rgba(255,255,255,.07);
}
[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
[data-testid="stFileUploader"] {
    background: rgba(255,255,255,.04) !important;
    border: 2px dashed rgba(255,255,255,.2) !important;
    border-radius: 10px !important;
}
hr { border-color: rgba(255,255,255,.1) !important; }
div[data-testid="stDataFrame"] { border-radius: 10px; overflow: hidden; }
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────
if "view" not in st.session_state:
    st.session_state.view = "general"
if "selected_vaccine" not in st.session_state:
    st.session_state.selected_vaccine = None

# ── Carga de datos ────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def _load_bytes(b: bytes) -> pd.DataFrame:
    return load_excel(b)

@st.cache_data(show_spinner=False)
def _load_default() -> pd.DataFrame:
    return load_excel()

# ── Sidebar ───────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="text-align:center;padding:20px 0 10px;">
        <div style="font-size:2.5rem;">💉</div>
        <div style="font-weight:800;font-size:0.95rem;color:#7dd3fc;letter-spacing:.3px;">
            DIRESA HUANCAVELICA</div>
        <div style="font-size:0.72rem;color:#64748b;margin-top:2px;">
            Dashboard de Vacunación 2026</div>
    </div>""", unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("### 📂 Actualizar Datos")
    uploaded = st.file_uploader(
        "Subir nuevo Excel de coberturas",
        type=["xlsx", "xls"],
        help="El Excel debe tener hojas por vacuna con columnas: Provincia, Meta, Dosis, %",
    )
    st.markdown("---")
    st.markdown("### 🚦 Semáforo de Cobertura")
    st.markdown(get_legend_html(), unsafe_allow_html=True)
    st.markdown("---")
    if st.session_state.view == "detail":
        if st.button("← Volver al Resumen General", use_container_width=True):
            st.session_state.view = "general"
            st.session_state.selected_vaccine = None
            st.rerun()
    st.markdown("""
    <div style="text-align:center;font-size:0.68rem;color:#475569;padding-top:10px;">
        DIRESA Huancavelica © 2026<br>
        Estrategia Sanitaria de Inmunizaciones<br>
        <span style="color:#3b82f6;">share.streamlit.io</span>
    </div>""", unsafe_allow_html=True)

# ── Carga efectiva ────────────────────────────────────────────────────────
if uploaded is not None:
    with st.spinner("Procesando Excel..."):
        df = _load_bytes(uploaded.read())
    st.sidebar.success(f"✅ {uploaded.name}")
else:
    with st.spinner("Cargando datos base..."):
        df = _load_default()

if df.empty:
    st.error("⚠️ No se encontraron datos. Verifica el formato del Excel.")
    st.stop()

vaccine_summary = get_vaccine_summary(df)

# ── Header ────────────────────────────────────────────────────────────────
fecha = datetime.now().strftime("%d/%m/%Y — %H:%M")
title_txt = (
    "Vacunación — Detalle: " + st.session_state.selected_vaccine
    if st.session_state.view == "detail" and st.session_state.selected_vaccine
    else "Dashboard Coberturas de Vacunación"
)
st.markdown(f"""
<div class="main-header">
    <div>
        <h1>🏥 {title_txt}</h1>
        <p>Región Huancavelica · DIRESA · Inmunizaciones 2026</p>
    </div>
    <div style="text-align:right;">
        <div>
            <span class="live-dot"></span>
            <span style="color:#4ade80;font-size:0.78rem;font-weight:700;margin-left:5px;">
                EN VIVO</span>
        </div>
        <div style="color:rgba(255,255,255,.6);font-size:0.72rem;margin-top:3px;">{fecha}</div>
    </div>
</div>
""", unsafe_allow_html=True)


# ════════════════════════════════════════════════════════════════════════
# VISTA GENERAL
# ════════════════════════════════════════════════════════════════════════
def render_general_view(df: pd.DataFrame, vs: pd.DataFrame):
    # KPIs globales
    total_meta  = int(df["meta"].sum())
    total_dosis = int(df["dosis"].sum())
    cob_gral    = round(total_dosis / total_meta * 100, 2) if total_meta > 0 else 0
    n_vacunas   = df["vacuna"].nunique()
    n_provs     = df["provincia"].nunique()
    sem_g       = assign_semaforo(cob_gral)
    c_g         = SEMAFORO_CONFIG[sem_g]["color"]

    st.markdown('<div class="section-title">Indicadores Globales del Programa</div>',
                unsafe_allow_html=True)
    c1, c2, c3, c4, c5 = st.columns(5)
    for col, label, val, color in [
        (c1, "Meta Total",      f"{total_meta:,}",  "#1d4ed8"),
        (c2, "Dosis Aplicadas", f"{total_dosis:,}", "#0ea5e9"),
        (c3, "Cobertura Dept.", f"{cob_gral:.1f}%", c_g),
        (c4, "Vacunas",         str(n_vacunas),      "#8b5cf6"),
        (c5, "Provincias",      str(n_provs),        "#64748b"),
    ]:
        with col:
            st.markdown(
                f'<div class="kpi-card"><div class="kpi-label">{label}</div>'
                f'<div class="kpi-value" style="color:{color};">{val}</div></div>',
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # Mapa general + tarjetas
    col_map, col_cards = st.columns([1.1, 1], gap="large")

    with col_map:
        st.markdown('<div class="section-title">Mapa de Cobertura — Huancavelica</div>',
                    unsafe_allow_html=True)
        # Mostrar vacuna con mayor cobertura en el mapa general
        best_vac = vs.sort_values("cobertura_pct", ascending=False).iloc[0]["vacuna"]
        with st.spinner("Generando mapa..."):
            map_bytes = render_colored_map(df, best_vac)
        st.image(map_bytes,
                 caption=f"Cobertura {best_vac} — Haz clic en una vacuna para ver detalle",
                 use_container_width=True)

    with col_cards:
        st.markdown('<div class="section-title">Resumen por Vacuna — Selecciona para ver detalle</div>',
                    unsafe_allow_html=True)
        rows_list = vs.to_dict("records")
        cols_per_row = 3
        for i in range(0, len(rows_list), cols_per_row):
            batch = rows_list[i: i + cols_per_row]
            cols = st.columns(cols_per_row)
            for j, vrow in enumerate(batch):
                with cols[j]:
                    st.markdown(
                        build_vaccine_card_html(
                            vacuna=vrow["vacuna"],
                            cobertura_pct=vrow["cobertura_pct"],
                            dosis=vrow["dosis"],
                            meta=vrow["meta"],
                            sem_color=vrow["sem_color"],
                            sem_label=vrow["sem_label"],
                            sem_bg=vrow["sem_bg"],
                        ),
                        unsafe_allow_html=True,
                    )
                    if st.button("Ver detalle →",
                                 key=f"btn_{vrow['vacuna']}",
                                 use_container_width=True):
                        st.session_state.view = "detail"
                        st.session_state.selected_vaccine = vrow["vacuna"]
                        st.rerun()

    # Heatmap de todas las vacunas
    st.markdown("---")
    st.markdown('<div class="section-title">Mapa de Calor — Todas las Vacunas × Provincias</div>',
                unsafe_allow_html=True)
    fig_heat = build_heatmap(df)
    st.plotly_chart(fig_heat, use_container_width=True,
                    config={"displayModeBar": False})


# ════════════════════════════════════════════════════════════════════════
# VISTA DETALLE
# ════════════════════════════════════════════════════════════════════════
def render_detail_view(df: pd.DataFrame, vacuna: str):
    df_vac = df[df["vacuna"] == vacuna].copy()
    if df_vac.empty:
        st.error(f"No hay datos para: {vacuna}")
        return

    # KPIs de la vacuna
    total_meta  = int(df_vac["meta"].sum())
    total_dosis = int(df_vac["dosis"].sum())
    cob_pct     = round(total_dosis / total_meta * 100, 2) if total_meta > 0 else 0
    brecha      = total_meta - total_dosis
    sem         = assign_semaforo(cob_pct)
    sem_cfg     = SEMAFORO_CONFIG[sem]

    st.markdown('<div class="section-title">Indicadores de la Vacuna</div>',
                unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    for col, label, val, color in [
        (c1, "Meta",             f"{total_meta:,}",  "#1d4ed8"),
        (c2, "Dosis Aplicadas",  f"{total_dosis:,}", "#0ea5e9"),
        (c3, "Cobertura Dept.",  f"{cob_pct:.1f}%",  sem_cfg["color"]),
        (c4, "Brecha Pendiente", f"{brecha:,}",       "#ef4444"),
    ]:
        with col:
            st.markdown(
                f'<div class="kpi-card"><div class="kpi-label">{label}</div>'
                f'<div class="kpi-value" style="color:{color};">{val}</div></div>',
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # Layout: mapa | análisis
    col_map, col_anl = st.columns([1.2, 1], gap="large")

    with st.spinner("Generando mapa..."):
        map_bytes = render_colored_map(df, vacuna)

    with col_map:
        st.markdown('<div class="section-title">Mapa Coroplético — Provincias de Huancavelica</div>',
                    unsafe_allow_html=True)
        st.image(map_bytes,
                 caption=f"Cobertura {vacuna} por provincia — Semáforo actualizado",
                 use_container_width=True)

    with col_anl:
        # Gauge
        st.markdown('<div class="section-title">Velocímetro Departamental</div>',
                    unsafe_allow_html=True)
        fig_gauge = build_gauge(cob_pct, f"Cobertura — {vacuna}")
        st.plotly_chart(fig_gauge, use_container_width=True,
                        config={"displayModeBar": False})

        # Semáforo
        st.markdown('<div class="section-title">Semáforo de Provincias</div>',
                    unsafe_allow_html=True)
        n_v = int((df_vac["semaforo"] == "verde").sum())
        n_a = int((df_vac["semaforo"] == "amarillo").sum())
        n_r = int((df_vac["semaforo"] == "rojo").sum())
        st.markdown(
            f'<div style="background:white;border-radius:10px;padding:12px 16px;'
            f'box-shadow:0 1px 4px rgba(0,0,0,.07);border:1px solid #e2e8f0;">'
            f'{build_semaforo_html(n_v, n_a, n_r)}</div>',
            unsafe_allow_html=True,
        )

    # Gráfico barras
    st.markdown('<div class="section-title">Comparativo por Provincia</div>',
                unsafe_allow_html=True)
    fig_bar = build_bar_chart(df_vac, vacuna)
    st.plotly_chart(fig_bar, use_container_width=True,
                    config={"displayModeBar": False})

    # Tabla
    st.markdown('<div class="section-title">Detalle por Provincia</div>',
                unsafe_allow_html=True)
    df_table = df_vac[["provincia", "meta", "dosis", "cobertura_pct", "sem_label"]].copy()
    df_table.columns = ["Provincia", "Meta", "Dosis", "Cobertura %", "Estado"]
    df_table = df_table.sort_values("Cobertura %", ascending=False)

    def _color_row(row):
        cfg = SEMAFORO_CONFIG.get(
            {"Logrado": "verde", "En Proceso": "amarillo", "Crítico": "rojo"}.get(
                row["Estado"], "rojo"
            ), {}
        )
        bg = cfg.get("bg", "white")
        color = cfg.get("color", "#1e293b")
        return [f"background-color:{bg};color:{color}" if c == "Estado"
                else "color:#1e293b" for c in df_table.columns]

    df_display = df_table.copy()
    df_display["Cobertura %"] = df_display["Cobertura %"].map("{:.2f}%".format)
    st.dataframe(
        df_display.style.apply(_color_row, axis=1)
                  .set_properties(**{"font-size": "13px"}),
        use_container_width=True,
        hide_index=True,
        height=300,
    )

    # Exportación
    st.markdown("---")
    st.markdown('<div class="section-title">Exportar Reporte</div>',
                unsafe_allow_html=True)

    df_pdf = df_table.copy()

    ce1, ce2, ce3 = st.columns(3)
    with ce1:
        st.download_button(
            "📥 Mapa PNG",
            data=map_bytes,
            file_name=f"mapa_{vacuna.replace(' ', '_')}.png",
            mime="image/png",
            use_container_width=True,
        )
    with ce2:
        try:
            bar_png = export_png(fig_bar)
            st.download_button(
                "📥 Gráfico PNG",
                data=bar_png,
                file_name=f"grafico_{vacuna.replace(' ', '_')}.png",
                mime="image/png",
                use_container_width=True,
            )
        except Exception:
            st.info("Instala kaleido para exportar PNG de gráficos.")
            bar_png = b""
    with ce3:
        try:
            pdf_bytes = export_pdf(
                vacuna=vacuna,
                cob_pct=cob_pct,
                sem_label=sem_cfg["label"],
                df_table=df_pdf,
                map_png=map_bytes,
                bar_png=bar_png if bar_png else map_bytes,
            )
            st.download_button(
                "📄 Reporte PDF",
                data=pdf_bytes,
                file_name=f"reporte_{vacuna.replace(' ', '_')}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        except Exception as e:
            st.info(f"PDF no disponible: {e}")


# ── Router principal ──────────────────────────────────────────────────────
if st.session_state.view == "general":
    render_general_view(df, vaccine_summary)
elif st.session_state.view == "detail" and st.session_state.selected_vaccine:
    render_detail_view(df, st.session_state.selected_vaccine)
else:
    st.session_state.view = "general"
    st.rerun()

# ── Footer ────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("""
<div style="display:flex;justify-content:space-between;align-items:center;
            padding:8px 0;font-size:0.72rem;color:#94a3b8;">
    <div>💉 <b>DIRESA Huancavelica</b> · Estrategia Sanitaria de Inmunizaciones · 2026</div>
    <div>Umbrales: ≥33.2% Logrado · 26.4–33.1% En Proceso · ≤26.3% Crítico</div>
    <div>Publicado en <b>Streamlit Cloud</b></div>
</div>
""", unsafe_allow_html=True)
