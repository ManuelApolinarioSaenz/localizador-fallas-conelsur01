# 11. Reporte PDF

[← Índice](../README.md) · Código: `escritorio/web/reporte.js` · Botón: «Generar reporte PDF» · **Solo versión de escritorio**

## Qué hace

Genera con un clic un informe de la falla, listo para enviar a la cuadrilla o adjuntar al informe de evento. Se guarda como:

```
Reporte_falla_<código>_<AAAAMMDD>_<HHMM>.pdf
```

## Proceso

1. Guarda la configuración actual del usuario (capas, vista, modo oscuro, posición del mapa).
2. **Activa temporalmente todas las capas** y todos los tipos de vía, y quita el modo oscuro.
3. Consulta en paralelo incendios, clima de la línea, clima de la falla y probabilidad de descargas.
4. Calcula distancias y **alertas** (`datosReporte`).
5. Captura tres imágenes del mapa:
   1. **Vista general** de la línea (calle, con probabilidad de descargas).
   2. **Detalle satelital** del punto de falla (zoom 14.3).
   3. **Detalle de calles** del punto de falla (zoom 14.3).

   Cada imagen incluye el marcador de falla, las etiquetas de SE, la escala gráfica y los créditos del mapa base.
6. Arma el PDF con jsPDF y lo descarga.
7. **Restaura** la configuración original del usuario, aunque haya ocurrido un error.

## Contenido

**Página 1**
- Encabezado con logo y fecha.
- Indicadores: distancia de falla, longitud, tensión, torres.
- **Datos del evento**: línea, medido desde, tensión/tipo, distancia, entre torres, coordenadas, longitud y extremos.
- **Alertas y precauciones**, ordenadas por nivel (alta → media → informativa).
- Vista general de la línea y leyenda.

**Página 2**: detalle satelital y de calles del punto de falla.

**Página 3 (tablas)**
- Torres adyacentes a la falla (2 antes y 2 después): progresiva, distancia a la falla y coordenadas.
- Accesos e hidrografía: cada tipo de vía, río, acequia y SE más cercana.
- Centros poblados rurales hasta 3 km de la falla.
- Incendios en atención cercanos.
- Condiciones meteorológicas.
- Probabilidad de descargas atmosféricas, con la serie por hora.
- Notas y fuentes.

## Reglas de alerta

| Nivel | Condición |
|---|---|
| Alta | Incendio en atención a < 100 m o < 500 m de la línea · Tormenta en el punto de falla · Probabilidad de descargas ≥ 60 % en la falla |
| Media | Incendio a < 5 km de la falla · Lluvia en la falla · Acumulado ≥ 10 mm/24 h · Probabilidad ≥ 35 % ahora o en las próximas horas · ≥ 60 % en otro tramo · Tormenta en algún punto de la línea · Centro poblado a ≤ 300 m · Sin acceso vehicular a 5 km o a más de 1 km · Río a < 300 m |
| Informativa | Acceso vehicular más cercano · Centro poblado más cercano · SE más cercana · «Sin alertas» si no hay ninguna de nivel alto o medio |

## Detalles técnicos

- Las fuentes estándar de jsPDF solo admiten Latin-1: guiones largos, comillas tipográficas y símbolos como `≤` se reemplazan por equivalentes simples.
- El mapa se crea con `preserveDrawingBuffer: true` para poder capturarlo.
- Sin conexión, el reporte se genera igual y las secciones de clima, descargas e incendios indican «sin conexión».
