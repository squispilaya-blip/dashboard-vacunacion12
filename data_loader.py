"""
data_loader.py
Carga y normaliza el Excel de coberturas por provincia DIRESA Huancavelica.
Excel: 9 hojas (una por vacuna), columnas: RIS/provincia, META, dosis, %
Umbrales semáforo: >=33.2% Logrado, 26.4-33.1% En Proceso, <=26.3% Crítico
"""
import pandas as pd
from pathlib import Path
from typing import Union
import io

DEFAULT_EXCEL = Path("data/coberturas.xlsx")

THRESHOLDS = {"verde": 33.2, "amarillo": 26.4}

SEMAFORO_CONFIG = {
    "verde":    {"label": "Logrado",    "color": "#22c55e", "bg": "#f0fdf4", "dark": "#15803d"},
    "amarillo": {"label": "En Proceso", "color": "#f59e0b", "bg": "#fffbeb", "dark": "#b45309"},
    "rojo":     {"label": "Crítico",    "color": "#ef4444", "bg": "#fef2f2", "dark": "#b91c1c"},
}

PROVINCIAS_VALIDAS = {
    "HUANCAVELICA", "ACOBAMBA", "TAYACAJA",
    "ANGARAES", "CASTROVIRREYNA", "CHURCAMPA",
    "HUAYTARA", "HUAYTARÁ",
}

SKIP_WORDS = {"RIS", "TOTAL", "DIRESA", "PROVINCIA", "REGION", "REGIÓN",
              "DEPARTAMENTO", "NONE", "NAN", ""}


def normalize_pct(val) -> float:
    """0.282 → 28.2; valores >= 2 ya son porcentaje."""
    try:
        f = float(str(val).replace(",", ".").strip())
        return round(f * 100, 2) if 0 < f < 2 else round(f, 2)
    except (ValueError, TypeError):
        return 0.0


def normalize_province(name: str) -> str:
    return (
        str(name).strip().upper()
        .replace("Á", "A").replace("É", "E").replace("Í", "I")
        .replace("Ó", "O").replace("Ú", "U").replace("Ü", "U")
        .replace("á", "A").replace("é", "E").replace("í", "I")
        .replace("ó", "O").replace("ú", "U")
    )


def assign_semaforo(pct: float) -> str:
    if pct >= THRESHOLDS["verde"]:
        return "verde"
    if pct >= THRESHOLDS["amarillo"]:
        return "amarillo"
    return "rojo"


def _parse_sheet(sheet_name: str, df_raw: pd.DataFrame) -> list:
    records = []
    for _, row in df_raw.iterrows():
        raw = str(row.iloc[0]).strip() if pd.notna(row.iloc[0]) else ""
        prov = normalize_province(raw)
        if prov in SKIP_WORDS:
            continue
        # Aceptar tanto provincias conocidas como cualquier texto que no sea skip
        if len(prov) < 3:
            continue
        try:
            meta_val  = row.iloc[1] if len(row) > 1 and pd.notna(row.iloc[1]) else 0
            dosis_val = row.iloc[2] if len(row) > 2 and pd.notna(row.iloc[2]) else 0
            pct_val   = row.iloc[3] if len(row) > 3 and pd.notna(row.iloc[3]) else None

            meta  = int(float(str(meta_val).replace(",", "")))
            dosis = int(float(str(dosis_val).replace(",", "")))

            if pct_val is not None:
                pct = normalize_pct(pct_val)
            else:
                pct = round(dosis / meta * 100, 2) if meta > 0 else 0.0
        except (ValueError, IndexError, ZeroDivisionError):
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
    Carga Excel de coberturas.
    source: ruta, bytes (upload Streamlit), o None (usa DEFAULT_EXCEL).
    Retorna DataFrame con columnas: vacuna, provincia, meta, dosis,
    cobertura_pct, semaforo, sem_label, sem_color, sem_bg, sem_dark
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
            parsed = _parse_sheet(sheet, df_raw)
            records.extend(parsed)
        except Exception:
            continue

    return pd.DataFrame(records) if records else pd.DataFrame()


def get_vaccine_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Resumen por vacuna: meta total, dosis total, cobertura %."""
    agg = df.groupby("vacuna", sort=False).agg(
        meta=("meta", "sum"),
        dosis=("dosis", "sum"),
    ).reset_index()
    agg["cobertura_pct"] = (agg["dosis"] / agg["meta"] * 100).round(2).fillna(0)
    agg["semaforo"]  = agg["cobertura_pct"].apply(assign_semaforo)
    agg["sem_label"] = agg["semaforo"].map(lambda s: SEMAFORO_CONFIG[s]["label"])
    agg["sem_color"] = agg["semaforo"].map(lambda s: SEMAFORO_CONFIG[s]["color"])
    agg["sem_bg"]    = agg["semaforo"].map(lambda s: SEMAFORO_CONFIG[s]["bg"])
    agg["sem_dark"]  = agg["semaforo"].map(lambda s: SEMAFORO_CONFIG[s]["dark"])
    return agg


def get_pivot(df: pd.DataFrame) -> pd.DataFrame:
    """Pivote: filas=provincia, columnas=vacuna, valores=cobertura_pct."""
    return df.pivot_table(
        index="provincia", columns="vacuna",
        values="cobertura_pct", aggfunc="first"
    ).reset_index()
