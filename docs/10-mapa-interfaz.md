# 10. Mapa base, leyenda e interfaz

[← Índice](../README.md) · Código: `prueba01.py` (secciones 0–2 y 6), `app.js` (`fuenteBase`, `crearCapas`, `actualizarLeyenda`), `estilo.css`, `.streamlit/config.toml`

## Distribución de la pantalla

```
┌─────────────────────────────────────────────────────────────────┐
│ Logo · Título · [Calle | Satélite] · Modo oscuro · [Reporte PDF]│
├──────────────────┬──────────────────────────────────────────────┤
│ Panel            │  KPI: Torres · Longitud · Tensión · Falla    │
│ - Evento         │ ┌──────────────────────────────────────────┐ │
│ - Ubicación      │ │                                          │ │
│ - Cercanos       │ │                 MAPA                     │ │
│ - Capas          │ │                               [Leyenda]  │ │
│                  │ └──────────────────────────────────────────┘ │
└──────────────────┴──────────────────────────────────────────────┘
```

El botón de reporte PDF existe solo en la versión de escritorio.

## Mapa base

| Vista | Con token de Mapbox | Sin token |
|---|---|---|
| Calle | Mapbox `streets-v12` (`dark-v11` en modo oscuro, escritorio) | Escritorio: CARTO claro/oscuro. Web: no carga, aviso en pantalla |
| Satélite | Mapbox `satellite-streets-v12` (imagen + nombres) | Esri World Imagery |

**Dónde se configura el token:**

- Web: secreto de Streamlit `[mapbox] token = "pk…"` (Settings → Secrets en Streamlit Cloud o `.streamlit/secrets.toml`). Nunca en el código.
- Escritorio: `escritorio/config.json` → `{"mapbox_token": "pk…"}` (no se sube a GitHub). También puede ponerse un `config.json` junto al `.exe`.

Detalle técnico (web): el componente de mapas de Streamlit usa mapbox-gl 1.13, que no carga bien los estilos v12 en satélite. Por eso la vista satélite pide las teselas ya renderizadas y las dibuja como capa raster plana (`TerrainLayer` con elevación cero).

## Modo oscuro

Interruptor en el encabezado. Cambia fondos, textos, tarjetas y bordes. Los colores de marca (azul `#0B3088`, verde `#00A651`) se mantienen. En escritorio, también cambia el mapa de calle a oscuro, y la carretera asfaltada pasa de negro a gris claro para que se vea.

## Indicadores (KPI)

| Indicador | Origen |
|---|---|
| Torres | Puntos con nombre de la línea, sin contar pórticos |
| Longitud | Progresiva del último punto (km) |
| Tensión nominal | kV del nombre del archivo KMZ |
| Distancia de falla | Valor ingresado (km) |

## Leyenda

Flotante en la esquina del mapa y **dinámica**: siempre muestra los niveles de tensión, la línea seleccionada y el tramo subterráneo. Cada capa (vías, ríos, centros poblados, incendios, clima, descargas) agrega su sección solo cuando está activa.

## Ventanas emergentes (tooltip)

Al pasar el mouse por líneas, torres, polígonos de SE, centros poblados, vías, ríos o incendios se muestra su nombre y su detalle (kV, progresiva, distancia, estado…).

## Identidad visual

- Tipografías: **Poppins** (títulos, valores) e **Inter** (texto).
- Tema base de Streamlit en `.streamlit/config.toml` (verde primario, fondo gris claro).
- Pie de página: «CONELSUR — Centro de Control de Operaciones de Transmisión». En escritorio también muestra la fecha de generación de los datos.
