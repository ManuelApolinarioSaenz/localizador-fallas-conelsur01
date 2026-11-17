# Localizador de Fallas Georreferenciado — CONELSUR

Herramienta del Centro de Control para **ubicar en el mapa el punto de falla** de una línea de transmisión a partir de la distancia que reporta el relé de protección. Alrededor de ese punto muestra el **contexto de campo** que necesita la cuadrilla: subestaciones, lluvias y tormentas, probabilidad de descargas atmosféricas, centros poblados, ríos y acequias, red vial e incendios activos.

> **Pregunta que responde:** «El relé de la SE X marca una falla a *N* km. ¿Dónde está exactamente, entre qué torres, cómo llego y qué riesgos hay en la zona?»

---

## Dos versiones de la misma herramienta

| | Versión web (Streamlit) | Versión de escritorio (.exe) |
|---|---|---|
| Archivo principal | `prueba01.py` | `escritorio/servidor.py` + `escritorio/web/` |
| Cálculo | Python, en el servidor, en cada interacción | JavaScript, en el navegador, con datos precalculados (`datos.json`) |
| Mapa | PyDeck (deck.gl) | MapLibre GL |
| Requiere Python en la PC del usuario | Sí (o Streamlit Cloud) | No, es un único `.exe` |
| Probabilidad de descargas atmosféricas | No | **Sí** |
| Búsqueda de líneas por texto | No | **Sí** |
| Reporte PDF | No | **Sí** |

Las dos comparten la misma lógica de datos: `cargar_kmz.py` (lectura de KMZ) y `circuitos.py` (armado de circuitos y progresivas).

---

## Documentación por módulo

| # | Módulo | Qué explica |
|---|---|---|
| 0 | [Arquitectura y flujo general](docs/00-arquitectura.md) | Componentes, flujo de datos y archivos del repositorio |
| 1 | [Líneas de transmisión y circuitos](docs/01-lineas-y-circuitos.md) | Lectura de KMZ, torres, trazado, circuitos dobles, progresivas |
| 2 | [Subestaciones](docs/02-subestaciones.md) | Patios (polígonos), pórticos y extremos de cada línea |
| 3 | [Localización de la falla](docs/03-localizacion-falla.md) | Cálculo del punto de falla, torres adyacentes, indicadores |
| 4 | [Lluvias y clima](docs/04-lluvias-clima.md) | Lluvia actual, acumulado de 24 h, tormentas a lo largo de la línea |
| 5 | [Probabilidad de descargas atmosféricas](docs/05-descargas-atmosfericas.md) | Índice de rayos (CAPE, LI, CIN…) y mapa de calor por hora |
| 6 | [Centros poblados (pueblos)](docs/06-centros-poblados.md) | Pueblos rurales cercanos a la línea y al punto de falla |
| 7 | [Ríos y acequias](docs/07-rios-acequias.md) | Hidrografía INEI y el río más cercano a la falla |
| 8 | [Red vial (carreteras y caminos)](docs/08-red-vial.md) | Vías INEI por tipo y acceso vehicular más cercano |
| 9 | [Incendios activos](docs/09-incendios.md) | Emergencias de Bomberos Perú y alertas por cercanía |
| 10 | [Mapa base, leyenda e interfaz](docs/10-mapa-interfaz.md) | Vista calle/satélite, modo oscuro, KPIs, leyenda |
| 11 | [Reporte PDF](docs/11-reporte-pdf.md) | Contenido del reporte y cómo se genera |
| 12 | [Versión de escritorio (.exe)](docs/12-version-escritorio.md) | Servidor local, `datos.json`, compilación |
| 13 | [Instalación, ejecución y mantenimiento](docs/13-instalacion-mantenimiento.md) | Cómo correrlo, agregar KMZ, actualizar datos, problemas comunes |

---

## Inicio rápido

**Versión web (Streamlit):**

```bash
pip install -r requirements.txt
```

```bash
streamlit run prueba01.py
```

Token de Mapbox (opcional) en `.streamlit/secrets.toml`:

```toml
[mapbox]
token = "pk...."
```

**Versión de escritorio:** en Windows, ejecutar `escritorio\construir.bat` y distribuir `escritorio\dist\LocalizadorFallas.exe`. Detalle en [docs/12-version-escritorio.md](docs/12-version-escritorio.md).
