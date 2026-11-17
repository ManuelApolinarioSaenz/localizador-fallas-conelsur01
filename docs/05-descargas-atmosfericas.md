# 5. Probabilidad de descargas atmosféricas

[← Índice](../README.md) · Código: `app.js` (`indiceRayo`, `crearGrillaRayos`, `cargarRayos`, `dibujarRayos`, `resumenRayos`) · Capa: «Probabilidad de descargas atmosféricas» · **Solo versión de escritorio**

## Qué hace

Estima, para la hora actual y las **6 horas siguientes**, la probabilidad (0–100 %) de descargas atmosféricas en toda la zona de las líneas, y la muestra como mapa de calor. A diferencia del módulo de [lluvias](04-lluvias-clima.md), que dice si *ahora* hay tormenta, este anticipa **dónde y cuándo** es probable que se forme.

> Es un **pronóstico basado en el modelo meteorológico**, no una detección de rayos observados.

## Grilla de cálculo

- Celdas de **0.25°** (~28 km) alrededor de todas las líneas, hasta **0.375°** de distancia de cualquier punto de circuito.
- Una sola consulta a Open-Meteo con todos los puntos de la grilla y `forecast_hours=7`.
- Se refresca cada **30 minutos** mientras la capa está activa.

Variables horarias usadas: `cape`, `lifted_index`, `convective_inhibition`, `precipitation_probability`, `weather_code`.

## Fórmula del índice

```
inestabilidad = 0.6 · clip((CAPE − 100) / 1400) + 0.4 · clip((0.5 − LI) / 6.5)
freno         = 1 − 0.6 · clip(|CIN| / 150)
p             = 100 · clip(PP / 100)^0.7 · inestabilidad · freno

si weather_code = 95        → p = máx(p, 70)
si weather_code = 96 o 99   → p = máx(p, 85)
```

`clip` limita entre 0 y 1. Significado:

| Variable | Interpretación |
|---|---|
| **CAPE** (J/kg) | Energía disponible para convección. Más alto = nubes de tormenta más potentes |
| **LI** (índice de elevación) | Negativo = atmósfera inestable |
| **CIN** (J/kg) | Inhibición: actúa como «tapa» que frena la convección |
| **PP** (%) | Probabilidad de precipitación |

## Niveles

| Rango | Nivel | Color |
|---|---|---|
| ≥ 60 % | Muy alto | Rojo oscuro |
| 35–60 % | Alto | Naranja |
| 15–35 % | Moderado | Amarillo |
| < 15 % | Bajo | Sin color / transparente |

El mapa se genera como imagen: interpolación **bilineal** entre celdas (10 px por celda) y una rampa de colores con transparencia. La opacidad baja al acercar el zoom para no tapar el terreno.

## Panel de resumen

Con el selector **«Hora del pronóstico»** (Hora actual, Dentro de 1 h, …):

- **Punto de falla**: % y nivel.
- **Máximo en la línea**: % y km donde ocurre (desde el extremo elegido).
- **Tramo alto o muy alto**: km de línea con ≥ 35 %.
- **Próximas horas en la falla**: serie hora a hora.
- **Actualizado**: hora de la última consulta. Si falla la conexión, se mantiene el último dato.

## Uso en el reporte PDF

Tabla de probabilidad y alertas:

- ≥ 60 % en la falla → **alta**: postergar trabajos a la intemperie o en altura.
- ≥ 35 % en la falla → **media**: vigilar la evolución.
- Sube a ≥ 35 % en las próximas horas → planificar la intervención antes de esa hora.
- ≥ 60 % en otro tramo → posible recierre o nueva falla.
