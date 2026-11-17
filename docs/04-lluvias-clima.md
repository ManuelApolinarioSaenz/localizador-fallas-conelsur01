# 4. Lluvias y clima

[← Índice](../README.md) · Código: `prueba01.py` (`cargar_clima`, `cargar_clima_en_puntos`), `app.js` (`cargarClimaLinea`, `cargarClimaFalla`) · Capa: «Lluvia y tormentas eléctricas» / «Mostrar clima (lluvia / riesgo de rayo)»

## Qué hace

Indica si **está lloviendo o hay tormenta eléctrica** a lo largo de la línea y en el punto de falla. Sirve para dos cosas: evaluar si la falla pudo ser causada por una descarga, y decidir si es seguro enviar la cuadrilla.

## Fuente

**Open-Meteo** (`https://api.open-meteo.com/v1/forecast`), gratuita y sin clave. Zona horaria `America/Lima`.

> Open-Meteo no da la ubicación de cada rayo. El **código de tiempo** (`weather_code`) indica si hay tormenta eléctrica en curso en el punto consultado, que es la mejor aproximación gratuita.

## A lo largo de la línea (mapa de calor)

1. Se toman **~12 puntos** repartidos a lo largo del circuito (`paso = n_puntos // 12`; máx. 25 en escritorio).
2. Se consulta el clima actual de todos en **una sola llamada** (Open-Meteo acepta listas de coordenadas).
3. Cada punto recibe un peso:

   | Condición | Peso |
   |---|---|
   | Tormenta eléctrica (código 95, 96 o 99) | 1.00 |
   | Lluvia (precipitación > 0) | 0.35 |
   | Seco | 0.04 |

4. Se dibuja un **mapa de calor morado**: oscuro = tormenta, claro = lluvia.

## En el punto de falla (detalle)

Variables consultadas: `precipitation`, `weather_code`, `wind_speed_10m` actuales, y precipitación horaria con un día hacia atrás (`past_days=1`).

| Resultado | Alerta |
|---|---|
| Código 95/96/99 | **Roja**: «Riesgo de descarga atmosférica en el punto de falla» |
| Lluvia > 0 | **Ámbar**: «Lluvia en el punto de falla (X mm/h)» |
| Sin lluvia | **Azul / informativa**: «Sin lluvia en el punto de falla» |

Además se muestra el **acumulado de lluvia de 24 h** (suma de las primeras 24 horas de la serie horaria) y, en escritorio, la velocidad del viento.

### Tabla de códigos de tiempo (`DESCRIPCION_CLIMA`)

0 Despejado · 1 Mayormente despejado · 2 Parcialmente nublado · 3 Nublado · 45/48 Niebla · 51–57 Llovizna · 61–67 Lluvia · 71–77 Nieve · 80–82 Chubascos · 85–86 Chubascos de nieve · **95 Tormenta eléctrica · 96/99 Tormenta con granizo**.

## Actualización y caché

| Versión | Comportamiento |
|---|---|
| Web | Respuestas en caché 10 min (`ttl=600`) por coordenada |
| Escritorio | Clima de la línea al activar la capa o cambiar de línea. Clima del punto de falla 0.6 s después de mover la distancia (evita consultas en cada pulsación) |

## Uso en el reporte PDF

Sección «Condiciones meteorológicas»: condición actual, lluvia, acumulado de 24 h, viento y cuántos puntos de la línea tienen tormenta o lluvia. Genera alertas si hay tormenta en la falla, lluvia, acumulado ≥ 10 mm en 24 h (accesos posiblemente afectados) o tormenta en algún punto de la línea.

## Consideración

Como la serie horaria empieza el día anterior a las 00:00, la «suma de las primeras 24 h» corresponde al **día calendario anterior**, no exactamente a las últimas 24 h móviles. Es una aproximación útil del acumulado reciente.
