# 12. Versión de escritorio (.exe)

[← Índice](../README.md) · Carpeta: `escritorio/`

## Qué es

Un único `LocalizadorFallas.exe` para Windows que **no requiere Python** en la PC del usuario. Se abre como una ventana de aplicación (Edge o Chrome en modo `--app`, sin barras del navegador), igual que el Instructivo de Avisos y OM.

## Estructura

```
escritorio/
├── servidor.py        Lanzador: servidor local + ventana + apagado automático
├── generar_datos.py   Precalcula datos.json desde los KMZ y capas INEI
├── construir.bat      Genera datos.json y empaqueta el .exe (PyInstaller)
├── version_info.txt   Versión y empresa (Propiedades → Detalles del .exe)
├── icono.ico
├── config.json        (no versionado) token de Mapbox
└── web/
    ├── index.html     Interfaz
    ├── app.js         Lógica de la app (mapa, capas, cálculos)
    ├── reporte.js     Reporte PDF
    ├── estilo.css
    ├── logo.png
    ├── datos.json     (generado, no versionado)
    └── lib/           MapLibre GL y jsPDF (sin dependencia de CDN)
```

## `datos.json` (generado por `generar_datos.py`)

Precalcula todo lo que la versión web calcula en cada interacción:

| Clave | Contenido |
|---|---|
| `generado` | Fecha y hora de generación (se muestra en el pie de página) |
| `circuitos` | `[{n, kv, tipo, se:[inicio, fin], partes:[índices], pts:[[lon, lat, progresiva_m, torre], …]}]` |
| `partes` | Trazos de dibujo, uno por archivo KMZ: `{kv, s (1 = subterráneo), c:[[lon, lat], …]}` |
| `subestaciones` | `{n, kv, lon, lat, pol:[[lon, lat], …]}` |
| `centros_poblados` | `[nombre, distrito, provincia, departamento, lon, lat]` |
| `vias`, `rios` | Copia de las capas INEI |

Si existe un `datos.json` **junto al `.exe`**, se usa ese en lugar del empaquetado. Así se pueden actualizar los datos sin recompilar.

## `servidor.py` — lanzador

1. Si la app ya está abierta (responde la firma en `/api/ping`), solo abre otra ventana.
2. Evita doble arranque con un mutex de Windows.
3. Busca un puerto libre desde **8765** (hasta +30) y sirve `web/` solo en `127.0.0.1`.
4. Abre la ventana con Edge o Chrome (`--app`) ajustada al área útil de la pantalla y a la escala DPI. Si no los encuentra, usa el navegador predeterminado.
5. **Apagado automático**: la página envía un latido cada 5 s. El servidor se apaga si:
   - no recibe latidos durante 75 s,
   - la ventana avisa que se cerró (`/api/adios`) y pasan 6 s sin que se recargue, o
   - la ventana nunca llegó a conectarse en 180 s.

### Rutas del servidor local

| Ruta | Función |
|---|---|
| `GET /api/ping` | Firma de la app y latido |
| `GET /api/config` | Token de Mapbox (`config.json` junto al `.exe` o empaquetado) |
| `GET /api/bomberos` | Proxy con caché de 60 s de la hoja de Bomberos |
| `POST /api/adios` | La ventana se cerró o se recargó |
| `GET /datos.json` | Datos (externo junto al `.exe` si existe) |

### Variables de entorno (opcionales)

| Variable | Por defecto | Uso |
|---|---|---|
| `LOCALIZADOR_PUERTO` | 8765 | Puerto inicial |
| `LOCALIZADOR_CIERRE_S` | 75 | Segundos sin latido antes de apagar |
| `LOCALIZADOR_SIN_NAVEGADOR` | — | Si está definida, no abre ventana (pruebas) |

Los errores se muestran en un cuadro de mensaje y se registran en `%LOCALAPPDATA%\LocalizadorFallas\registro.log`.

## Compilación

Requisitos solo en la PC que compila: Python con `streamlit pandas numpy pyinstaller`.

1. (Opcional) Crear `escritorio\config.json` con `{"mapbox_token": "pk...."}`. Sin él, el `.exe` usa CARTO y Esri.
2. Ejecutar `escritorio\construir.bat`. Para indicar otro Python: `set PYTHON=C:\ruta\python.exe` antes.
3. Resultado: `escritorio\dist\LocalizadorFallas.exe`.

El `.bat` hace dos pasos: `generar_datos.py`, y luego PyInstaller con `--onefile --noconsole`, incluyendo `web/` y `config.json` y excluyendo numpy, pandas y streamlit para reducir el tamaño.

Para cambiar la versión, editar `filevers`, `prodvers`, `FileVersion` y `ProductVersion` en `version_info.txt`.
