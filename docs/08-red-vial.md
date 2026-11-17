# 8. Red vial (carreteras y caminos)

[← Índice](../README.md) · Código: `prueba01.py` (sección «Ríos y acequias / red vial»), `app.js` (`dibujarVias`, `actualizarCercanos`, `colorVia`) · Capa: «Red vial» / «Mostrar vías (INEI)»

## Qué hace

Muestra las vías alrededor de la línea y calcula, **por tipo de vía, la distancia más corta desde el punto de falla**. Responde «¿hasta dónde llega la camioneta y cuánto hay que caminar?».

## Fuente

`vias_inei.json` — **INEI, SIGE Atlas**, franja de ~5 km alrededor de las líneas (10 537 elementos). Formato: `{"t": tipo, "p": [[lon, lat], ...]}`.

## Tipos de vía

| Clave | Nombre en pantalla | Color | Grosor | Estilo |
|---|---|---|---|---|
| `Asfaltada` | Carretera asfaltada | Negro `#212121` (gris claro en modo oscuro) | 4 px | Continua |
| `Afirmada` | Carretera afirmada | Marrón `#8D6E63` | 3 px | Continua |
| `Carrozable` | Camino carrozable | Ámbar `#FFB300` | 2 px | Continua |
| `Herradura` | Camino de herradura | Morado `#AB47BC` | 2 px | **Punteada** (solo a pie o a caballo) |

Al activar la capa aparecen casillas (o un selector múltiple en la versión web) para mostrar u ocultar cada tipo.

## Cálculo

Igual que en [ríos y acequias](07-rios-acequias.md): se filtran los elementos cuyo recuadro cruza la zona de la línea (±0.05°) y, para cada tipo activo, se busca el tramo más cercano al punto de falla, si está a ≤ 5 km.

## En el panel

Tarjeta «Accesos e hidrografía cercanos», por ejemplo:

```
Carretera asfaltada   3.20 km
Carretera afirmada    850 m
Camino carrozable     240 m
Camino de herradura   60 m
```

## Uso en el reporte PDF

- Tabla con la distancia a cada tipo de vía.
- Alerta según el **acceso vehicular** más cercano (asfaltada, afirmada o carrozable, excluye herradura):
  - Ninguno a 5 km → **media**: «No se identificó acceso vehicular en un radio de 5 km».
  - A más de 1 km → **media**: «prever tramo a pie».
  - A 1 km o menos → informativa.

## Limitación

Es la distancia en línea recta al tramo más cercano, no la distancia de recorrido. No considera pendiente, puentes ni el estado actual de la vía.
