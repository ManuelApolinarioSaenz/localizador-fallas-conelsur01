# 3. Localización de la falla

[← Índice](../README.md) · Código: `prueba01.py` (`punto_en_distancia`, sección «Ubicación de la falla»), `app.js` (`puntoEnDistancia`, `actualizarFalla`)

## Datos de entrada (panel «Datos del evento» / «Evento»)

| Campo | Descripción |
|---|---|
| Línea de transmisión | Circuito afectado. En escritorio se puede **buscar** por código o subestación. |
| Medir distancia desde | Subestación donde está el relé que reportó la falla. |
| Distancia de falla (km) | Valor del relé. Se limita entre 0 y la longitud de la línea. Por defecto, la mitad de la línea. En escritorio también hay un deslizador. |

## Cálculo

1. **Conversión al origen de la línea.** Internamente toda progresiva se cuenta desde el primer punto del circuito. Si el relé está en el otro extremo:

   ```
   distancia_desde_inicio = longitud_total − distancia_ingresada
   ```

2. **Interpolación sobre el trazado real.** Se buscan los dos puntos consecutivos cuya progresiva encierra la distancia y se interpola linealmente la latitud y longitud entre ellos. En escritorio la búsqueda es binaria.

3. **Torres que encierran la falla.** Solo se consideran puntos con nombre (torres y pórticos; los vértices sin torre no sirven de referencia en campo):
   - Torre anterior: última con progresiva ≤ distancia.
   - Torre posterior: primera con progresiva > distancia.
   - Si coinciden: «Falla exacta en torre Txx»; si no: «Entre torres Txx y Tyy».

> **Limitación.** El cálculo es sobre la proyección horizontal del trazado. No considera la flecha del conductor ni el desnivel, y la distancia del relé tiene su propio error. Es una **estimación** para orientar la búsqueda.

## Salidas

- **Tarjeta «Ubicación estimada»**: km y extremo de medición, coordenadas (5 decimales) y torres.
- **Marcador de falla** en el mapa: ícono de rayo rojo con etiqueta `FALLA · X km`, de tamaño fijo en píxeles.
- **Indicadores (KPI)** sobre el mapa: número de torres (sin contar pórticos), longitud total, tensión nominal y distancia de falla.
- **Encuadre automático**: al cambiar de línea, el mapa se acerca a esa línea.
- **Tooltip de cada torre**: progresiva desde el extremo elegido, que permite contrastar en campo.

Todas las demás capas usan este punto de falla para medir distancias: centros poblados a ≤ 3 km, vía y río más cercanos, clima en el punto, probabilidad de descargas, incendios cercanos.

## Validación

- Si una línea tiene menos de 2 puntos válidos, la app muestra un error y no calcula (revisar ese KMZ).
