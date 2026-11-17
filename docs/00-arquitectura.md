# 0. Arquitectura y flujo general

[← Índice](../README.md)

## Idea central

Todo gira alrededor de **una línea seleccionada** y **un punto de falla** sobre ella. Cada módulo de capa (lluvias, pueblos, ríos, vías, incendios…) se filtra a la zona de esa línea y mide su distancia a la línea y/o al punto de falla.

```
            ┌──────────────────────────┐
 kmz/*.kmz ─►  cargar_kmz.py            │  torres, trazados, subestaciones, kV, tipo
            └────────────┬─────────────┘
                         ▼
            ┌──────────────────────────┐
            │  circuitos.py            │  circuitos completos + progresiva (m)
            └────────────┬─────────────┘    + pórticos de SE en los extremos
                         ▼
     Usuario: línea + extremo (SE del relé) + distancia de falla (km)
                         ▼
            ┌──────────────────────────┐
            │  Localización de falla   │  lat/lon, torres anterior y posterior
            └────────────┬─────────────┘
                         ▼
  ┌──────────┬───────────┼───────────┬───────────┬───────────┐
  ▼          ▼           ▼           ▼           ▼           ▼
 Subest.   Lluvias/   Descargas   Centros     Ríos y      Vías e
 (KMZ)     clima      atmosf.     poblados    acequias    incendios
           (Open-Meteo)(Open-Meteo)(INEI)     (INEI)      (INEI / Bomberos)
                         ▼
               Mapa + panel + reporte PDF
```

## Componentes

| Archivo | Rol |
|---|---|
| `cargar_kmz.py` | Lee los `.kmz` de `kmz/`: clasifica cada archivo como línea o subestación por su nombre, extrae torres, trazados (`LineString`), polígonos de patio, voltaje y tipo (aérea/subterránea). |
| `circuitos.py` | Une los archivos que forman un mismo circuito, arma una ruta continua, agrega el vano hasta el pórtico de la SE y calcula la **progresiva** (distancia acumulada) de cada punto. También mide la distancia de puntos externos a la línea. |
| `prueba01.py` | Aplicación web Streamlit: interfaz, consultas en línea (clima, Bomberos) y dibujo del mapa con PyDeck. |
| `escritorio/generar_datos.py` | Ejecuta `cargar_kmz` + `circuitos` una sola vez y guarda todo en `escritorio/web/datos.json`. |
| `escritorio/web/app.js` | Aplicación de escritorio (MapLibre): misma lógica que `prueba01.py`, en JavaScript, más el módulo de descargas atmosféricas. |
| `escritorio/web/reporte.js` | Generación del reporte PDF (jsPDF). |
| `escritorio/servidor.py` | Lanzador del `.exe`: servidor local, proxy de Bomberos, abre la ventana y se apaga al cerrarla. |

## Archivos de datos

| Archivo | Contenido | Usado por |
|---|---|---|
| `kmz/*.kmz` (200 archivos: 119 líneas, 81 subestaciones) | Trazado, torres y patios reales | Ambas versiones (fuente principal) |
| `consolidado_total.xlsx` | Torres por línea (columnas `Linea`, `Torre`, `Latitud`, `Longitud`) | Solo respaldo de la versión web si `kmz/` está vacío |
| `centros_poblados_rurales.csv` (1 855 filas) | Centros poblados rurales a ≤ 5 km de alguna línea | Módulo de centros poblados |
| `rios_acequias_inei.json` (3 012 elementos) | Ríos y acequias en una franja de ~5 km | Módulo de ríos y acequias |
| `vias_inei.json` (10 537 elementos) | Vías asfaltadas, afirmadas, carrozables y de herradura | Módulo de red vial |
| `analisis_centros_poblados_lineas.csv` | Análisis completo (rurales y urbanos) de distancia de cada centro poblado a la línea más cercana, con km y torre | Referencia, no lo lee la app |
| `restricciones_conelsur.csv` | Obstáculos y restricciones por tramo (poblados, carreteras, cultivos…) por código de línea | Referencia, no lo lee la app |
| `conelsur_logo*.{png,jpg}` | Logo del encabezado | Interfaz |

Formato de las capas INEI (`rios_acequias_inei.json`, `vias_inei.json`): lista de objetos `{"t": tipo, "n": nombre, "p": [[lon, lat], ...]}`.

## Servicios externos (requieren internet)

| Servicio | Para qué | Clave |
|---|---|---|
| Open-Meteo (`api.open-meteo.com`) | Lluvia, código de tiempo, viento, índices de inestabilidad | No |
| Hoja de Google Sheets de emergencias de Bomberos | Incendios activos | No |
| Mapbox | Mapa base calle y satélite | Token (opcional) |
| Esri World Imagery / CARTO | Mapa base alternativo sin token | No |

Sin internet, la localización de la falla y las capas INEI siguen funcionando; solo fallan clima, descargas, incendios y el mapa base.
