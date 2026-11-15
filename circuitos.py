"""
Arma los circuitos que se muestran en el selector de la app a partir de las
torres y trazados leídos de los KMZ (cargar_kmz.py), y calcula la distancia
acumulada de cada punto.

Resuelve tres problemas del cálculo original:

1. Circuitos dobles / tramos compartidos. Un circuito como L-2001 viene
   repartido en varios archivos: el tramo compartido "L-2001-2002" (casi
   todo el recorrido) y el archivo propio "L-2001" (solo las bajadas a cada
   subestación), más a veces un tramo subterráneo "_S". Antes cada archivo
   era una "línea" distinta y L-2001 medía ~36 km en vez de ~42 km. Ahora
   cada código de circuito junta TODOS los archivos que lo contienen y se
   recorre como una sola ruta.

2. Origen en el pórtico, no en la primera torre. Si en un extremo hay una
   subestación (archivo KMZ de SE) a menos de RADIO_BUSQUEDA_SE_M, se
   agrega el vano de llegada hasta el borde del patio (o hasta su punto, si
   la SE no tiene polígono).

3. Extremos con nombre. Se devuelve el nombre de la SE de cada extremo para
   que la app permita elegir desde qué subestación se mide la distancia.
"""

import math
import re
import unicodedata

import numpy as np
import pandas as pd

from cargar_kmz import _unir_tramos, _distancia_aprox_m, _numero_de_torre

RADIO_BUSQUEDA_SE_M = 500       # SE nombrada en la línea: hasta esta distancia
RADIO_SE_SIN_NOMBRE_M = 150     # SE que no figura en el nombre de la línea
TOLERANCIA_UNION_M = 10         # unir tramos de distintos archivos
TOLERANCIA_NOMBRE_TORRE_M = 25  # vértice del trazado <-> torre con nombre
TOLERANCIA_YA_CUBIERTO_M = 15   # tramo que repite parte de la ruta ya armada


def distancia_haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 2 * R * np.arcsin(np.sqrt(a))


def codigos_de_linea(nombre_linea):
    """'L-2001-2002 SE Huinco - ...' -> ['2001', '2002'];
    'L-6040-(6031) SE ...' -> ['6040', '6031']; 'L-6527A SE ...' -> ['6527A'].
    Solo mira el primer bloque "L-..." del nombre (no el resto, que puede
    mencionar otra línea, p. ej. 'L-6528C SE Nueva Morococha - L-6528B')."""
    m = re.match(r"\s*L-(\S+)", nombre_linea)
    if not m:
        return []
    return re.findall(r"\d{4}[A-Z]{0,2}", m.group(1).upper())


def _sin_sufijo_subterranea(nombre):
    return nombre.replace(" (Subterránea)", "")


def _punto_mas_cercano_en_segmento(p, a, b):
    """Proyección (lat, lon) de p sobre el segmento a-b (aprox. plana local)."""
    k_lon = 111_320 * math.cos(math.radians(p[0]))
    px, py = p[1] * k_lon, p[0] * 111_320
    ax, ay = a[1] * k_lon, a[0] * 111_320
    bx, by = b[1] * k_lon, b[0] * 111_320
    dx, dy = bx - ax, by - ay
    largo2 = dx * dx + dy * dy
    t = 0.0 if largo2 == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / largo2))
    return (a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1]))


def _dentro_de_poligono(p, poligono):
    lat, lon = p
    dentro = False
    j = len(poligono) - 1
    for i in range(len(poligono)):
        yi, xi = poligono[i]
        yj, xj = poligono[j]
        if (yi > lat) != (yj > lat) and lon < (xj - xi) * (lat - yi) / ((yj - yi) or 1e-12) + xi:
            dentro = not dentro
        j = i
    return dentro


def _llegada_a_subestacion(p, se):
    """(distancia_m, punto_de_llegada) desde p al patio de la SE: borde del
    polígono más cercano, 0 si p ya está dentro; o su punto si no hay polígono."""
    poligono = se.get("poligono")
    if poligono and len(poligono) >= 3:
        if _dentro_de_poligono(p, poligono):
            return 0.0, p
        mejor = None
        for i in range(len(poligono)):
            q = _punto_mas_cercano_en_segmento(p, poligono[i], poligono[(i + 1) % len(poligono)])
            d = _distancia_aprox_m(p, q)
            if mejor is None or d < mejor[0]:
                mejor = (d, q)
        return mejor
    q = (se["lat"], se["lon"])
    return _distancia_aprox_m(p, q), q


def _normalizar(texto):
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9 ]+", " ", texto)


def _nombre_base_se(nombre_se):
    """'SE Caripa (UNACEM)' -> 'caripa'; 'SE Pachachaca (CNS)' -> 'pachachaca'."""
    base = re.sub(r"\(.*?\)", " ", nombre_se)
    base = re.sub(r"^\s*SE\b", " ", base, flags=re.IGNORECASE)
    return _normalizar(base).strip()


def _subestacion_en_extremo(p, subestaciones, voltaje_kv, nombre_linea):
    """Nombre, distancia y punto de llegada de la SE del extremo p.
    Una SE que aparece en el nombre de la línea se acepta hasta
    RADIO_BUSQUEDA_SE_M; cualquier otra solo si está muy cerca
    (RADIO_SE_SIN_NOMBRE_M), para no "estirar" la línea hasta un patio vecino
    que no le corresponde. Se prefiere el mismo nivel de tensión."""
    nombre_linea_norm = f" {_normalizar(nombre_linea)} "
    candidatas = []
    for nombre, se in subestaciones.items():
        if se.get("lat") is None:
            continue
        # descarte rápido por distancia al centro
        if _distancia_aprox_m(p, (se["lat"], se["lon"])) > RADIO_BUSQUEDA_SE_M + 2000:
            continue
        d, q = _llegada_a_subestacion(p, se)
        base = _nombre_base_se(nombre)
        en_nombre = bool(base) and f" {base} " in nombre_linea_norm
        if d <= (RADIO_BUSQUEDA_SE_M if en_nombre else RADIO_SE_SIN_NOMBRE_M):
            mismo_kv = voltaje_kv is not None and se.get("voltaje_kv") == voltaje_kv
            candidatas.append((0 if en_nombre else 1, 0 if mismo_kv else 1, d, nombre, q))
    if not candidatas:
        return None
    _, _, d, nombre, q = min(candidatas)
    return nombre, d, q


def _armar_ruta(cadenas):
    """Encadena los tramos en una sola ruta: parte del más largo y le pega,
    por el extremo más cercano, el tramo restante más próximo. Descarta los
    tramos de largo ~0 y los que solo repiten parte de la ruta ya armada
    (si no, se agregarían "ida y vuelta" falsos)."""
    restantes = [c for c in cadenas if len(c) >= 2 and _largo(c) >= 1.0]
    if not restantes:
        return [p for c in cadenas for p in c][:1]
    restantes.sort(key=_largo, reverse=True)
    ruta = list(restantes.pop(0))
    while restantes:
        restantes = [c for c in restantes if not _ya_cubierto(c, ruta)]
        if not restantes:
            break
        mejor = None
        for i, c in enumerate(restantes):
            for d, extremo, orientada in (
                (_distancia_aprox_m(ruta[-1], c[0]), "fin", c),
                (_distancia_aprox_m(ruta[-1], c[-1]), "fin", c[::-1]),
                (_distancia_aprox_m(ruta[0], c[-1]), "inicio", c),
                (_distancia_aprox_m(ruta[0], c[0]), "inicio", c[::-1]),
            ):
                if mejor is None or d < mejor[0]:
                    mejor = (d, i, extremo, orientada)
        salto, i, extremo, c = mejor
        restantes.pop(i)
        if salto > TOLERANCIA_YA_CUBIERTO_M and _largo(c) < salto:
            # Fragmento suelto (p. ej. un trazo de 30 m dibujado aparte):
            # pegarlo agregaría un salto recto más largo que el propio tramo.
            continue
        ruta = ruta + list(c) if extremo == "fin" else list(c) + ruta
    # sin puntos repetidos consecutivos
    limpia = [ruta[0]]
    for p in ruta[1:]:
        if _distancia_aprox_m(limpia[-1], p) > 0.5:
            limpia.append(p)
    return limpia


def _largo(cadena):
    return sum(_distancia_aprox_m(cadena[i], cadena[i + 1]) for i in range(len(cadena) - 1))


def _ya_cubierto(cadena, ruta):
    for p in cadena:
        cerca = False
        for i in range(len(ruta) - 1):
            if _distancia_aprox_m(p, _punto_mas_cercano_en_segmento(p, ruta[i], ruta[i + 1])) <= TOLERANCIA_YA_CUBIERTO_M:
                cerca = True
                break
        if not cerca:
            return False
    return True


def _puntos_de_circuito(nombres_miembro, df_torres, trazados_lineas):
    """Ruta (vértices del trazado) de un circuito formado por varios archivos,
    con el nombre de la torre más cercana en cada vértice ('' si no hay)."""
    segmentos = [c for n in nombres_miembro for c in trazados_lineas.get(n) or []]
    torres = df_torres[df_torres["Linea"].isin(nombres_miembro)]
    torres = [(r.Torre, r.Latitud, r.Longitud) for r in torres.itertuples()]

    ruta = _armar_ruta(_unir_tramos(segmentos, tolerancia_m=TOLERANCIA_UNION_M)) if segmentos else []
    if len(ruta) < 2:
        # sin trazado: las torres de todos los archivos, por número
        torres.sort(key=lambda t: (_numero_de_torre(t[0]) or 10**9, t[0]))
        return [(n, la, lo) for n, la, lo in torres]

    puntos = []
    for lat, lon in ruta:
        nombre, mejor = "", TOLERANCIA_NOMBRE_TORRE_M
        for n, la, lo in torres:
            d = _distancia_aprox_m((lat, lon), (la, lo))
            if d <= mejor:
                nombre, mejor = n, d
        puntos.append((nombre, lat, lon))
    # Sentido: empezar por la torre de menor número si la mayoría va al revés.
    numeros = [_numero_de_torre(n) for n, _, _ in puntos if n]
    pares = [(a, b) for a, b in zip(numeros, numeros[1:]) if a is not None and b is not None]
    if sum(b < a for a, b in pares) > sum(b > a for a, b in pares):
        puntos.reverse()
    return puntos


def _con_distancias(nombre_linea, puntos):
    df = pd.DataFrame(puntos, columns=["Torre", "Latitud", "Longitud"])
    df.insert(0, "Linea", nombre_linea)
    lat, lon = df["Latitud"].to_numpy(float), df["Longitud"].to_numpy(float)
    tramos = distancia_haversine_m(lat[:-1], lon[:-1], lat[1:], lon[1:]) if len(df) > 1 else np.array([])
    df["Distancia_m"] = np.concatenate([[0.0], np.cumsum(tramos)])
    return df


def construir_circuitos(df_torres, info_lineas, trazados_lineas, subestaciones):
    """Devuelve:
      datos_lineas: {nombre_circuito: DataFrame[Linea, Torre, Latitud,
                     Longitud, Distancia_m]} — lo que lista el selector.
                     'Torre' vacío = vértice del trazado sin torre marcada.
      partes:       {nombre_circuito: [nombres de archivo/línea originales]}
                     para dibujarlo con su estilo (aéreo/subterráneo).
      extremos:     {nombre_circuito: (SE_inicio | None, SE_fin | None)}
      info_circuitos: {nombre_circuito: {"voltaje_kv", "tipo"}}
    """
    nombres = list(dict.fromkeys(df_torres["Linea"]))
    codigos = {n: codigos_de_linea(n) for n in nombres}

    miembros_por_codigo = {}
    for n in nombres:
        for c in codigos[n]:
            miembros_por_codigo.setdefault(c, []).append(n)

    def _es_circuito_compuesto(codigo):
        miembros = miembros_por_codigo[codigo]
        return len(miembros) > 1 or len(codigos[miembros[0]]) > 1

    datos_lineas, partes, extremos, info_circuitos = {}, {}, {}, {}

    # Orden del selector: el de los archivos; cada circuito compuesto aparece
    # donde aparece su primer archivo.
    vistos = set()
    for n in nombres:
        cods = codigos[n]
        compuestos = [c for c in cods if _es_circuito_compuesto(c)]
        if not compuestos:
            if n not in vistos:
                vistos.add(n)
                datos_lineas[n] = _puntos_de_circuito([n], df_torres, trazados_lineas)
                partes[n] = [n]
                info_circuitos[n] = dict(info_lineas.get(n, {}))
            continue
        for c in compuestos:
            if c in vistos:
                continue
            vistos.add(c)
            miembros = miembros_por_codigo[c]
            # Nombre: el del archivo propio del circuito si existe
            # ("L-2001 SE Huinco - SE Carapongo"); si no, el del compartido
            # con el código cambiado.
            propio = [m for m in miembros if codigos[m] == [c]]
            base = _sin_sufijo_subterranea(propio[0] if propio else miembros[0])
            resto = re.sub(r"^\s*L-\S+\s*", "", base)
            resto = re.sub(r"\s*\(SE [^()]*\)\s*$", "", resto)  # quita "(SE x - SE y)" del compartido
            nombre_circuito = f"L-{c} {resto}".strip()

            datos_lineas[nombre_circuito] = _puntos_de_circuito(miembros, df_torres, trazados_lineas)
            partes[nombre_circuito] = miembros
            tipos = {info_lineas.get(m, {}).get("tipo") for m in miembros} - {None}
            kvs = [info_lineas.get(m, {}).get("voltaje_kv") for m in miembros]
            info_circuitos[nombre_circuito] = {
                "voltaje_kv": next((k for k in kvs if k), None),
                "tipo": "Aérea y subterránea" if len(tipos) > 1 else (tipos.pop() if tipos else None),
            }

    # Vano de llegada a la subestación de cada extremo (pórtico)
    for nombre, puntos in list(datos_lineas.items()):
        if len(puntos) < 2:
            datos_lineas[nombre] = _con_distancias(nombre, puntos)
            extremos[nombre] = (None, None)
            continue
        kv = info_circuitos.get(nombre, {}).get("voltaje_kv")
        p_ini = (puntos[0][1], puntos[0][2])
        p_fin = (puntos[-1][1], puntos[-1][2])
        se_ini = _subestacion_en_extremo(p_ini, subestaciones, kv, nombre)
        se_fin = _subestacion_en_extremo(p_fin, subestaciones, kv, nombre)
        if se_ini and se_fin and _nombre_base_se(se_ini[0]) == _nombre_base_se(se_fin[0]):
            # la misma SE en ambos extremos: solo vale para el más cercano
            if se_ini[1] <= se_fin[1]:
                se_fin = None
            else:
                se_ini = None
        puntos = list(puntos)
        if se_ini and se_ini[1] > 1.0:
            puntos.insert(0, (f"Pórtico {se_ini[0]}", se_ini[2][0], se_ini[2][1]))
        if se_fin and se_fin[1] > 1.0:
            puntos.append((f"Pórtico {se_fin[0]}", se_fin[2][0], se_fin[2][1]))
        datos_lineas[nombre] = _con_distancias(nombre, puntos)
        extremos[nombre] = (se_ini[0] if se_ini else None, se_fin[0] if se_fin else None)

    return datos_lineas, partes, extremos, info_circuitos


def distancia_puntos_a_linea(lats, lons, df_linea):
    """Distancia mínima (m) de cada punto al recorrido de la línea y su
    progresiva (m, desde el inicio de la línea) en el punto más cercano.
    Aproximación plana local: suficiente para distancias de pocos km."""
    lats = np.asarray(lats, float)
    lons = np.asarray(lons, float)
    la = df_linea["Latitud"].to_numpy(float)
    lo = df_linea["Longitud"].to_numpy(float)
    prog = df_linea["Distancia_m"].to_numpy(float)
    if len(lats) == 0 or len(la) < 2:
        return np.full(len(lats), np.nan), np.full(len(lats), np.nan)
    k_lon = 111_320 * np.cos(np.radians(lats))[:, None]   # (N, 1)
    k_lat = 110_574
    ax = (lo[None, :-1] - lons[:, None]) * k_lon
    ay = (la[None, :-1] - lats[:, None]) * k_lat
    bx = (lo[None, 1:] - lons[:, None]) * k_lon
    by = (la[None, 1:] - lats[:, None]) * k_lat
    vx, vy = bx - ax, by - ay
    l2 = vx * vx + vy * vy
    t = np.clip(np.where(l2 > 0, -(ax * vx + ay * vy) / np.where(l2 > 0, l2, 1), 0), 0, 1)
    dist = np.hypot(ax + t * vx, ay + t * vy)           # (N, segmentos)
    j = dist.argmin(axis=1)
    filas = np.arange(len(lats))
    progresiva = prog[j] + t[filas, j] * (prog[j + 1] - prog[j])
    return dist[filas, j], progresiva
