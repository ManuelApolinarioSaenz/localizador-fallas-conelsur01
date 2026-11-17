# 7. Ríos y acequias

[← Índice](../README.md) · Código: `prueba01.py` (`cargar_capa_inei`, `elementos_en_caja`, `_mas_cercano`), `app.js` (`dibujarHidro`, `actualizarCercanos`) · Capa: «Ríos y acequias»

## Qué hace

Dibuja la red hidrográfica alrededor de la línea y calcula el **río y la acequia más cercanos al punto de falla**. Ayuda a prever cruces de río, crecidas en temporada de lluvias y zonas húmedas o inestables.

## Fuente

`rios_acequias_inei.json` — **INEI, SIGE Atlas**, vectorizado en una franja de ~5 km alrededor de las líneas (3 012 elementos).

Formato: `{"t": "Río" | "Acequia", "n": "<nombre o vacío>", "p": [[lon, lat], ...]}`.

## Cálculo

1. Al cargar, se calcula el **recuadro** (mín/máx de lon y lat) de cada elemento.
2. Al seleccionar una línea, se toman solo los elementos cuyo recuadro cruza el de la línea ampliado **0.05° (~5 km)**.
3. Para el punto de falla, se calcula la distancia mínima a cada polilínea (proyección sobre cada segmento) y se reporta el más cercano de cada tipo si está a **≤ 5 km**.

## En el mapa y el panel

| Tipo | Color | Grosor |
|---|---|---|
| Río | Celeste `#29B6F6` | 3 px |
| Acequia | Turquesa claro `#80DEEA` | 2 px |

Tooltip con el nombre del río (si el INEI lo registra).

Tarjeta **«Más cercano al punto de falla» / «Accesos e hidrografía cercanos»**: p. ej. «Río (Río Rímac): 420 m», «Acequia: 1.35 km». Se muestra junto con las vías si ambas capas están activas.

## Uso en el reporte PDF

- Fila de río y acequia más cercanos en la tabla «Accesos e hidrografía».
- Alerta **media** si un río está a menos de **300 m** del punto de falla: «posible cruce o crecida».

## Precisión

Datos INEI con precisión aproximada de 5 a 10 m. Algunos cauces pueden no estar actualizados.
