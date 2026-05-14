"""
export_utils.py
Exportación de figuras Plotly como PNG y PDF ejecutivo.
"""
import io
import plotly.graph_objects as go
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer,
    Image as RLImage, Table, TableStyle,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from datetime import datetime


def export_png(fig: go.Figure, width: int = 1200, height: int = 600) -> bytes:
    """Exporta figura Plotly como bytes PNG."""
    return fig.to_image(format="png", width=width, height=height, scale=2)


def export_map_png(map_bytes: bytes) -> bytes:
    """Devuelve los bytes del mapa ya generado (ya es PNG)."""
    return map_bytes


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
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        rightMargin=1.5 * cm, leftMargin=1.5 * cm,
        topMargin=1.5 * cm, bottomMargin=1.5 * cm,
    )
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "title", parent=styles["Title"],
        fontSize=16, textColor=colors.HexColor("#1e3a5f"),
        spaceAfter=4, alignment=TA_CENTER,
    )
    sub_style = ParagraphStyle(
        "sub", parent=styles["Normal"],
        fontSize=9, textColor=colors.HexColor("#64748b"),
        spaceAfter=3, alignment=TA_CENTER,
    )
    section_style = ParagraphStyle(
        "section", parent=styles["Heading2"],
        fontSize=11, textColor=colors.HexColor("#1d4ed8"),
        spaceBefore=10, spaceAfter=5,
    )
    cell_s = ParagraphStyle("cell", parent=styles["Normal"], fontSize=8)

    elements = []

    # Encabezado
    elements.append(Paragraph("Reporte de Coberturas de Vacunación", title_style))
    elements.append(Paragraph(
        f"Vacuna: <b>{vacuna}</b> &nbsp;|&nbsp; Cobertura Departamental: <b>{cob_pct:.1f}%</b>"
        f" &nbsp;|&nbsp; Estado: <b>{sem_label}</b>",
        sub_style,
    ))
    elements.append(Paragraph(
        f"DIRESA Huancavelica 2026 &nbsp;·&nbsp; "
        f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        sub_style,
    ))
    elements.append(Spacer(1, 0.4 * cm))

    # Mapa
    elements.append(Paragraph("Mapa de Cobertura por Provincia", section_style))
    elements.append(RLImage(io.BytesIO(map_png), width=16 * cm, height=9 * cm))
    elements.append(Spacer(1, 0.3 * cm))

    # Gráfico barras
    elements.append(Paragraph("Comparativo por Provincia", section_style))
    elements.append(RLImage(io.BytesIO(bar_png), width=16 * cm, height=6 * cm))
    elements.append(Spacer(1, 0.3 * cm))

    # Tabla
    elements.append(Paragraph("Detalle por Provincia", section_style))
    headers = ["Provincia", "Meta", "Dosis", "Cobertura %", "Estado"]
    table_data = [[Paragraph(h, ParagraphStyle("hdr", parent=styles["Normal"],
                             fontSize=8, textColor=colors.white))
                   for h in headers]]
    for _, row in df_table.iterrows():
        table_data.append([
            Paragraph(str(row.get("Provincia", "")), cell_s),
            Paragraph(f"{int(row.get('Meta', 0)):,}", cell_s),
            Paragraph(f"{int(row.get('Dosis', 0)):,}", cell_s),
            Paragraph(str(row.get("Cobertura %", "")), cell_s),
            Paragraph(str(row.get("Estado", "")), cell_s),
        ])

    tbl = Table(table_data, colWidths=[5 * cm, 3 * cm, 3 * cm, 3 * cm, 3 * cm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), colors.HexColor("#1e3a5f")),
        ("TEXTCOLOR",     (0, 0), (-1, 0), colors.white),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1),
         [colors.white, colors.HexColor("#f8fafc")]),
        ("GRID",          (0, 0), (-1, -1), 0.4, colors.HexColor("#e2e8f0")),
        ("ALIGN",         (1, 0), (-1, -1), "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(tbl)

    # Footer
    elements.append(Spacer(1, 0.5 * cm))
    elements.append(Paragraph(
        "DIRESA Huancavelica · Estrategia Sanitaria de Inmunizaciones · 2026",
        sub_style,
    ))

    doc.build(elements)
    buf.seek(0)
    return buf.getvalue()
