"""
export_utils.py
Exportación de figuras Plotly como PNG y PDF ejecutivo.
"""
import io
import plotly.graph_objects as go
import pandas as pd
from PIL import Image as PILImage
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer,
    Image as RLImage, Table, TableStyle, HRFlowable,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from datetime import datetime


def export_png(fig: go.Figure, width: int = 1400, height: int = 700) -> bytes:
    """Exporta figura Plotly como bytes PNG de alta resolución."""
    return fig.to_image(format="png", width=width, height=height, scale=2)


def _resize_image_for_pdf(img_bytes: bytes, max_width_cm: float, max_height_cm: float) -> tuple:
    """
    Redimensiona imagen manteniendo proporción para caber en el PDF.
    Retorna (width_cm, height_cm) reales en cm para ReportLab.
    """
    img = PILImage.open(io.BytesIO(img_bytes))
    orig_w, orig_h = img.size  # píxeles

    # Convertir límites a píxeles (72 dpi para PDF)
    dpi = 96
    max_w_px = max_width_cm / 2.54 * dpi
    max_h_px = max_height_cm / 2.54 * dpi

    ratio = min(max_w_px / orig_w, max_h_px / orig_h)
    new_w_px = orig_w * ratio
    new_h_px = orig_h * ratio

    # Convertir de vuelta a cm para ReportLab
    w_cm = new_w_px / dpi * 2.54
    h_cm = new_h_px / dpi * 2.54
    return w_cm, h_cm


def export_pdf(
    vacuna: str,
    cob_pct: float,
    sem_label: str,
    df_table: pd.DataFrame,
    map_png: bytes,
    bar_png: bytes,
) -> bytes:
    """
    Genera PDF ejecutivo del reporte de una vacuna.
    df_table columnas: Provincia, Meta, Dosis, Cobertura %, Estado
    """
    # Colores semáforo
    sem_colors = {
        "Logrado":    "#22c55e",
        "En Proceso": "#f59e0b",
        "Crítico":    "#ef4444",
    }
    sem_color_hex = sem_colors.get(sem_label, "#64748b")

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        rightMargin=1.8 * cm, leftMargin=1.8 * cm,
        topMargin=1.5 * cm, bottomMargin=1.5 * cm,
    )
    styles = getSampleStyleSheet()
    page_w = A4[0] - 3.6 * cm  # ancho útil

    title_style = ParagraphStyle(
        "title", parent=styles["Title"],
        fontSize=17, textColor=colors.HexColor("#1e3a5f"),
        spaceAfter=3, alignment=TA_CENTER, fontName="Helvetica-Bold",
    )
    sub_style = ParagraphStyle(
        "sub", parent=styles["Normal"],
        fontSize=9, textColor=colors.HexColor("#64748b"),
        spaceAfter=2, alignment=TA_CENTER,
    )
    section_style = ParagraphStyle(
        "section", parent=styles["Normal"],
        fontSize=11, textColor=colors.HexColor("#1d4ed8"),
        spaceBefore=10, spaceAfter=5, fontName="Helvetica-Bold",
    )
    cell_s = ParagraphStyle("cell", parent=styles["Normal"], fontSize=8.5,
                            alignment=TA_CENTER)
    cell_l = ParagraphStyle("cell_l", parent=styles["Normal"], fontSize=8.5,
                            alignment=TA_LEFT)

    elements = []

    # ── Encabezado ────────────────────────────────────────────────────
    elements.append(Paragraph(
        "DIRESA Huancavelica — Reporte de Coberturas de Vacunación", title_style
    ))
    elements.append(Paragraph(
        f"Vacuna: <b>{vacuna}</b> &nbsp;·&nbsp; "
        f"Cobertura Departamental: <b>{cob_pct:.1f}%</b> &nbsp;·&nbsp; "
        f"Estado: <b><font color='{sem_color_hex}'>{sem_label}</font></b>",
        sub_style,
    ))
    elements.append(Paragraph(
        f"Región Huancavelica · Estrategia Sanitaria de Inmunizaciones 2026 &nbsp;·&nbsp; "
        f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        sub_style,
    ))
    elements.append(HRFlowable(width="100%", thickness=1,
                               color=colors.HexColor("#e2e8f0"),
                               spaceAfter=8))

    # ── Mapa ──────────────────────────────────────────────────────────
    elements.append(Paragraph("Mapa de Cobertura por Provincia", section_style))
    try:
        map_w, map_h = _resize_image_for_pdf(map_png, max_width_cm=16, max_height_cm=11)
        elements.append(RLImage(io.BytesIO(map_png),
                                width=map_w * cm, height=map_h * cm))
    except Exception:
        elements.append(Paragraph("(Imagen del mapa no disponible)", sub_style))
    elements.append(Spacer(1, 0.4 * cm))

    # ── Gráfico barras ────────────────────────────────────────────────
    if bar_png and len(bar_png) > 100:
        elements.append(Paragraph("Comparativo por Provincia", section_style))
        try:
            bar_w, bar_h = _resize_image_for_pdf(bar_png, max_width_cm=16, max_height_cm=8)
            elements.append(RLImage(io.BytesIO(bar_png),
                                    width=bar_w * cm, height=bar_h * cm))
        except Exception:
            elements.append(Paragraph("(Gráfico de barras no disponible)", sub_style))
        elements.append(Spacer(1, 0.4 * cm))

    # ── Tabla detalle ─────────────────────────────────────────────────
    elements.append(Paragraph("Detalle por Provincia", section_style))

    hdr_style = ParagraphStyle("hdr", parent=styles["Normal"],
                               fontSize=8.5, textColor=colors.white,
                               fontName="Helvetica-Bold", alignment=TA_CENTER)
    headers = ["Provincia", "Meta", "Dosis", "Cobertura %", "Estado"]
    table_data = [[Paragraph(h, hdr_style) for h in headers]]

    row_colors = []
    for i, (_, row) in enumerate(df_table.iterrows()):
        estado = str(row.get("Estado", ""))
        bg = colors.white if i % 2 == 0 else colors.HexColor("#f8fafc")
        row_colors.append(bg)
        table_data.append([
            Paragraph(str(row.get("Provincia", "")), cell_l),
            Paragraph(f"{int(float(str(row.get('Meta', 0)).replace(',', '').replace('%', ''))):,}", cell_s),
            Paragraph(f"{int(float(str(row.get('Dosis', 0)).replace(',', '').replace('%', ''))):,}", cell_s),
            Paragraph(str(row.get("Cobertura %", "")), cell_s),
            Paragraph(estado, cell_s),
        ])

    col_widths = [5.5 * cm, 2.8 * cm, 2.8 * cm, 3.2 * cm, 3.2 * cm]
    tbl = Table(table_data, colWidths=col_widths, repeatRows=1)

    ts = [
        ("BACKGROUND",    (0, 0), (-1, 0), colors.HexColor("#1e3a5f")),
        ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 8.5),
        ("GRID",          (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8f0")),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("ALIGN",         (0, 1), (0, -1), "LEFT"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
    ]
    for i, bg in enumerate(row_colors):
        ts.append(("BACKGROUND", (0, i + 1), (-1, i + 1), bg))

    tbl.setStyle(TableStyle(ts))
    elements.append(tbl)

    # ── Footer ────────────────────────────────────────────────────────
    elements.append(Spacer(1, 0.6 * cm))
    elements.append(HRFlowable(width="100%", thickness=0.5,
                               color=colors.HexColor("#e2e8f0"), spaceAfter=4))
    elements.append(Paragraph(
        "DIRESA Huancavelica · Estrategia Sanitaria de Inmunizaciones · 2026 · "
        "Semáforo: ≥33.2% Logrado · 26.4–33.1% En Proceso · ≤26.3% Crítico",
        sub_style,
    ))

    doc.build(elements)
    buf.seek(0)
    return buf.getvalue()
