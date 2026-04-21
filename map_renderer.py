"""
map_renderer.py
Colorea el mapa PNG de Huancavelica con flood-fill según cobertura (semáforo).
Tipografía y diseño ejecutivo de alta visibilidad.
"""

import io
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import pandas as pd


# ── Puntos semilla por provincia (coordenadas px en imagen 827×1170) ──
PROVINCE_SEEDS = {
    "TAYACAJA":       [(530, 180), (480, 140), (600, 200)],
    "CHURCAMPA":      [(630, 335), (660, 345)],
    "ACOBAMBA":       [(575, 450), (600, 430)],
    "HUANCAVELICA":   [(330, 430), (360, 380), (300, 500)],
    "ANGARAES":       [(540, 580), (560, 600), (520, 550)],
    "CASTROVIRREYNA": [(190, 630), (160, 600), (220, 660)],
    "HUAYTARA":       [(420, 820), (380, 800), (450, 850)],
}

# Posiciones del texto de % y vacunados por provincia
LABEL_POSITIONS = {
    "TAYACAJA":       {"pct": (480, 188), "num": (480, 224)},
    "CHURCAMPA":      {"pct": (614, 345), "num": (614, 381)},
    "ACOBAMBA":       {"pct": (558, 448), "num": (558, 482)},
    "HUANCAVELICA":   {"pct": (305, 435), "num": (305, 471)},
    "ANGARAES":       {"pct": (524, 588), "num": (524, 622)},
    "CASTROVIRREYNA": {"pct": (172, 638), "num": (172, 674)},
    "HUAYTARA":       {"pct": (395, 825), "num": (395, 861)},
}

MAP_PATH = "mapa-departamento-huancavelica-provincias.png"


def _hex_to_rgba(hex_color: str, alpha: int = 185) -> tuple:
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return (r, g, b, alpha)


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    """Carga la mejor fuente disponible en el sistema."""
    candidates = [
        "arialbd.ttf",    # Arial Bold Windows
        "arial.ttf",
        "DejaVuSans-Bold.ttf",
        "DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Linux
        "/System/Library/Fonts/Helvetica.ttc",                   # macOS
    ]
    for name in candidates:
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _draw_text_with_shadow(
    draw: ImageDraw.ImageDraw,
    pos: tuple,
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: tuple,
    shadow_color: tuple = (0, 0, 0),
    shadow_offset: int = 2,
    anchor: str = "mm",
):
    """Dibuja texto con sombra para máxima legibilidad."""
    sx, sy = pos[0] + shadow_offset, pos[1] + shadow_offset
    draw.text((sx, sy), text, font=font, fill=shadow_color + (200,), anchor=anchor)
    draw.text(pos, text, font=font, fill=fill + (255,), anchor=anchor)


def _draw_rounded_badge(
    draw: ImageDraw.ImageDraw,
    center_x: int,
    center_y: int,
    text: str,
    font: ImageFont.FreeTypeFont,
    bg_color: tuple,
    text_color: tuple = (255, 255, 255),
    padding_x: int = 14,
    padding_y: int = 6,
    radius: int = 10,
):
    """Dibuja un badge redondeado con texto centrado."""
    bbox = font.getbbox(text)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]

    w = tw + padding_x * 2
    h = th + padding_y * 2
    x0 = center_x - w // 2
    y0 = center_y - h // 2
    x1 = center_x + w // 2
    y1 = center_y + h // 2

    # Fondo semitransparente con borde
    draw.rounded_rectangle([x0, y0, x1, y1], radius=radius,
                            fill=bg_color + (210,), outline=(255, 255, 255, 120), width=1)
    draw.text((center_x, center_y), text, font=font, fill=text_color + (255,), anchor="mm")


def render_colored_map(
    df: pd.DataFrame,
    vacuna: str,
    map_path: str = MAP_PATH,
) -> bytes:
    """
    Genera el mapa PNG con provincias coloreadas según semáforo y
    etiquetas ejecutivas de alta visibilidad.

    Args:
        df:       DataFrame de load_coverage_data()
        vacuna:   Nombre de la vacuna a visualizar
        map_path: Ruta a la imagen base PNG

    Returns:
        bytes PNG de la imagen coloreada
    """
    img = Image.open(map_path).convert("RGBA")
    W, H = img.size   # 827 × 1170

    # ── Capa 1: Color de provincias (flood-fill) ──────────────────────
    colored = img.copy()
    df_vac = df[df["vacuna"] == vacuna]

    for _, row in df_vac.iterrows():
        prov   = row["provincia"]
        color  = _hex_to_rgba(row["semaforo_color"], alpha=195)
        seeds  = PROVINCE_SEEDS.get(prov, [])
        for seed in seeds:
            try:
                px = colored.getpixel(seed)
                if px[0] > 50 or px[1] > 50 or px[2] > 50:
                    ImageDraw.floodfill(colored, seed, color, thresh=80)
                    break
            except Exception:
                continue

    # Compositar sobre original para conservar bordes negros
    result = Image.alpha_composite(img, colored)

    # ── Capa 2: Etiquetas ejecutivas ──────────────────────────────────
    draw = ImageDraw.Draw(result)

    # Fuentes de distintos tamaños
    font_pct  = _load_font(18)   # % compacto y legible (no tapa el nombre de provincia)

    for _, row in df_vac.iterrows():
        prov = row["provincia"]
        pct  = row["cobertura_pct"]
        sem_color_hex = row["semaforo_color"]

        pos_info = LABEL_POSITIONS.get(prov)
        if not pos_info:
            continue

        cx_pct, cy_pct = pos_info["pct"]

        # ── Determinar color del texto según fondo ──
        if sem_color_hex == "#FFC107":   # amarillo → texto oscuro
            txt_color = (30, 20, 0)
        else:                            # rojo/verde → texto blanco
            txt_color = (255, 255, 255)

        # ── Badge de porcentaje compacto (solo % en el mapa) ──────────
        h_ex = sem_color_hex.lstrip("#")
        bg = (int(h_ex[0:2], 16), int(h_ex[2:4], 16), int(h_ex[4:6], 16))
        bg_dark = tuple(max(0, c - 40) for c in bg)

        pct_text = f"{pct:.1f}%"
        _draw_rounded_badge(
            draw, cx_pct, cy_pct, pct_text,
            font=font_pct,
            bg_color=bg_dark,
            text_color=txt_color,
            padding_x=10, padding_y=4, radius=8,
        )

    # ── Capa 3: Leyenda en esquina inferior derecha ────────────────────
    _draw_map_legend(draw, W, H, font_pct, font_pct)

    # Convertir a RGB y exportar
    result_rgb = result.convert("RGB")
    buf = io.BytesIO()
    result_rgb.save(buf, format="PNG", dpi=(150, 150))
    buf.seek(0)
    return buf.getvalue()


def _draw_map_legend(draw: ImageDraw.ImageDraw, W: int, H: int,
                     font_title, font_body):
    """Dibuja la leyenda del semáforo sobre el mapa."""
    items = [
        ("#F44336", "Crítico",    "< 20%"),
        ("#FFC107", "En Proceso", "20% – 23.75%"),
        ("#4CAF50", "Óptimo",     "≥ 23.75%"),
    ]
    font_leg = _load_font(15)
    font_leg_bold = _load_font(16)

    lx = W - 210
    ly = H - 175
    pad = 10
    bw = 195
    bh = 155

    # Fondo de la leyenda
    draw.rounded_rectangle(
        [lx - pad, ly - pad, lx + bw, ly + bh],
        radius=10,
        fill=(15, 15, 25, 210),
        outline=(255, 255, 255, 60),
        width=1,
    )

    # Título
    draw.text((lx + 5, ly + 2), "🚦 SEMÁFORO", font=font_leg_bold,
              fill=(180, 210, 255, 255))

    for i, (color_hex, label, rango) in enumerate(items):
        iy = ly + 32 + i * 38
        h_ex = color_hex.lstrip("#")
        c = (int(h_ex[0:2], 16), int(h_ex[2:4], 16), int(h_ex[4:6], 16))
        # Rectángulo de color
        draw.rounded_rectangle([lx + 4, iy, lx + 28, iy + 22],
                                radius=5, fill=c + (230,))
        # Texto
        draw.text((lx + 36, iy + 2), label, font=font_leg_bold,
                  fill=(255, 255, 255, 255))
        draw.text((lx + 36, iy + 18), rango, font=font_leg,
                  fill=(180, 180, 180, 220))


def get_legend_html(thresholds: list = None) -> str:
    """Genera HTML de la leyenda del semáforo para el sidebar."""
    items = [
        ("#F44336", "Crítico",    "0% – 20.0%"),
        ("#FFC107", "En Proceso", "20.0% – 23.75%"),
        ("#4CAF50", "Óptimo",     "≥ 23.75%"),
    ]
    html = '<div style="display:flex;flex-direction:column;gap:8px;">'
    for color, label, rango in items:
        html += f"""
        <div style="display:flex;align-items:center;gap:10px;">
            <div style="width:32px;height:20px;background:{color};border-radius:5px;
                        border:1px solid rgba(0,0,0,.2);flex-shrink:0;"></div>
            <div>
                <span style="font-size:13px;font-weight:700;">{label}</span><br>
                <span style="font-size:11px;color:#94a3b8;">{rango}</span>
            </div>
        </div>"""
    html += "</div>"
    return html
