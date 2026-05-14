# Dashboard Coberturas de Vacunación DIRESA Huancavelica — Spec

**Fecha:** 2026-05-13  
**Proyecto:** Dashboard Streamlit ejecutivo de coberturas de vacunación por provincias  
**Región:** Huancavelica — 7 provincias  
**Fuente de datos:** Excel con 9 hojas (una por vacuna)

---

## 1. Objetivo

Crear una aplicación Streamlit ejecutiva que:
- Cargue automáticamente el Excel de coberturas por defecto (`data/coberturas.xlsx`)
- Permita subir un nuevo Excel para actualizar todos los datos en sesión
- Muestre un resumen general de las 9 vacunas y un detalle interactivo por vacuna
- Visualice un mapa coroplético real de Huancavelica coloreado por % de cobertura
- Permita exportar el dashboard como PDF/imagen

---

## 2. Arquitectura

### Estructura de archivos

```
dashboard-vacunacion/
├── app.py                        # UI principal Streamlit
├── data_loader.py                # Lectura y normalización del Excel
├── charts.py                     # Gráficos Plotly (gauge, barras, semáforo)
├── map_utils.py                  # Mapa coroplético GeoJSON + Plotly
├── data/
│   └── coberturas.xlsx           # Excel por defecto
├── assets/
│   └── huancavelica.geojson      # GeoJSON oficial provincias Huancavelica
├── requirements.txt
└── .streamlit/
    └── config.toml               # Tema visual, colores DIRESA
```

### Módulos

| Módulo | Responsabilidad |
|--------|----------------|
| `data_loader.py` | Lee cada hoja del Excel, normaliza % (0.282 → 28.2%), retorna DataFrame unificado |
| `map_utils.py` | Carga GeoJSON, une con DataFrame, genera figura Plotly choropleth |
| `charts.py` | Gauge SVG/Plotly, gráfico barras 3D, tarjetas semáforo |
| `app.py` | Layout Streamlit, sidebar, navegación entre vistas, exportación |

### DataFrame unificado (salida de `data_loader.py`)

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `vacuna` | str | Nombre de la hoja/vacuna |
| `provincia` | str | Nombre provincia (normalizado en mayúsculas) |
| `meta` | int | Meta padrón nominal 2024 |
| `dosis` | int | Dosis aplicadas |
| `cobertura_pct` | float | Porcentaje cobertura (0–100) |
| `semaforo` | str | "verde" / "amarillo" / "rojo" |

---

## 3. Semáforo (umbrales fijos)

| Rango | Color | Etiqueta |
|-------|-------|----------|
| ≥ 33.2% | 🟢 Verde | Logrado |
| 26.4% – 33.1% | 🟡 Amarillo | En Proceso |
| ≤ 26.3% | 🔴 Rojo | Crítico |

---

## 4. Flujo de usuario

### Pantalla 1 — Vista General
- Header ejecutivo: logo DIRESA, título, fecha actualización, dot animado "EN VIVO"
- Sidebar: uploader de Excel, filtro de provincia (opcional)
- Cuerpo: 9 tarjetas de vacunas (nombre, % promedio departamental, badge semáforo)
- Mapa coroplético de Huancavelica (coloreado por vacuna con mayor cobertura o la primera)
- KPIs globales: total meta, total dosis, cobertura departamental promedio

### Pantalla 2 — Detalle de vacuna (clic en tarjeta)
- Botón "← Volver"
- Layout 2 columnas:
  - Izquierda: mapa coroplético con % de cobertura por provincia + tooltip (nombre, %, dosis, meta)
  - Derecha: KPIs (meta, dosis, cobertura dept.), gauge, semáforo por provincia, tabla detalle, gráfico barras Plotly
- Footer: botón exportar PDF / PNG

---

## 5. Mapa

- Fuente GeoJSON: datos oficiales de provincias del Perú filtrados para Huancavelica (INEI / OpenStreetMap)
- Librería: `plotly.express.choropleth_mapbox` o `plotly.graph_objects.Choroplethmapbox`
- Mapbox style: `carto-positron` (sin token requerido)
- Color scale personalizada: rojo (#ef4444) → amarillo (#f59e0b) → verde (#22c55e)
- Tooltip al hover: Provincia, Cobertura %, Dosis, Meta, Estado semáforo

---

## 6. Persistencia de datos

- El Excel por defecto vive en `data/coberturas.xlsx` (commiteado al repositorio)
- El uploader en sidebar reemplaza los datos **solo en sesión** (st.session_state)
- Al refrescar la app, vuelve al Excel del repositorio
- Para actualización permanente: subir nuevo Excel al repositorio (reemplazar `data/coberturas.xlsx`)

---

## 7. Exportación

- Librería: `kaleido` para exportar figuras Plotly como PNG
- PDF: `reportlab` o captura HTML con `pdfkit`
- Botón de descarga con `st.download_button`
- Exporta: mapa + KPIs + tabla + gráfico en un solo PDF o imagen PNG

---

## 8. Dependencias (requirements.txt)

```
streamlit>=1.32.0
pandas>=2.0.0
openpyxl>=3.1.0
plotly>=5.18.0
kaleido>=0.2.1
reportlab>=4.0.0
requests>=2.31.0
```

---

## 9. Despliegue Streamlit Cloud

- Repositorio GitHub público o privado con acceso a Streamlit Cloud
- `data/coberturas.xlsx` commiteado como datos por defecto
- `assets/huancavelica.geojson` commiteado
- Sin secrets requeridos (mapbox carto-positron es gratuito sin token)
