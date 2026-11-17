# 9. Incendios activos

[← Índice](../README.md) · Código: `prueba01.py` (`cargar_emergencias_bomberos`), `app.js` (`cargarIncendios`, `dibujarIncendios`), `servidor.py` (`/api/bomberos`) · Capa: «Incendios activos»

## Qué hace

Muestra los incendios registrados por **Bomberos Perú** y **alerta si hay alguno en atención cerca de la línea seleccionada**. Un incendio forestal o de pastizal bajo la línea puede causar fallas (ionización del aire, daño a conductores) y es un riesgo para la cuadrilla.

## Fuente

Hoja de Google Sheets con el registro de emergencias de Bomberos Perú, actualizada por un tercero y descargada como CSV:

```
https://docs.google.com/spreadsheets/d/1n_YelAX4D_mFQbXLduWTpjFLfzYOElzSYM8FiiWBhto/export?format=csv
```

Columnas usadas: `Nro Parte`, `Fecha Hora`, `Dirección / Distrito`, `Tipo`, `Estado`, `Máquina`, `Coordenada` (`"lat,lon"`).

## Procesamiento

1. Se conservan solo las filas cuyo `Tipo` contiene **«INCENDIO»**.
2. Se separa la coordenada en latitud y longitud. Se descartan coordenadas vacías o `0,0`.
3. Estado: **ATENDIENDO** (en atención) o **CERRADO**.
4. Para los incendios en atención se calcula la distancia a la línea seleccionada:
   - Web: distancia a la **torre más cercana**.
   - Escritorio: distancia al **trazado** (más preciso entre torres).

## Alertas en el panel

| Condición | Alerta |
|---|---|
| Incendio en atención a < 500 m de la línea | Roja: «N incendio(s) en atención a menos de 500 m» + lista con dirección, distancia y fecha |
| Incendio en atención a < 100 m | Roja: **«Alerta crítica»**, riesgo inmediato |

Además se muestra el total nacional: «N en atención · M cerrados».

## En el mapa

| Estado | Símbolo |
|---|---|
| En atención | Punto **rojo** con halo naranja |
| Cerrado | Punto **naranja** |

Tooltip: tipo, estado, dirección, fecha y hora, unidades (máquinas) asignadas.

Se muestran los incendios de **todo el Perú**, no solo los cercanos.

## Actualización

| Versión | Frecuencia |
|---|---|
| Web | Caché de 90 s |
| Escritorio | El navegador consulta cada 90 s mientras la capa está activa. El servidor local guarda la respuesta 60 s y actúa de proxy (la hoja no permite leerla directamente desde el navegador por CORS). Si no hay conexión, entrega la última copia. |

## Uso en el reporte PDF

- Tabla de incendios en atención a < 5 km de la línea o < 10 km de la falla, con distancia a la línea y a la falla.
- Alertas: **alta** si hay alguno a < 100 m o < 500 m de la línea; **media** si hay alguno a < 5 km del punto de falla.
