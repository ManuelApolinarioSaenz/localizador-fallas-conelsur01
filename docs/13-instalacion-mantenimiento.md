# 13. Instalación, ejecución y mantenimiento

[← Índice](../README.md)

## Ejecutar la versión web

Requisitos: Python 3.11 o superior.

```bash
pip install -r requirements.txt
```

```bash
streamlit run prueba01.py
```

Se abre en `http://localhost:8501`. En GitHub Codespaces, el `.devcontainer` instala dependencias y arranca la app automáticamente.

Token de Mapbox (opcional): crear `.streamlit/secrets.toml` (no subirlo al repositorio):

```toml
[mapbox]
token = "pk...."
```

En Streamlit Cloud: *Settings → Secrets* con el mismo contenido.

## Ejecutar la versión de escritorio

- **Usuario final**: doble clic en `LocalizadorFallas.exe`. No requiere instalación.
- **Desarrollo**: generar los datos y lanzar el servidor directamente:

```bash
python escritorio/generar_datos.py
```

```bash
python escritorio/servidor.py
```

## Tareas de mantenimiento

### Agregar o actualizar una línea o subestación

1. Copiar el `.kmz` en `kmz/` respetando la [convención de nombres](01-lineas-y-circuitos.md#convención-de-nombres-de-archivo).
2. Web: reiniciar la app o esperar 1 h (caché de lectura de KMZ).
3. Escritorio: volver a ejecutar `construir.bat`, o solo `generar_datos.py` y copiar `escritorio/web/datos.json` junto al `.exe`.
4. Verificar en la app: que aparezca en el selector, que su longitud sea razonable y que los extremos muestren el nombre de la SE.

Revisar al agregar un KMZ:

- Que el prefijo de kV sea correcto (define el color y la preferencia de SE).
- Que los circuitos dobles usen `L-XXXX-YYYY` para el tramo compartido y `L-XXXX` para el propio.
- Que el archivo de la SE de cada extremo exista. Si no, la distancia empieza en la primera torre y no en el pórtico.
- Que no contenga `ZZZ` en el nombre si debe cargarse (esos se ignoran).

### Actualizar las capas INEI

Los archivos `centros_poblados_rurales.csv`, `rios_acequias_inei.json` y `vias_inei.json` se generan fuera de la app (recorte de SIGE Atlas a ~5 km de las líneas). Si se agregan líneas en zonas nuevas, hay que **regenerarlos** para que cubran esa zona; si no, las capas aparecerán vacías alrededor de la nueva línea.

### Cambiar parámetros

| Qué | Dónde |
|---|---|
| Colores por tensión | `COLORES_POR_VOLTAJE` (`cargar_kmz.py`) y `COLORES_KV` (`app.js`) |
| Radios de búsqueda de SE | `RADIO_BUSQUEDA_SE_M`, `RADIO_SE_SIN_NOMBRE_M` (`circuitos.py`) |
| Tolerancias de unión de tramos | Constantes al inicio de `circuitos.py` |
| Umbrales de incendios (100 m / 500 m) | `prueba01.py` y `dibujarIncendios` en `app.js` |
| Grilla y fórmula de descargas | `RAYOS_*`, `indiceRayo` en `app.js` |
| Reglas de alertas del PDF | `datosReporte` en `reporte.js` |

Si un parámetro existe en las dos versiones, cambiarlo en **ambas** para mantenerlas coherentes.

## Problemas comunes

| Síntoma | Causa probable | Solución |
|---|---|---|
| Aviso «No se pudieron leer estos archivos KMZ» | KMZ sin `.kml`, sin geometría o XML dañado | Abrirlo en Google Earth y volver a exportarlo |
| La línea dibuja un salto recto o un «abanico» | Tramos que no empalman o coordenadas inválidas | Revisar el trazado del KMZ; verificar si hay un archivo `ZZZ` o tramos sueltos |
| Longitud de la línea menor a la real | Falta el archivo propio o compartido del circuito | Verificar que todos los archivos del circuito usen el mismo código |
| Extremo «Inicio de la línea (T01)» en vez del nombre de la SE | No hay KMZ de esa SE o está a más de 500 m | Agregar el KMZ de la SE o revisar su nombre |
| Mapa de calle en blanco (web) | Falta el token de Mapbox | Configurar el secreto `[mapbox]` |
| Satélite en negro o con errores 429 | Límite de teselas de Mapbox | Acercar el mapa; sin token se usa Esri |
| Clima, descargas o incendios «sin conexión» | Sin internet o servicio caído | Reintentar; el resto de la app sigue funcionando |
| El `.exe` no abre | Puerto ocupado u otro error | Ver `%LOCALAPPDATA%\LocalizadorFallas\registro.log` |
