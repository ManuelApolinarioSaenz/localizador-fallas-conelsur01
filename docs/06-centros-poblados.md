# 6. Centros poblados (pueblos)

[← Índice](../README.md) · Código: `prueba01.py` (sección «Centros poblados rurales»), `circuitos.py` (`distancia_puntos_a_linea`), `app.js` (`calcularCP`, `dibujarCP`, `actualizarTablaCP`) · Capa: «Centros poblados rurales»

## Qué hace

Muestra los **centros poblados rurales** cercanos a la línea seleccionada y lista los que están a menos de 3 km del punto de falla. Sirve para:

- Coordinar con la población el acceso a la zona.
- Identificar riesgo para terceros (pueblos bajo o junto a la línea).
- Dar referencias de ubicación a la cuadrilla («la falla está a 800 m del caserío X»).

## Fuente

`centros_poblados_rurales.csv` — **INEI, SIGE Atlas**. Contiene solo los 1 855 centros poblados rurales que están a ≤ 5 km de alguna línea (prefiltrado fuera de la app).

Columnas: `departamento, provincia, distrito, ubigeo, centro_poblado, lat, lon`.

El archivo `analisis_centros_poblados_lineas.csv` contiene el análisis completo (rurales y urbanos, con línea más cercana, kV, km y torre). Es de referencia y la app no lo usa.

## Cálculo

1. **Prefiltro por recuadro**: se descartan los centros poblados fuera del rectángulo de la línea más un margen.
2. **Distancia al eje**: distancia perpendicular mínima de cada pueblo al trazado (aproximación plana local, suficiente para pocos km).
3. **Progresiva**: km de la línea frente al pueblo, contado desde el extremo elegido.
4. **Filtro por radio** seleccionado por el usuario: 100 m, 300 m, 500 m, **1 km** (por defecto), 2 km o 5 km.
5. **Distancia al punto de falla** (Haversine) para la tabla de cercanía.

## En el mapa

Puntos coloreados según la distancia al eje:

| Distancia al eje | Color | Lectura |
|---|---|---|
| ≤ 100 m | Rojo | Prácticamente bajo la línea |
| 100–300 m | Naranja | Muy cerca |
| > 300 m | Amarillo | En el entorno |

Tooltip: nombre, distrito, provincia, distancia al eje y km de la línea.

## En el panel

- Conteo: «N centros poblados rurales a ≤ X de la línea».
- **Tabla «Centros poblados cerca de la falla»** (hasta 3 km): centro poblado, distrito, distancia a la falla (km) y al eje (m), ordenada del más cercano al más lejano.

## Uso en el reporte PDF

- Tabla de centros poblados a ≤ 3 km de la falla.
- Conteo por bandas: ≤ 100 m, 100–300 m, 300 m–1 km, 1–5 km del eje.
- Alerta **media** si hay un pueblo a ≤ 300 m de la falla («coordinar con la población»); informativa con el más cercano si no.
