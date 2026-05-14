# Dashboard Vacunación Huancavelica — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reconstruir el dashboard Streamlit de coberturas de vacunación DIRESA Huancavelica usando el nuevo Excel (9 vacunas por provincia), mapa coroplético real GeoJSON + Plotly, semáforo con umbrales ≥33.2%/26.4%/≤26.3%, vista general + detalle interactivo, y exportación PDF/PNG.

**Architecture:** App modular con `data_loader.py` (lectura/normalización Excel), `map_utils.py` (mapa GeoJSON Plotly), `charts.py` (gauge/barras/semáforo), y `app.py` (UI Streamlit con navegación session_state entre vista general y detalle). El Excel por defecto vive en `data/coberturas.xlsx`; el uploader lo reemplaza en sesión.

**Tech Stack:** Python 3.11, Streamlit ≥1.32, Plotly ≥5.18, pandas ≥2.0, openpyxl ≥3.1, kaleido ≥0.2.1, reportlab ≥4.0, requests ≥2.31

---

## Task 1: Estructura de proyecto + requirements

**Files:**
- Modify: `requirements.txt`
- Create: `data/` (carpeta)
- Create: `assets/` (carpeta)

- [ ] **Step 1: Actualizar requirements.txt**

```
streamlit>=1.32.0
pandas>=2.0.0
openpyxl>=3.1.0
plotly>=5.18.0
kaleido>=0.2.1
reportlab>=4.0.0
requests>=2.31.0
```

- [ ] **Step 2: Crear carpetas data/ y assets/**

```bash
mkdir data
mkdir assets
```

- [ ] **Step 3: Copiar Excel a data/coberturas.xlsx**

Copiar el archivo `Coberturas de Vacunacion por Provincias.xlsx` descargado a `data/coberturas.xlsx`. Este archivo tiene 9 hojas (BCG, 3ª Pentavalente, 1ª SPR, 2ª SPR, 2ª SPR (2), DPTa, VPH 9 años, VPH 10 años, Neumococo). Cada hoja tiene columnas: RIS (provincia), META PADRON NOMINAL (PN) 2024, [dosis], %.

- [ ] **Step 4: Instalar dependencias**

```bash
pip install -r requirements.txt
```

Expected: instalación exitosa de todos los paquetes.

- [ ] **Step 5: Commit**

```bash
git add requirements.txt
git commit -m "chore: actualizar requirements para nueva arquitectura"
```

---

## Task 2: Obtener GeoJSON de provincias de Huancavelica

**Files:**
- Create: `assets/huancavelica.geojson`
- Create: `download_geojson.py` (script de utilidad, no parte del app)

- [ ] **Step 1: Crear script de descarga**

Crear `download_geojson.py`:

```python
"""
Script de utilidad (ejecutar una sola vez).
Descarga el GeoJSON de provincias del Perú y extrae solo Huancavelica.
Guarda: assets/huancavelica.geojson
"""
import json
import requests
import os

# GeoJSON de provincias del Perú — fuente: datos.gob.pe / INEI
URL = "https://raw.githubusercontent.com/juaneladio/peru-geojson/master/peru_provincias_geo.json"

os.makedirs("assets", exist_ok=True)
print("Descargando GeoJSON de provincias de Perú...")
resp = requests.get(URL, timeout=30)
resp.raise_for_status()
data = resp.json()

# Filtrar solo Huancavelica
# Inspeccionar las propiedades disponibles:
if data["features"]:
    print("Propiedades disponibles:", list(data["features"][0]["properties"].keys()))

# Ajustar el nombre del campo según la salida anterior.
# Campos comunes: DEPARTAMEN, NOMBDEP, NAME_1
DEPT_FIELD = "DEPARTAMEN"  # Cambiar si la salida muestra otro nombre
DEPT_VALUE = "HUANCAVELICA"

hvca_features = [
    f for f in data["features"]
    if str(f["properties"].get(DEPT_FIELD, "")).upper() == DEPT_VALUE
]
print(f"Provincias encontradas: {len(hvca_features)}")
for f in hvca_features:
    print(" -", f["properties"])

huancavelica_geojson = {
    "type": "FeatureCollection",
    "features": hvca_features
}

with open("assets/huancavelica.geojson", "w", encoding="utf-8") as fp:
    json.dump(huancavelica_geojson, fp, ensure_ascii=False, indent=2)

print("✅ Guardado en assets/huancavelica.geojson")
```

- [ ] **Step 2: Ejecutar el script**

```bash
python download_geojson.py
```

Expected output (ejemplo):
```
Descargando GeoJSON de provincias de Perú...
Propiedades disponibles: ['DEPARTAMEN', 'PROVINCIA', 'UBIGEO', ...]
Provincias encontradas: 7
 - {'DEPARTAMEN': 'HUANCAVELICA', 'PROVINCIA': 'ACOBAMBA', ...}
 - {'DEPARTAMEN': 'HUANCAVELICA', 'PROVINCIA': 'ANGARAES', ...}
 ...
✅ Guardado en assets/huancavelica.geojson
```

Si la URL falla o el campo de departamento es distinto, ajustar `URL` y `DEPT_FIELD` según la salida real. Si el campo de provincia se llama distinto a "PROVINCIA", anotar el nombre real — se usará en `map_utils.py`.

- [ ] **Step 3: Verificar el GeoJSON**

```python
import json
with open("assets/huancavelica.geojson") as f:
    g = json.load(f)
print(len(g["features"]))  # debe ser 7
print(g["features"][0]["properties"])  # ver nombres de campo
```

Anotar el campo que contiene el nombre de provincia (ej. "PROVINCIA", "NOMBPROV", "NAME_2"). Se usará como `GEOJSON_PROV_FIELD` en `map_utils.py`.

- [ ] **Step 4: Commit**

```bash
git add assets/huancavelica.geojson download_geojson.py
git commit -m "feat: agregar GeoJSON de provincias de Huancavelica"
```

---

## Task 3: Reescribir data_loader.py

**Files:**
- Modify: `data_loader.py` (reemplazar completamente)
- Create: `tests/test_data_loader.py`

El nuevo Excel tiene estructura diferente al anterior: 9 hojas, columnas por posición (0=RIS/provincia, 1=meta, 2=dosis, 3=%). Los % pueden venir como decimal (0.282) o como porcentaje (28.2). Los umbrales cambian a ≥33.2% verde, 26.4–33.1% amarillo, ≤26.3% rojo.

- [ ] **Step 1: Escribir tests que fallan**

Crear `tests/test_data_loader.py`:

```python
import pytest
import pandas as pd
from io import BytesIO
import openpyxl
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from data_loader import normalize_pct, assign_semaforo, THRESHOLDS


def test_normalize_pct_decimal():
    """0.282 debe convertirse a 28.2"""
    assert normalize_pct(0.282) == pytest.approx(28.2, rel=1e-3)


def test_normalize_pct_already_pct():
    """28.2 ya es porcentaje, debe quedarse igual"""
    assert normalize_pct(28.2) == pytest.approx(28.2, rel=1e-3)


def test_normalize_pct_zero():
    assert normalize_pct(0) == 0.0


def test_normalize_pct_none():
    assert normalize_pct(None) == 0.0


def test_assign_semaforo_verde():
    assert assign_semaforo(33.2) == "verde"
    assert assign_semaforo(50.0) == "verde"


def test_assign_semaforo_amarillo():
    assert assign_semaforo(26.4) == "amarillo"
    assert assign_semaforo(30.0) == "amarillo"
    assert assign_semaforo(33.1) == "amarillo"


def test_assign_semaforo_rojo():
    assert assign_semaforo(26.3) == "rojo"
    assert assign_semaforo(0.0)  == "rojo"
    assert assign_semaforo(10.0) == "rojo"


def test_thresholds_values():
    assert THRESHOLDS["verde"] == 33.2
    assert THRESHOLDS["amarillo"] == 26.4
```

- [ ] **Step 2: Ejecutar tests para confirmar que fallan**

```bash
python -m pytest tests/test_data_loader.py -v
```

Expected: ImportError o AttributeError (data_loader no tiene las funciones nuevas).

- [ ] **Step 3: Reescribir data_loader.py**

```python
"""
data_loader.py
Carga y normaliza el Excel de coberturas por provincia DIRESA Huancavelica.
Excel esperado: 9 hojas (una por vacuna), columnas:
  col 0 = RIS/provincia, col 1 = META, col 2 = dosis, col 3 = %
"""
import pandas as pd
from pathlib import Path
from typing import Union
import io

DEFAULT_EXCEL = Path("data/coberturas.xlsx")

# Umbrales semáforo (% cobertura)
THRESHOLDS = {"verde": 33.2, "amarillo": 26.4}

SEMAFORO_CONFIG = {
    "verde":    {"label": "Logrado",    "color": "#22c55e", "bg": "#f0fdf4", "dark": "#15803d"},
    "amarillo": {"label": "En Proceso", "color": "#f59e0b", "bg": "#fffbeb", "dark": "#b45309"},
    "rojo":     {"label": "Crítico",    "color": "#ef4444", "bg": "#fef2f2", "dark": "#b91c1c"},
}

PROVINCIAS = {
    "HUANCAVELICA", "ACOBAMBA", "TAYACAJA",
    "ANGARAES", "CASTROVIRREYNA", "CHURCAMPA", "HUAYTARA", "HUAYTARÁ",
}

SKIP_ROWS = {"RIS", "TOTAL", "DIRESA", "PROVINCIA", "REGIÓN", "REGION", ""}


def normalize_pct(val) -> float:
    """Convierte 0.282 → 28.2. Valores ≥ 2 se asumen ya como porcentaje."""
    try:
        f = float(str(val).replace(",", ".").strip())
        return round(f * 100, 2) if f < 2 else round(f, 2)
    except (ValueError, TypeError):
        return 0.0


def normalize_province(name: str) -> str:
    """Normaliza nombre de provincia: mayúsculas, sin tildes en A."""
    return (
        str(name).strip().upper()
        .replace("Á", "A").replace("É", "E").replace("Í", "I")
        .replace("Ó", "O").replace("Ú", "U").replace("Ü", "U")
    )


def assign_semaforo(pct: float) -> str:
    """Retorna 'verde', 'amarillo' o 'rojo' según el % de cobertura."""
    if pct >= THRESHOLDS["verde"]:
        return "verde"
    if pct >= THRESHOLDS["amarillo"]:
        return "amarillo"
    return "rojo"


def _parse_sheet(sheet_name: str, df_raw: pd.DataFrame) -> list[dict]:
    """Extrae filas válidas de una hoja del Excel."""
    records = []
    for _, row in df_raw.iterrows():
        prov_raw = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ""
        prov = normalize_province(prov_raw)
        if prov in SKIP_ROWS:
            continue
        # Aceptar provincias conocidas o cualquier valor no vacío como provincia
        try:
            meta  = int(float(str(row.iloc[1]).replace(",", ""))) if pd.notna(row.iloc[1]) else 0
            dosis = int(float(str(row.iloc[2]).replace(",", ""))) if pd.notna(row.iloc[2]) else 0
            pct_raw = row.iloc[3] if len(row) > 3 and pd.notna(row.iloc[3]) else None
            pct   = normalize_pct(pct_raw) if pct_raw is not None else (
                round(dosis / meta * 100, 2) if meta > 0 else 0.0
            )
        except (ValueError, IndexError):
            continue
        if meta == 0 and dosis == 0:
            continue
        sem = assign_semaforo(pct)
        records.append({
            "vacuna":        sheet_name,
            "provincia":     prov,
            "meta":          meta,
            "dosis":         dosis,
            "cobertura_pct": pct,
            "semaforo":      sem,
            "sem_label":     SEMAFORO_CONFIG[sem]["label"],
            "sem_color":     SEMAFORO_CONFIG[sem]["color"],
            "sem_bg":        SEMAFORO_CONFIG[sem]["bg"],
            "sem_dark":      SEMAFORO_CONFIG[sem]["dark"],
        })
    return records


def load_excel(source: Union[str, Path, bytes, None] = None) -> pd.DataFrame:
    """
    Carga el Excel de coberturas. 
    source: ruta de archivo, BytesIO, bytes, o None (usa DEFAULT_EXCEL).
    Retorna DataFrame con columnas:
      vacuna, provincia, meta, dosis, cobertura_pct,
      semaforo, sem_label, sem_color, sem_bg, sem_dark
    """
    if source is None:
        source = DEFAULT_EXCEL
    if isinstance(source, bytes):
        source = io.BytesIO(source)

    xl = pd.ExcelFile(source, engine="openpyxl")
    records = []
    for sheet in xl.sheet_names:
        try:
            df_raw = xl.parse(sheet, header=0)
            if df_raw.empty or len(df_raw.columns) < 3:
                continue
            records.extend(_parse_sheet(sheet, df_raw))
        except Exception:
            continue
    return pd.DataFrame(records)


def get_vaccine_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Resumen por vacuna: total meta, dosis, cobertura_pct ponderada."""
    agg = df.groupby("vacuna").agg(
        meta=("meta", "sum"),
        dosis=("dosis", "sum"),
    ).reset_index()
    agg["cobertura_pct"] = (agg["dosis"] / agg["meta"] * 100).round(2).fillna(0)
    agg["semaforo"] = agg["cobertura_pct"].apply(assign_semaforo)
    for col in ("sem_label", "sem_color", "sem_bg", "sem_dark"):
        key = col.replace("sem_", "")
        agg[col] = agg["semaforo"].map(
            lambda s, c=col: SEMAFORO_CONFIG[s][c.replace("sem_", "") if c != "sem_label" else "label"]
        )
    return agg


def get_pivot(df: pd.DataFrame) -> pd.DataFrame:
    """Tabla pivote: filas=provincia, columnas=vacuna, valores=cobertura_pct."""
    return df.pivot_table(
        index="provincia", columns="vacuna",
        values="cobertura_pct", aggfunc="first"
    ).reset_index()
```

- [ ] **Step 4: Ejecutar tests para confirmar que pasan**

```bash
python -m pytest tests/test_data_loader.py -v
```

Expected: todos los tests en PASS.

- [ ] **Step 5: Test de integración rápido con el Excel real**

```bash
python -c "
from data_loader import load_excel, get_vaccine_summary
df = load_excel()
print('Filas:', len(df))
print('Vacunas:', df['vacuna'].unique().tolist())
print('Provincias:', df['provincia'].unique().tolist())
print(get_vaccine_summary(df)[['vacuna','cobertura_pct','sem_label']])
"
```

Expected: 9 vacunas × 7 provincias = ~63 filas (puede variar). Ver semáforos correctos.

- [ ] **Step 6: Commit**

```bash
git add data_loader.py tests/test_data_loader.py
git commit -m "feat: reescribir data_loader para nuevo Excel (9 vacunas, umbrales 33.2/26.4%)"
```

---

## Task 4: Crear map_utils.py (mapa coroplético GeoJSON + Plotly)

**Files:**
- Create: `map_utils.py`
- Create: `tests/test_map_utils.py`

El mapa usa `plotly.graph_objects.Choroplethmapbox` con el GeoJSON de Huancavelica. Las provincias se colorean según cobertura_pct con escala rojo→amarillo→verde. El tooltip muestra nombre, %, dosis, meta y estado semáforo.

- [ ] **Step 1: Escribir tests que fallan**

Crear `tests/test_map_utils.py`:

```python
import pytest
import pandas as pd
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from map_utils import get_province_color, GEOJSON_PROV_FIELD


def test_get_province_color_verde():
    color = get_province_color(35.0)
    assert color == "#22c55e"


def test_get_province_color_amarillo():
    color = get_province_color(30.0)
    assert color == "#f59e0b"


def test_get_province_color_rojo():
    color = get_province_color(20.0)
    assert color == "#ef4444"


def test_geojson_field_defined():
    assert isinstance(GEOJSON_PROV_FIELD, str)
    assert len(GEOJSON_PROV_FIELD) > 0
```

- [ ] **Step 2: Ejecutar tests para confirmar que fallan**

```bash
python -m pytest tests/test_map_utils.py -v
```

Expected: ImportError (map_utils no existe aún).

- [ ] **Step 3: Crear map_utils.py**

**IMPORTANTE:** Antes de escribir este archivo, abrir `assets/huancavelica.geojson` y verificar el nombre del campo de provincia (puede ser "PROVINCIA", "NOMBPROV", "NAME_2", etc.). Reemplazar `"PROVINCIA"` en `GEOJSON_PROV_FIELD` con el nombre real.

```python
"""
map_utils.py
Mapa coroplético de Huancavelica usando GeoJSON real + Plotly Mapbox.
"""
import json
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path
from data_loader import SEMAFORO_CONFIG, THRESHOLDS, assign_semaforo

GEOJSON_PATH = Path("assets/huancavelica.geojson")

# ⚠️ Verificar contra assets/huancavelica.geojson — puede ser
# "PROVINCIA", "NOMBPROV", "NAME_2", etc.
GEOJSON_PROV_FIELD = "PROVINCIA"

# Normalización de nombres de provincia en el GeoJSON → Excel
PROV_ALIAS = {
    "HUAYTARÁ": "HUAYTARA",
    "HUAYTARA": "HUAYTARA",
}


def _load_geojson() -> dict:
    with open(GEOJSON_PATH, encoding="utf-8") as f:
        return json.load(f)


def get_province_color(pct: float) -> str:
    """Retorna color hex según semáforo."""
    return SEMAFORO_CONFIG[assign_semaforo(pct)]["color"]


def _normalize_geojson_name(name: str) -> str:
    """Normaliza nombre del GeoJSON para matchear con el Excel."""
    n = str(name).strip().upper()
    n = n.replace("Á","A").replace("É","E").replace("Í","I").replace("Ó","O").replace("Ú","U")
    return PROV_ALIAS.get(n, n)


def build_choropleth(
    df_vacuna: pd.DataFrame,
    vacuna_name: str,
    height: int = 500,
) -> go.Figure:
    """
    Construye mapa coroplético de Huancavelica.
    df_vacuna: DataFrame filtrado para una sola vacuna (columnas: provincia, cobertura_pct, dosis, meta, sem_label).
    vacuna_name: nombre para el título.
    """
    geojson = _load_geojson()

    # Normalizar nombres en GeoJSON para unir con DataFrame
    for feat in geojson["features"]:
        raw = feat["properties"].get(GEOJSON_PROV_FIELD, "")
        feat["properties"]["_prov_key"] = _normalize_geojson_name(raw)

    # Preparar data
    df = df_vacuna.copy()
    df["_prov_key"] = df["provincia"].apply(
        lambda p: PROV_ALIAS.get(p.upper(), p.upper())
    )

    # Colores por provincia
    color_map = {row["_prov_key"]: row["cobertura_pct"] for _, row in df.iterrows()}
    hover_map = {
        row["_prov_key"]: (
            f"<b>{row['provincia']}</b><br>"
            f"Cobertura: <b>{row['cobertura_pct']:.1f}%</b><br>"
            f"Dosis: {int(row['dosis']):,} / Meta: {int(row['meta']):,}<br>"
            f"Estado: {row['sem_label']}"
        )
        for _, row in df.iterrows()
    }

    locations = [f["properties"]["_prov_key"] for f in geojson["features"]]
    z_values  = [color_map.get(loc, 0) for loc in locations]
    hover_texts = [hover_map.get(loc, loc) for loc in locations]

    colorscale = [
        [0.0,  "#ef4444"],   # rojo  (≤26.3%)
        [0.35, "#f59e0b"],   # amarillo (26.4–33.1%)
        [0.65, "#22c55e"],   # verde (≥33.2%)
        [1.0,  "#15803d"],   # verde oscuro
    ]

    fig = go.Figure(go.Choroplethmapbox(
        geojson=geojson,
        locations=locations,
        featureidkey=f"properties._prov_key",
        z=z_values,
        colorscale=colorscale,
        zmin=0,
        zmax=max(50, max(z_values) + 5) if z_values else 50,
        text=hover_texts,
        hovertemplate="%{text}<extra></extra>",
        marker_line_color="white",
        marker_line_width=1.5,
        colorbar=dict(
            title="Cobertura %",
            thickness=12,
            len=0.6,
            tickfont=dict(color="#475569"),
            titlefont=dict(color="#475569"),
        ),
    ))

    # Calcular centro aproximado de Huancavelica
    fig.update_layout(
        mapbox_style="carto-positron",
        mapbox_zoom=7.2,
        mapbox_center={"lat": -13.0, "lon": -74.8},
        margin=dict(t=40, b=0, l=0, r=0),
        height=height,
        title=dict(
            text=f"Cobertura {vacuna_name} — Huancavelica",
            font=dict(size=14, color="#1e3a5f"),
            x=0.01,
        ),
        paper_bgcolor="white",
    )
    return fig
```

- [ ] **Step 4: Ejecutar tests**

```bash
python -m pytest tests/test_map_utils.py -v
```

Expected: todos en PASS.

- [ ] **Step 5: Test visual rápido**

```bash
python -c "
from data_loader import load_excel
from map_utils import build_choropleth
df = load_excel()
df_vac = df[df['vacuna'] == df['vacuna'].iloc[0]]
fig = build_choropleth(df_vac, df['vacuna'].iloc[0])
fig.write_html('/tmp/test_map.html')
print('Abrir /tmp/test_map.html en el navegador para verificar el mapa')
"
```

Si el mapa no muestra provincias: verificar que `GEOJSON_PROV_FIELD` y la normalización de nombres sean correctos. Agregar print de `locations` y compararlos con `df['provincia'].unique()`.

- [ ] **Step 6: Commit**

```bash
git add map_utils.py tests/test_map_utils.py
git commit -m "feat: crear map_utils con mapa coropletico GeoJSON + Plotly para Huancavelica"
```

---

## Task 5: Crear charts.py (gauge, barras, semáforo, tarjetas)

**Files:**
- Create: `charts.py`
- Create: `tests/test_charts.py`

- [ ] **Step 1: Escribir tests que fallan**

Crear `tests/test_charts.py`:

```python
import pytest
import pandas as pd
import plotly.graph_objects as go
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from charts import build_gauge, build_bar_chart, build_semaforo_html


def test_build_gauge_returns_figure():
    fig = build_gauge(30.2, "Cobertura Dept.")
    assert isinstance(fig, go.Figure)


def test_build_bar_chart_returns_figure():
    df = pd.DataFrame({
        "provincia": ["HUANCAVELICA", "ACOBAMBA", "TAYACAJA"],
        "cobertura_pct": [35.0, 25.0, 30.0],
        "dosis": [100, 60, 80],
        "meta": [280, 240, 266],
        "sem_color": ["#22c55e", "#ef4444", "#f59e0b"],
        "sem_label": ["Logrado", "Crítico", "En Proceso"],
    })
    fig = build_bar_chart(df, "BCG")
    assert isinstance(fig, go.Figure)


def test_build_semaforo_html_returns_string():
    html = build_semaforo_html(3, 1, 3)
    assert isinstance(html, str)
    assert "verde" in html.lower() or "#22c55e" in html.lower()
```

- [ ] **Step 2: Ejecutar tests para confirmar que fallan**

```bash
python -m pytest tests/test_charts.py -v
```

Expected: ImportError.

- [ ] **Step 3: Crear charts.py**

```python
"""
charts.py
Componentes Plotly y HTML para el dashboard de vacunación.
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
        number={"suffix": "%", "font": {"size": 30, "color": "#1e293b", "family": "Inter"}},
        title={"text": title, "font": {"size": 12, "color": "#64748b"}},
        gauge={
            "axis": {
                "range": [0, 60],
                "tickcolor": "#94a3b8",
                "tickfont": {"color": "#94a3b8", "size": 10},
                "tickvals": [0, THRESHOLDS["amarillo"], THRESHOLDS["verde"], 60],
                "ticktext": ["0%", f"{THRESHOLDS['amarillo']}%", f"{THRESHOLDS['verde']}%", "60%"],
            },
            "bar": {"color": color, "thickness": 0.3},
            "bgcolor": "#f8fafc",
            "bordercolor": "#e2e8f0",
            "borderwidth": 1,
            "steps": [
                {"range": [0, THRESHOLDS["amarillo"]],                   "color": "#fef2f2"},
                {"range": [THRESHOLDS["amarillo"], THRESHOLDS["verde"]], "color": "#fffbeb"},
                {"range": [THRESHOLDS["verde"], 60],                     "color": "#f0fdf4"},
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
        margin=dict(t=50, b=10, l=30, r=30),
        paper_bgcolor="white",
        plot_bgcolor="white",
        font={"family": "Inter"},
    )
    return fig


def build_bar_chart(df_vacuna: pd.DataFrame, vacuna_name: str) -> go.Figure:
    """Gráfico horizontal de barras por provincia."""
    df = df_vacuna.sort_values("cobertura_pct", ascending=True)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        y=df["provincia"],
        x=df["cobertura_pct"],
        orientation="h",
        marker_color=df["sem_color"].tolist(),
        marker_line_width=0,
        text=[f" {v:.1f}%  ({int(d):,}/{int(m):,})"
              for v, d, m in zip(df["cobertura_pct"], df["dosis"], df["meta"])],
        textposition="inside",
        textfont={"color": "white", "size": 12, "family": "Inter"},
        hovertemplate="<b>%{y}</b><br>Cobertura: %{x:.1f}%<extra></extra>",
    ))

    # Líneas semáforo
    for thresh, color, label in [
        (THRESHOLDS["amarillo"], "#ef4444", f"{THRESHOLDS['amarillo']}% — Crítico"),
        (THRESHOLDS["verde"],    "#22c55e", f"{THRESHOLDS['verde']}% — Logrado"),
    ]:
        fig.add_vline(
            x=thresh, line_dash="dash", line_color=color, line_width=1.5,
            annotation_text=label,
            annotation_font_color=color,
            annotation_font_size=10,
            annotation_position="top right",
        )

    fig.update_layout(
        title=dict(text=f"Cobertura por Provincia — {vacuna_name}",
                   font=dict(size=13, color="#1e3a5f")),
        xaxis=dict(
            title="% Cobertura",
            range=[0, max(df["cobertura_pct"].max() * 1.2, 50)],
            gridcolor="#f1f5f9",
            color="#64748b",
        ),
        yaxis=dict(color="#475569"),
        paper_bgcolor="white",
        plot_bgcolor="white",
        height=300,
        margin=dict(t=50, b=30, l=10, r=20),
        font={"family": "Inter"},
    )
    return fig


def build_semaforo_html(n_verde: int, n_amarillo: int, n_rojo: int) -> str:
    """HTML del semáforo de provincias para mostrar en Streamlit."""
    total = n_verde + n_amarillo + n_rojo
    rows = [
        ("#22c55e", f"≥ {THRESHOLDS['verde']}%", "Logrado",    n_verde),
        ("#f59e0b", f"{THRESHOLDS['amarillo']}–{THRESHOLDS['verde']-0.1:.1f}%", "En Proceso", n_amarillo),
        ("#ef4444", f"≤ {THRESHOLDS['amarillo']-0.1:.1f}%",  "Crítico",    n_rojo),
    ]
    items = ""
    for color, rango, label, n in rows:
        pct_bar = (n / total * 100) if total > 0 else 0
        items += f"""
        <div style="display:flex;align-items:center;gap:10px;padding:8px 0;
                    border-bottom:1px solid #f1f5f9;">
            <div style="width:12px;height:12px;border-radius:50%;background:{color};flex-shrink:0;"></div>
            <div style="font-size:11px;font-weight:600;color:{color};min-width:130px;">{rango}</div>
            <div style="flex:1;height:6px;background:#f1f5f9;border-radius:3px;overflow:hidden;">
                <div style="width:{pct_bar:.0f}%;height:100%;background:{color};border-radius:3px;"></div>
            </div>
            <div style="font-size:13px;font-weight:800;color:{color};min-width:50px;text-align:right;">
                {n} prov.
            </div>
        </div>"""
    return f'<div style="font-family:Inter,sans-serif;">{items}</div>'


def build_vaccine_card_html(
    vacuna: str,
    cobertura_pct: float,
    dosis: int,
    meta: int,
    sem_color: str,
    sem_label: str,
    sem_bg: str,
    selected: bool = False,
) -> str:
    """HTML de tarjeta de vacuna para vista general."""
    border = f"3px solid {sem_color}" if selected else f"1px solid #e2e8f0"
    shadow = "0 4px 16px rgba(0,0,0,.12)" if selected else "0 1px 4px rgba(0,0,0,.07)"
    return f"""
    <div style="background:white;border-radius:12px;padding:16px;border:{border};
                box-shadow:{shadow};cursor:pointer;transition:all .2s;text-align:center;">
        <div style="font-size:10px;font-weight:700;letter-spacing:1.5px;color:#64748b;
                    text-transform:uppercase;margin-bottom:8px;">{vacuna}</div>
        <div style="font-size:28px;font-weight:800;color:{sem_color};line-height:1;">
            {cobertura_pct:.1f}%
        </div>
        <div style="font-size:10px;color:#94a3b8;margin:4px 0 8px;">
            {int(dosis):,} / {int(meta):,} dosis
        </div>
        <div style="display:inline-block;padding:3px 12px;border-radius:20px;
                    background:{sem_bg};color:{sem_color};font-size:10px;font-weight:700;
                    border:1px solid {sem_color}33;">
            {sem_label}
        </div>
    </div>"""
```

- [ ] **Step 4: Ejecutar tests**

```bash
python -m pytest tests/test_charts.py -v
```

Expected: todos en PASS.

- [ ] **Step 5: Commit**

```bash
git add charts.py tests/test_charts.py
git commit -m "feat: crear charts.py con gauge, barras, semaforo y tarjetas de vacuna"
```

---

## Task 6: Reescribir app.py — Vista general (9 tarjetas de vacunas)

**Files:**
- Modify: `app.py` (reemplazar completamente)

La vista general muestra las 9 tarjetas de vacunas con su semáforo, un mapa coroplético general coloreado por la primera vacuna o la vacuna con mayor cobertura, y KPIs globales. Al hacer clic en una tarjeta se navega a la vista de detalle via `st.session_state`.

- [ ] **Step 1: Reescribir app.py con vista general**

```python
"""
app.py — Dashboard Coberturas de Vacunación DIRESA Huancavelica
Streamlit · Publicar en Streamlit Cloud
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from io import BytesIO
from pathlib import Path

from data_loader import load_excel, get_vaccine_summary, get_pivot, SEMAFORO_CONFIG
from map_utils import build_choropleth
from charts import build_gauge, build_bar_chart, build_semaforo_html, build_vaccine_card_html
from export_utils import export_pdf, export_png

# ── Configuración Streamlit ───────────────────────────────────────────────
st.set_page_config(
    page_title="Dashboard Vacunación — DIRESA Huancavelica",
    page_icon="💉",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS global ────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.stApp { background: #f8fafc; }
.main-header {
    background: linear-gradient(135deg, #1e3a5f 0%, #1d4ed8 60%, #0ea5e9 100%);
    border-radius: 16px; padding: 24px 32px; margin-bottom: 20px;
    box-shadow: 0 8px 32px rgba(30,58,95,0.25);
    display: flex; align-items: center; justify-content: space-between;
}
.main-header h1 { color: white; font-size: 1.5rem; font-weight: 800; margin: 0; }
.main-header p  { color: rgba(255,255,255,.75); font-size: 0.82rem; margin: 4px 0 0; }
.section-title {
    font-size: 0.78rem; font-weight: 700; letter-spacing: 2px;
    text-transform: uppercase; color: #64748b;
    display: flex; align-items: center; gap: 8px; margin: 16px 0 10px;
}
.section-title::before {
    content: ''; width: 3px; height: 14px;
    background: #1d4ed8; border-radius: 2px;
}
.kpi-card {
    background: white; border-radius: 12px; padding: 16px 12px;
    text-align: center; box-shadow: 0 1px 4px rgba(0,0,0,.07);
    border: 1px solid #e2e8f0;
}
.kpi-value { font-size: 1.9rem; font-weight: 800; line-height: 1; margin: 6px 0; }
.kpi-label { font-size: 0.72rem; font-weight: 600; letter-spacing: 1.5px;
              color: #94a3b8; text-transform: uppercase; }
.live-dot  { display: inline-block; width: 8px; height: 8px; border-radius: 50%;
              background: #4ade80; box-shadow: 0 0 6px #4ade80;
              animation: blink 2.5s ease infinite; }
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:.3} }
[data-testid="stSidebar"] { background: #1e293b !important; }
[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
</style>
""", unsafe_allow_html=True)

# ── Session state inicial ─────────────────────────────────────────────────
if "view" not in st.session_state:
    st.session_state.view = "general"
if "selected_vaccine" not in st.session_state:
    st.session_state.selected_vaccine = None

# ── Sidebar ───────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="text-align:center;padding:20px 0 12px;">
        <div style="font-size:2.5rem;">💉</div>
        <div style="font-weight:800;font-size:0.95rem;color:#7dd3fc;">DIRESA HUANCAVELICA</div>
        <div style="font-size:0.75rem;color:#64748b;margin-top:2px;">Dashboard de Vacunación 2026</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("### 📂 Actualizar Datos")
    uploaded = st.file_uploader(
        "Subir nuevo Excel de coberturas",
        type=["xlsx", "xls"],
        help="El Excel debe tener hojas por vacuna con columnas: Provincia, Meta, Dosis, %",
    )
    st.markdown("---")
    st.markdown("### 🚦 Semáforo")
    st.markdown("""
    <div style="font-size:12px;">
        <div style="display:flex;align-items:center;gap:8px;margin:6px 0;">
            <div style="width:12px;height:12px;border-radius:50%;background:#22c55e;"></div>
            <span>≥ 33.2% — Logrado</span>
        </div>
        <div style="display:flex;align-items:center;gap:8px;margin:6px 0;">
            <div style="width:12px;height:12px;border-radius:50%;background:#f59e0b;"></div>
            <span>26.4–33.1% — En Proceso</span>
        </div>
        <div style="display:flex;align-items:center;gap:8px;margin:6px 0;">
            <div style="width:12px;height:12px;border-radius:50%;background:#ef4444;"></div>
            <span>≤ 26.3% — Crítico</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")
    st.markdown("""
    <div style="text-align:center;font-size:0.7rem;color:#475569;padding-top:8px;">
        DIRESA Huancavelica © 2026<br>
        Estrategia Sanitaria de Inmunizaciones
    </div>
    """, unsafe_allow_html=True)

# ── Carga de datos ────────────────────────────────────────────────────────
@st.cache_data(show_spinner=False)
def _load(source_bytes: bytes) -> pd.DataFrame:
    return load_excel(source_bytes)

@st.cache_data(show_spinner=False)
def _load_default() -> pd.DataFrame:
    return load_excel()

if uploaded is not None:
    with st.spinner("Procesando Excel..."):
        df = _load(uploaded.read())
    st.sidebar.success(f"✅ {uploaded.name}")
else:
    with st.spinner("Cargando datos base..."):
        df = _load_default()

if df.empty:
    st.error("No se pudieron cargar datos. Verifica el formato del Excel.")
    st.stop()

vaccine_summary = get_vaccine_summary(df)

# ── Header ────────────────────────────────────────────────────────────────
fecha = datetime.now().strftime("%d/%m/%Y %H:%M")
st.markdown(f"""
<div class="main-header">
    <div>
        <h1>🏥 Dashboard Coberturas de Vacunación</h1>
        <p>Región Huancavelica · DIRESA · Estrategia de Inmunizaciones 2026</p>
    </div>
    <div style="text-align:right;">
        <div class="live-dot"></div>
        <span style="color:#4ade80;font-size:0.8rem;font-weight:600;margin-left:6px;">EN VIVO</span>
        <div style="color:rgba(255,255,255,.6);font-size:0.75rem;margin-top:4px;">{fecha}</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════
# VISTA GENERAL
# ═══════════════════════════════════════════════════════════════════════════
if st.session_state.view == "general":
    _render_general_view(df, vaccine_summary)

# ═══════════════════════════════════════════════════════════════════════════
# VISTA DETALLE
# ═══════════════════════════════════════════════════════════════════════════
elif st.session_state.view == "detail":
    _render_detail_view(df, st.session_state.selected_vaccine)
```

> **Nota:** Las funciones `_render_general_view` y `_render_detail_view` se definen en los pasos siguientes del mismo archivo.

- [ ] **Step 2: Agregar función _render_general_view en app.py**

Agregar antes del bloque `if st.session_state.view == "general":`:

```python
def _render_general_view(df: pd.DataFrame, vaccine_summary: pd.DataFrame):
    # KPIs globales
    total_meta  = df["meta"].sum()
    total_dosis = df["dosis"].sum()
    cob_gral    = round(total_dosis / total_meta * 100, 2) if total_meta > 0 else 0
    n_vacunas   = df["vacuna"].nunique()

    st.markdown('<div class="section-title">Indicadores Globales</div>', unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f'<div class="kpi-card"><div class="kpi-label">Meta Total</div>'
                    f'<div class="kpi-value" style="color:#1d4ed8;">{total_meta:,}</div></div>',
                    unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="kpi-card"><div class="kpi-label">Total Dosis</div>'
                    f'<div class="kpi-value" style="color:#0ea5e9;">{total_dosis:,}</div></div>',
                    unsafe_allow_html=True)
    with c3:
        from data_loader import SEMAFORO_CONFIG, assign_semaforo
        sem = assign_semaforo(cob_gral)
        color = SEMAFORO_CONFIG[sem]["color"]
        st.markdown(f'<div class="kpi-card"><div class="kpi-label">Cobertura Dept.</div>'
                    f'<div class="kpi-value" style="color:{color};">{cob_gral:.1f}%</div></div>',
                    unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="kpi-card"><div class="kpi-label">Vacunas</div>'
                    f'<div class="kpi-value" style="color:#8b5cf6;">{n_vacunas}</div></div>',
                    unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Mapa general (primera vacuna)
    col_map, col_cards = st.columns([1.2, 1])
    with col_map:
        st.markdown('<div class="section-title">Mapa de Cobertura — Vista General</div>',
                    unsafe_allow_html=True)
        first_vaccine = vaccine_summary.sort_values("cobertura_pct").iloc[-1]["vacuna"]
        df_map = df[df["vacuna"] == first_vaccine]
        fig_map = build_choropleth(df_map, first_vaccine, height=420)
        st.plotly_chart(fig_map, use_container_width=True, config={"displayModeBar": False})
        st.caption(f"Mostrando: {first_vaccine}")

    # Tarjetas de vacunas
    with col_cards:
        st.markdown('<div class="section-title">Resumen por Vacuna — Clic para ver detalle</div>',
                    unsafe_allow_html=True)
        cols_per_row = 3
        vacunas_list = vaccine_summary.to_dict("records")
        for row_start in range(0, len(vacunas_list), cols_per_row):
            batch = vacunas_list[row_start: row_start + cols_per_row]
            cols = st.columns(cols_per_row)
            for i, vrow in enumerate(batch):
                with cols[i]:
                    card_html = build_vaccine_card_html(
                        vacuna=vrow["vacuna"],
                        cobertura_pct=vrow["cobertura_pct"],
                        dosis=vrow["dosis"],
                        meta=vrow["meta"],
                        sem_color=vrow["sem_color"],
                        sem_label=vrow["sem_label"],
                        sem_bg=vrow["sem_bg"],
                    )
                    st.markdown(card_html, unsafe_allow_html=True)
                    if st.button("Ver detalle →", key=f"btn_{vrow['vacuna']}",
                                 use_container_width=True):
                        st.session_state.view = "detail"
                        st.session_state.selected_vaccine = vrow["vacuna"]
                        st.rerun()
```

- [ ] **Step 3: Verificar arranque de la app**

```bash
streamlit run app.py
```

Expected: la vista general se muestra con KPIs, mapa y tarjetas de vacunas. Sin errores en consola.

- [ ] **Step 4: Commit parcial**

```bash
git add app.py
git commit -m "feat: vista general con KPIs, mapa y tarjetas de 9 vacunas"
```

---

## Task 7: Vista detalle por vacuna en app.py

**Files:**
- Modify: `app.py` (agregar función `_render_detail_view`)

- [ ] **Step 1: Agregar función _render_detail_view en app.py**

Agregar antes del bloque `if st.session_state.view == "general":`:

```python
def _render_detail_view(df: pd.DataFrame, vacuna: str):
    from data_loader import assign_semaforo, SEMAFORO_CONFIG

    # Botón volver
    if st.button("← Volver al resumen general"):
        st.session_state.view = "general"
        st.session_state.selected_vaccine = None
        st.rerun()

    df_vac = df[df["vacuna"] == vacuna].copy()
    if df_vac.empty:
        st.error(f"No hay datos para la vacuna: {vacuna}")
        return

    # KPIs de esta vacuna
    total_meta  = int(df_vac["meta"].sum())
    total_dosis = int(df_vac["dosis"].sum())
    cob_pct     = round(total_dosis / total_meta * 100, 2) if total_meta > 0 else 0
    sem         = assign_semaforo(cob_pct)
    sem_cfg     = SEMAFORO_CONFIG[sem]

    st.markdown(f'<div class="section-title">Detalle — {vacuna}</div>', unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f'<div class="kpi-card"><div class="kpi-label">Meta</div>'
                    f'<div class="kpi-value" style="color:#1d4ed8;">{total_meta:,}</div></div>',
                    unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="kpi-card"><div class="kpi-label">Dosis Aplicadas</div>'
                    f'<div class="kpi-value" style="color:#0ea5e9;">{total_dosis:,}</div></div>',
                    unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="kpi-card"><div class="kpi-label">Cobertura Dept.</div>'
                    f'<div class="kpi-value" style="color:{sem_cfg["color"]};">{cob_pct:.1f}%</div></div>',
                    unsafe_allow_html=True)
    with c4:
        brecha = total_meta - total_dosis
        st.markdown(f'<div class="kpi-card"><div class="kpi-label">Brecha Pendiente</div>'
                    f'<div class="kpi-value" style="color:#ef4444;">{brecha:,}</div></div>',
                    unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Layout 2 columnas: mapa | análisis
    col_map, col_anl = st.columns([1.2, 1])

    with col_map:
        st.markdown('<div class="section-title">Mapa Coroplético por Provincia</div>',
                    unsafe_allow_html=True)
        fig_map = build_choropleth(df_vac, vacuna, height=450)
        st.plotly_chart(fig_map, use_container_width=True, config={"displayModeBar": False})

    with col_anl:
        # Gauge
        st.markdown('<div class="section-title">Cobertura Departamental</div>',
                    unsafe_allow_html=True)
        fig_gauge = build_gauge(cob_pct, f"Cobertura — {vacuna}")
        st.plotly_chart(fig_gauge, use_container_width=True,
                        config={"displayModeBar": False})

        # Semáforo
        st.markdown('<div class="section-title">Semáforo de Provincias</div>',
                    unsafe_allow_html=True)
        n_verde    = int((df_vac["semaforo"] == "verde").sum())
        n_amarillo = int((df_vac["semaforo"] == "amarillo").sum())
        n_rojo     = int((df_vac["semaforo"] == "rojo").sum())
        st.markdown(build_semaforo_html(n_verde, n_amarillo, n_rojo), unsafe_allow_html=True)

    # Gráfico de barras
    st.markdown('<div class="section-title">Comparativo por Provincia</div>',
                unsafe_allow_html=True)
    fig_bar = build_bar_chart(df_vac, vacuna)
    st.plotly_chart(fig_bar, use_container_width=True, config={"displayModeBar": False})

    # Tabla
    st.markdown('<div class="section-title">Detalle por Provincia</div>',
                unsafe_allow_html=True)
    df_table = df_vac[["provincia", "meta", "dosis", "cobertura_pct", "sem_label"]].copy()
    df_table.columns = ["Provincia", "Meta", "Dosis", "Cobertura %", "Estado"]
    df_table = df_table.sort_values("Cobertura %", ascending=False)
    df_table["Cobertura %"] = df_table["Cobertura %"].map("{:.2f}%".format)

    st.dataframe(
        df_table,
        use_container_width=True,
        hide_index=True,
        height=280,
    )

    # Botón exportar
    st.markdown("---")
    _render_export_buttons(df_vac, vacuna, fig_map, fig_bar, fig_gauge, cob_pct)
```

- [ ] **Step 2: Verificar navegación**

```bash
streamlit run app.py
```

Hacer clic en "Ver detalle →" en una tarjeta. Expected: navegar a vista detalle con mapa, gauge, semáforo, tabla, barras. Botón "← Volver" regresa a vista general.

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "feat: vista detalle por vacuna con mapa, gauge, semaforo, tabla y barras"
```

---

## Task 8: Crear export_utils.py (exportar PNG + PDF)

**Files:**
- Create: `export_utils.py`
- Modify: `app.py` (agregar función `_render_export_buttons`)

- [ ] **Step 1: Crear export_utils.py**

```python
"""
export_utils.py
Exportación de figuras Plotly como PNG y PDF.
"""
import io
import plotly.graph_objects as go
import pandas as pd
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table, TableStyle
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from datetime import datetime


def export_png(fig: go.Figure) -> bytes:
    """Exporta una figura Plotly como bytes PNG."""
    return fig.to_image(format="png", width=1200, height=600, scale=2)


def export_pdf(
    vacuna: str,
    cob_pct: float,
    df_table: pd.DataFrame,
    fig_map_bytes: bytes,
    fig_bar_bytes: bytes,
) -> bytes:
    """
    Genera un PDF ejecutivo del reporte de una vacuna.
    df_table debe tener columnas: Provincia, Meta, Dosis, Cobertura %, Estado
    fig_map_bytes y fig_bar_bytes: imágenes PNG como bytes.
    Retorna bytes del PDF.
    """
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        rightMargin=1.5*cm, leftMargin=1.5*cm,
        topMargin=1.5*cm, bottomMargin=1.5*cm
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "title", parent=styles["Title"],
        fontSize=16, textColor=colors.HexColor("#1e3a5f"),
        spaceAfter=6, alignment=TA_CENTER,
    )
    sub_style = ParagraphStyle(
        "sub", parent=styles["Normal"],
        fontSize=9, textColor=colors.HexColor("#64748b"),
        spaceAfter=4, alignment=TA_CENTER,
    )
    section_style = ParagraphStyle(
        "section", parent=styles["Heading2"],
        fontSize=11, textColor=colors.HexColor("#1d4ed8"),
        spaceBefore=12, spaceAfter=6,
    )
    cell_style = ParagraphStyle(
        "cell", parent=styles["Normal"], fontSize=8,
    )

    elements = []

    # Encabezado
    elements.append(Paragraph(f"Reporte de Coberturas de Vacunación", title_style))
    elements.append(Paragraph(f"Vacuna: {vacuna} — DIRESA Huancavelica 2026", sub_style))
    elements.append(Paragraph(
        f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')} · Cobertura Departamental: {cob_pct:.1f}%",
        sub_style
    ))
    elements.append(Spacer(1, 0.4*cm))

    # Mapa
    elements.append(Paragraph("Mapa de Cobertura por Provincia", section_style))
    map_img = RLImage(io.BytesIO(fig_map_bytes), width=16*cm, height=8*cm)
    elements.append(map_img)
    elements.append(Spacer(1, 0.3*cm))

    # Gráfico barras
    elements.append(Paragraph("Comparativo por Provincia", section_style))
    bar_img = RLImage(io.BytesIO(fig_bar_bytes), width=16*cm, height=6*cm)
    elements.append(bar_img)
    elements.append(Spacer(1, 0.3*cm))

    # Tabla
    elements.append(Paragraph("Detalle por Provincia", section_style))
    table_data = [["Provincia", "Meta", "Dosis", "Cobertura %", "Estado"]]
    for _, row in df_table.iterrows():
        table_data.append([
            Paragraph(str(row["Provincia"]), cell_style),
            Paragraph(f"{int(row['Meta']):,}", cell_style),
            Paragraph(f"{int(row['Dosis']):,}", cell_style),
            Paragraph(str(row["Cobertura %"]), cell_style),
            Paragraph(str(row["Estado"]), cell_style),
        ])

    tbl = Table(table_data, colWidths=[5*cm, 3*cm, 3*cm, 3.5*cm, 3.5*cm])
    tbl.setStyle(TableStyle([
        ("BACKGROUND",  (0,0), (-1,0), colors.HexColor("#1e3a5f")),
        ("TEXTCOLOR",   (0,0), (-1,0), colors.white),
        ("FONTNAME",    (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",    (0,0), (-1,-1), 8),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
        ("GRID",        (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ("ALIGN",       (1,0), (-1,-1), "CENTER"),
        ("VALIGN",      (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING",  (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    elements.append(tbl)

    # Footer
    elements.append(Spacer(1, 0.5*cm))
    elements.append(Paragraph(
        "DIRESA Huancavelica · Estrategia Sanitaria de Inmunizaciones · 2026",
        sub_style
    ))

    doc.build(elements)
    buf.seek(0)
    return buf.getvalue()
```

- [ ] **Step 2: Agregar función _render_export_buttons en app.py**

Agregar esta función antes del bloque `if st.session_state.view == "general":`:

```python
def _render_export_buttons(
    df_vac: pd.DataFrame,
    vacuna: str,
    fig_map: go.Figure,
    fig_bar: go.Figure,
    fig_gauge: go.Figure,
    cob_pct: float,
):
    from export_utils import export_png, export_pdf

    st.markdown('<div class="section-title">Exportar Reporte</div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)

    # PNG del mapa
    with c1:
        png_map = export_png(fig_map)
        st.download_button(
            "📥 Descargar Mapa (PNG)",
            data=png_map,
            file_name=f"mapa_{vacuna.replace(' ','_')}.png",
            mime="image/png",
            use_container_width=True,
        )

    # PNG del gráfico de barras
    with c2:
        png_bar = export_png(fig_bar)
        st.download_button(
            "📥 Descargar Gráfico (PNG)",
            data=png_bar,
            file_name=f"barras_{vacuna.replace(' ','_')}.png",
            mime="image/png",
            use_container_width=True,
        )

    # PDF completo
    with c3:
        df_table_pdf = df_vac[["provincia", "meta", "dosis", "cobertura_pct", "sem_label"]].copy()
        df_table_pdf.columns = ["Provincia", "Meta", "Dosis", "Cobertura %", "Estado"]
        df_table_pdf["Cobertura %"] = df_table_pdf["Cobertura %"].map("{:.2f}%".format)
        pdf_bytes = export_pdf(
            vacuna=vacuna,
            cob_pct=cob_pct,
            df_table=df_table_pdf,
            fig_map_bytes=png_map,
            fig_bar_bytes=png_bar,
        )
        st.download_button(
            "📄 Descargar Reporte PDF",
            data=pdf_bytes,
            file_name=f"reporte_{vacuna.replace(' ','_')}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
```

También agregar el import en la parte superior de app.py:

```python
import plotly.graph_objects as go  # agregar si no está
```

- [ ] **Step 3: Verificar exportación**

```bash
streamlit run app.py
```

Ir a detalle de una vacuna → hacer clic en "Descargar Mapa (PNG)". Expected: descarga un PNG del mapa. Hacer clic en "Descargar Reporte PDF". Expected: descarga un PDF con mapa, gráfico y tabla.

- [ ] **Step 4: Commit**

```bash
git add export_utils.py app.py
git commit -m "feat: exportacion PNG y PDF con kaleido + reportlab"
```

---

## Task 9: Streamlit config + limpieza final

**Files:**
- Create: `.streamlit/config.toml`
- Modify: `app.py` (importar get_pivot si se usa, limpiar imports)

- [ ] **Step 1: Crear .streamlit/config.toml**

```bash
mkdir .streamlit
```

Crear `.streamlit/config.toml`:

```toml
[theme]
primaryColor = "#1d4ed8"
backgroundColor = "#f8fafc"
secondaryBackgroundColor = "#e2e8f0"
textColor = "#1e293b"
font = "sans serif"

[server]
maxUploadSize = 50

[browser]
gatherUsageStats = false
```

- [ ] **Step 2: Agregar .gitignore si no existe**

Crear o actualizar `.gitignore`:

```
__pycache__/
*.pyc
.env
*.egg-info/
dist/
.pytest_cache/
```

- [ ] **Step 3: Verificación final completa**

```bash
streamlit run app.py
```

Verificar:
1. Vista general muestra 9 tarjetas de vacunas con semáforo correcto
2. Mapa coroplético colorea las 7 provincias correctamente
3. Hacer clic en "Ver detalle →" navega al detalle
4. Vista detalle muestra mapa, gauge, semáforo, tabla, gráfico de barras
5. "← Volver" regresa a la vista general
6. Subir un nuevo Excel desde el sidebar actualiza todos los datos
7. Botones de descarga PNG y PDF funcionan
8. Sin errores en consola

- [ ] **Step 4: Ejecutar todos los tests**

```bash
python -m pytest tests/ -v
```

Expected: todos en PASS.

- [ ] **Step 5: Commit final**

```bash
git add .streamlit/ .gitignore
git commit -m "chore: configuracion streamlit theme y gitignore"
git add -A
git commit -m "feat: dashboard vacunacion Huancavelica completo — listo para Streamlit Cloud"
```

---

## Notas de despliegue en Streamlit Cloud

1. Subir el repositorio a GitHub (público o privado)
2. Ir a share.streamlit.io → "New app" → seleccionar el repo
3. Main file: `app.py`
4. Asegurarse de que `data/coberturas.xlsx` esté commiteado en el repo
5. Asegurarse de que `assets/huancavelica.geojson` esté commiteado
6. Sin secrets requeridos (mapbox carto-positron es gratuito sin token)
7. Para actualizar datos: reemplazar `data/coberturas.xlsx` en el repo y hacer push → Streamlit Cloud se actualiza automáticamente
