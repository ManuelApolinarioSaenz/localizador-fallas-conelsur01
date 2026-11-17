# 2. Subestaciones

[← Índice](../README.md) · Código: `cargar_kmz.py` (`_parsear_subestacion`), `circuitos.py` (`_subestacion_en_extremo`), capa «Subestaciones»

## Qué hace

1. Dibuja el **patio real** de cada subestación (polígono) con su nombre y tensión.
2. Identifica la **subestación de cada extremo** de una línea, que es desde donde mide el relé.
3. Agrega el **vano de llegada al pórtico**, para que la distancia se cuente desde la SE y no desde la primera torre.

## Fuentes

| Prioridad | Origen | Datos |
|---|---|---|
| 1 | Archivo dedicado `<kV>KV_SE <nombre>.kmz` | Polígono del patio, centroide (para la etiqueta) y kV confirmado |
| 2 | Puntos `SE …` dentro de los KMZ de línea | Solo un punto, sin polígono ni kV. Se usa si no existe el archivo dedicado |
| 3 | `SUBESTACIONES_POR_LINEA` en `prueba01.py` (modo Excel) | Nombre de origen/destino por código de línea; posición = primera/última torre |

El nombre se normaliza a `SE <nombre>`. Si el archivo no tiene polígono, se usa un `Point`.

## Identificación de extremos y pórticos

Para cada extremo (primer y último punto) del circuito se busca una subestación candidata:

- Si la SE **aparece en el nombre de la línea** (p. ej. «Huinco» en `L-2001 SE Huinco - SE Carapongo`), se acepta hasta **500 m** (`RADIO_BUSQUEDA_SE_M`).
- Si **no aparece**, solo hasta **150 m** (`RADIO_SE_SIN_NOMBRE_M`), para no «estirar» la línea hasta un patio vecino que no le corresponde.
- Entre candidatas se prefiere: nombrada en la línea → mismo nivel de tensión → más cercana.
- La distancia se mide al **borde del polígono** más cercano (0 si el extremo ya está dentro del patio) o al punto si no hay polígono.
- Si sale la misma SE en ambos extremos, solo se asigna al más cercano.

Si la distancia al patio es mayor que 1 m, se agrega un punto llamado `Pórtico SE <nombre>` al inicio o al final del circuito. En el mapa, ese vano se dibuja como una línea azul punteada («Vano de llegada»).

## En la interfaz

- **Capa «Subestaciones»** (casilla): polígonos grises semitransparentes con borde oscuro y etiqueta `SE <nombre> · <kV> kV`.
- **Selector «Distancia medida desde / Medir distancia desde»**: muestra las dos SE de extremo. Si no se identificó SE en un extremo, aparece «Inicio de la línea (T01)» o «Fin de la línea (T…)».
- **Reporte PDF**: incluye la subestación más cercana al punto de falla y su distancia.
