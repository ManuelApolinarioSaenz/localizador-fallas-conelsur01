# 1. Líneas de transmisión y circuitos

[← Índice](../README.md) · Código: `cargar_kmz.py`, `circuitos.py`

## Qué hace

Convierte los archivos KMZ de la carpeta `kmz/` en la lista de **circuitos** que aparece en el selector «Línea de transmisión», cada uno con sus puntos ordenados y la **progresiva** (metros desde el inicio) de cada punto. Esa progresiva es la base para ubicar la falla.

## Convención de nombres de archivo

El nombre del archivo basta para clasificarlo (todos pueden estar en la misma carpeta):

| Tipo | Patrón | Ejemplo |
|---|---|---|
| Línea | `<kV>KV_L-<código[-código2]>_<Origen> - <Destino>[_A\|_S].kmz` | `220KV_L-2007_SE Matucana - SE Callahuanca_A.kmz` |
| Subestación | `<kV>KV_SE <nombre>.kmz` | `220KV_SE Cajamarca Norte.kmz` |

- `<kV>` define el **nivel de tensión** y el color de la línea.
- El sufijo `_A` (aérea) o `_S` (subterránea) es **opcional**. Las subterráneas se dibujan punteadas y se nombran `… (Subterránea)`.
- Archivos con `ZZZ` en el nombre (combinados de varios circuitos, p. ej. `138KV_L-1040-1047_SE ZZZ_A.kmz`) **se ignoran**: repiten circuitos que ya tienen archivo propio y suelen tener solo los extremos.

## Paso 1 — Lectura de cada KMZ de línea (`cargar_kmz.py`)

1. Un KMZ es un `.zip` con un `doc.kml`. Si el XML trae prefijos de espacio de nombres mal declarados, se limpian y se vuelve a leer.
2. De cada `Placemark` se toma:
   - `Point` con nombre `SE …` → subestación de extremo («inline»).
   - Otro `Point` → **torre** (sin nombre se numera `T01`, `T02`…).
   - `LineString` (también dentro de `MultiGeometry`) → segmentos del **trazado real**.
3. Los segmentos sueltos (muchos KMZ dibujan torre a torre, en cualquier orden y sentido) se **unen** por extremos que coinciden con 5 m de tolerancia.
4. Orden de las torres:
   - Con trazado: se ordenan por su **posición proyectada sobre el trazado** (no por el número del nombre, que puede ser `TA-12`, `PMB-76`, descendente, etc.). Si la mayoría de la numeración queda al revés, se invierte el sentido.
   - Sin torres pero con trazado (típico de cables subterráneos): se usan los vértices del trazado.
   - Sin trazado: se ordenan por el número del nombre (último recurso).

Resultado: tabla `Linea, Torre, Latitud, Longitud` + trazados + `voltaje_kv` y `tipo` por archivo.

## Paso 2 — Armado de circuitos (`circuitos.py`)

Un circuito como **L-2001** viene repartido en varios archivos: el tramo compartido de doble circuito `L-2001-2002`, el archivo propio `L-2001` (bajadas a cada SE) y a veces un tramo subterráneo `_S`. Si se tratara cada archivo por separado, L-2001 mediría ~36 km en vez de ~42 km.

1. **Códigos**: de `L-2001-2002 …` se obtienen `2001` y `2002`; de `L-6040-(6031)` → `6040`, `6031`; de `L-6527A` → `6527A`.
2. **Agrupación**: cada código junta *todos* los archivos que lo contienen.
3. **Ruta única**: se unen los tramos (tolerancia 10 m), se parte del más largo y se pega el tramo más cercano por el extremo correcto. Se descartan tramos que solo repiten parte de la ruta (≤ 15 m) y fragmentos sueltos que crearían un salto recto mayor que el propio tramo.
4. **Nombre de torre en cada vértice**: si hay una torre a ≤ 25 m del vértice, el vértice toma su nombre; si no, queda vacío (vértice del trazado sin torre).
5. **Pórticos**: se agrega el vano hasta el patio de la SE de cada extremo (ver [Subestaciones](02-subestaciones.md)).
6. **Progresiva**: distancia acumulada (fórmula de Haversine) desde el primer punto → columna `Distancia_m`.
7. **Tensión y tipo del circuito**: el kV del primer archivo que lo tenga; el tipo es «Aérea», «Subterránea» o «Aérea y subterránea».

### Parámetros

| Constante | Valor | Uso |
|---|---|---|
| `TOLERANCIA_UNION_M` | 10 m | Unir tramos de distintos archivos |
| `TOLERANCIA_NOMBRE_TORRE_M` | 25 m | Asignar nombre de torre a un vértice |
| `TOLERANCIA_YA_CUBIERTO_M` | 15 m | Detectar tramos repetidos |

## Cómo se ve en el mapa

- Todas las líneas se dibujan con el color de su tensión: **220 kV rojo**, **138 kV verde**, **69 kV naranja**, **60/50 kV azul**, gris si no se pudo determinar.
- Tramos subterráneos: línea punteada.
- La **línea seleccionada** se resalta en azul CONELSUR, más gruesa, con sus torres como puntos. Al pasar el mouse sobre una torre se ve su progresiva desde el extremo elegido.
- Solo se dibujan las torres de la línea seleccionada, para no saturar el mapa.

## Respaldo con Excel (solo versión web)

Si la carpeta `kmz/` no existe o está vacía, `prueba01.py` lee `consolidado_total.xlsx`, descarta torres sin coordenadas, calcula la progresiva torre a torre y nombra los extremos con el diccionario `SUBESTACIONES_POR_LINEA`. En este modo no hay trazado real, polígonos de SE ni pórticos.
