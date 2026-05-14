"""
map_renderer.py
Colorea el mapa PNG de Huancavelica con flood-fill según cobertura (semáforo).
Umbrales: >=33.2% Logrado (verde), 26.4-33.1% En Proceso (amarillo), <=26.3% Crítico (rojo)
"""
import io
import os
from PIL import Image, ImageDraw, ImageFont
import pandas as pd

MAP_PATH = "mapa-departamento-huancavelica-provincias.png"

# Puntos semilla por provincia (coordenadas px en imagen 827×1170)
PROVINCE_SEEDS = {
    "TAYACAJA":       [(530, 180), (480, 140), (600, 200)],
    "CHURCAMPA":      [(630, 335), (660, 345)],
    "ACOBAMBA":       [(575, 450), (600, 430)],
    "HUANCAVELICA":   [(330, 430), (360, 380), (300, 500)],
    "ANGARAES":       [(540, 580), (560, 600), (520, 550)],
    "CASTROVIRREYNA": [(190, 630), (160, 600), (220, 660)],
    "HUAYTARA":       [(420, 820), (380, 800), (450, 850)],
}

LABEL_POSITIONS = {
    "TAYACAJA":       {"pct": (480, 188), "num": (480, 224)},
    "CHURCAMPA":      {"pct": (614, 345), "num": (614, 381)},
    "ACOBAMBA":       {"pct": (558, 448), "num": (558, 482)},
    "HUANCAVELICA":   {"pct": (305, 435), "num": (305, 471)},
    "ANGARAES":       {"pct": (524, 588), "num": (524, 622)},
    "CASTROVIRREYNA": {"pct": (172, 638), "num": (172, 674)},
    "HUAYTARA":       {"pct": (395, 825), "num": (395, 861)},
}


def _hex_to_rgba(hex_color: str, alpha: int = 185) -> tuple:
    h = hex_color.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), alpha)


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    for name in [
        "arialbd.ttf", "arial.ttf",
        "DejaVuSans-Bold.ttf", "DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
    ]:
        try:
            return ImageFont.truetype(name, size)
        except Exception:
            continue
    return ImageFont.load_default()


def _draw_badge(draw, cx, cy, text, font, bg_color, text_color=(255, 255, 255),
                pad_x=10, pad_y=4, radius=8):
    bbox = font.getbbox(text)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    w, h = tw + pad_x * 2, th + pad_y * 2
    x0, y0 = cx - w // 2, cy - h // 2
    draw.rounded_rectangle([x0, y0, x0 + w, y0 + h], radius=radius,
                            fill=bg_color + (210,), outline=(255, 255, 255, 120), width=1)
    draw.text((cx, cy), text, font=font, fill=text_color + (255,), anchor="mm")


def render_colored_map(df: pd.DataFrame, vacuna: str,
                       map_path: str = MAP_PATH) -> bytes:
    """
    Genera mapa PNG con provincias coloreadas según semáforo y badges de cobertura.
    Retorna bytes PNG.
    """
    img = Image.open(map_path).convert("RGBA")
    colored = img.copy()

    df_vac = df[df["vacuna"] == vacuna]

    # Flood-fill por provincia
    for _, row in df_vac.iterrows():
        prov = row["provincia"]
        color = _hex_to_rgba(row["sem_color"], alpha=195)
        for seed in PROVINCE_SEEDS.get(prov, []):
            try:
                px = colored.getpixel(seed)
                if px[0] > 50 or px[1] > 50 or px[2] > 50:
                    ImageDraw.floodfill(colored, seed, color, thresh=80)
                    break
            except Exception:
                continue

    result = Image.alpha_composite(img, colored)
    draw = ImageDraw.Draw(result)
    font = _load_font(18)

    # Badges de % por provincia
    for _, row in df_vac.iterrows():
        prov = row["provincia"]
        pos = LABEL_POSITIONS.get(prov)
        if not pos:
            continue
        hex_c = row["sem_color"].lstrip("#")
        bg = (int(hex_c[0:2], 16), int(hex_c[2:4], 16), int(hex_c[4:6], 16))
        bg_dark = tuple(max(0, c - 40) for c in bg)
        txt_color = (30, 20, 0) if row["sem_color"] == "#f59e0b" else (255, 255, 255)
        _draw_badge(draw, pos["pct"][0], pos["pct"][1],
                    f"{row['cobertura_pct']:.1f}%", font, bg_dark, txt_color)

    # Leyenda
    _draw_legend(draw, result.size[0], result.size[1])

    buf = io.BytesIO()
    result.convert("RGB").save(buf, format="PNG", dpi=(150, 150))
    buf.seek(0)
    return buf.getvalue()


def _draw_legend(draw, W, H):
    items = [
        ("#22c55e", "Logrado",    "≥ 33.2%"),
        ("#f59e0b", "En Proceso", "26.4–33.1%"),
        ("#ef4444", "Crítico",    "≤ 26.3%"),
    ]
    font_b = _load_font(16)
    font_s = _load_font(14)
    lx, ly = W - 210, H - 175
    pad, bw, bh = 10, 195, 155
    draw.rounded_rectangle([lx - pad, ly - pad, lx + bw, ly + bh],
                            radius=10, fill=(15, 15, 25, 210),
                            outline=(255, 255, 255, 60), width=1)
    draw.text((lx + 5, ly + 2), "SEMÁFORO", font=font_b, fill=(180, 210, 255, 255))
    for i, (color_hex, label, rango) in enumerate(items):
        iy = ly + 32 + i * 38
        h_ex = color_hex.lstrip("#")
        c = (int(h_ex[0:2], 16), int(h_ex[2:4], 16), int(h_ex[4:6], 16))
        draw.rounded_rectangle([lx + 4, iy, lx + 28, iy + 22], radius=5, fill=c + (230,))
        draw.text((lx + 36, iy + 2), label, font=font_b, fill=(255, 255, 255, 255))
        draw.text((lx + 36, iy + 18), rango, font=font_s, fill=(180, 180, 180, 220))


def get_legend_html() -> str:
    items = [
        ("#22c55e", "Logrado",    "≥ 33.2%"),
        ("#f59e0b", "En Proceso", "26.4% – 33.1%"),
        ("#ef4444", "Crítico",    "≤ 26.3%"),
    ]
    html = '<div style="display:flex;flex-direction:column;gap:8px;">'
    for color, label, rango in items:
        html += f"""
        <div style="display:flex;align-items:center;gap:10px;">
            <div style="width:28px;height:16px;background:{color};border-radius:4px;"></div>
            <div>
                <span style="font-size:13px;font-weight:700;color:#e2e8f0;">{label}</span><br>
                <span style="font-size:11px;color:#94a3b8;">{rango}</span>
            </div>
        </div>"""
    html += "</div>"
    return html
