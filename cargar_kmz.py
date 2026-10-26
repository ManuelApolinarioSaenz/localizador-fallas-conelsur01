"""
Carga de líneas de transmisión y subestaciones directamente desde archivos
KMZ, reemplazando consolidado_total.xlsx y el diccionario SUBESTACIONES_POR_LINEA
que antes se mantenía a mano.

Convención de nombres de archivo (confirmada con archivos reales de Conelsur):

  - SUBESTACIÓN:  "<kV>KV_SE_<nombre>.kmz"   ej. "220KV_SE_Ishcayucro (ATN).kmz"
                  Adentro: un Placemark de tipo <Polygon> (el patio de la
                  subestación). Se usa el centroide del polígono como posición.

  - LÍNEA:        "L-<código>[ Nombre1-Nombre2].kmz"   ej. "L-2263.kmz"
                  Adentro: Placemarks de tipo <Point> — las torres (T01, T02, ...)
                  y, en los dos extremos, las subestaciones de ese tramo con
                  nombre "SE <nombre>". El trazado también viene como una
                  <LineString> (CONDUCTOR_LT), pero coincide vértice a vértice
                  con las torres, así que no hace falta usarla aparte.

Todos los .kmz (líneas y subestaciones) pueden convivir en una sola carpeta
del repositorio, p. ej. kmz/ — el nombre del archivo basta para clasificarlos.
"""

import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd
import streamlit as st

NS_KML = "{http://www.opengis.net/kml/2.2}"

# Color por nivel de tensión para la leyenda del mapa — AJUSTAR si no coincide
# con tu convención real. Como el KMZ de una LÍNEA no trae el voltaje adentro,
# falta definir de dónde sale (ver pregunta en el chat). En cuanto lo confirmes,
# se usa este mismo diccionario para colorear cada línea según su voltaje.
COLORES_POR_VOLTAJE = {
    220: "#111111",   # negro
    138: "#808080",   # gris medio
    69: "#B5B5B5",    # gris claro
    60: "#111111",    # negro (comparte estilo con 50 kV en la leyenda de referencia)
    50: "#111111",
}


def _leer_kml_de_kmz(ruta_kmz: Path) -> ET.Element:
    """Un KMZ es un .zip que contiene un doc.kml (u otro .kml) adentro."""
    with zipfile.ZipFile(ruta_kmz, "r") as z:
        nombres_kml = [n for n in z.namelist() if n.lower().endswith(".kml")]
        if not nombres_kml:
            raise ValueError(f"{ruta_kmz.name} no contiene ningún archivo .kml")
        nombre_elegido = next((n for n in nombres_kml if n.lower() == "doc.kml"), nombres_kml[0])
        contenido = z.read(nombre_elegido)
    return ET.fromstring(contenido)


def _coords_texto_a_latlon(texto_coords: str):
    """'<coordinates>' en KML viene como "lon,lat,alt" — puede haber varias."""
    puntos = []
    for grupo in texto_coords.strip().split():
        partes = grupo.split(",")
        if len(partes) >= 2:
            lon, lat = float(partes[0]), float(partes[1])
            puntos.append((lat, lon))
    return puntos


def _es_archivo_subestacion(nombre_archivo: str) -> bool:
    """'220KV_SE_...' / '138KV_SE ...' -> subestación."""
    return bool(re.match(r"^\d+\s*kv[_ ]+se", nombre_archivo, re.IGNORECASE))


def _parsear_subestacion(ruta_kmz: Path):
    """Devuelve (nombre, lat, lon, voltaje_kv) a partir del polígono del patio
    y del nombre del archivo."""
    nombre_sin_ext = ruta_kmz.stem
    m = re.match(r"^(\d+)\s*kv[_ ]+se[_ ]*(.*)$", nombre_sin_ext, re.IGNORECASE)
    voltaje_kv = int(m.group(1)) if m else None
    nombre_se = re.sub(r"_+", " ", m.group(2)).strip() if m else nombre_sin_ext
    nombre_se = f"SE {nombre_se}" if not nombre_se.upper().startswith("SE") else nombre_se

    raiz = _leer_kml_de_kmz(ruta_kmz)

    anillo = raiz.find(f".//{NS_KML}Polygon/{NS_KML}outerBoundaryIs/{NS_KML}LinearRing/{NS_KML}coordinates")
    if anillo is not None and anillo.text:
        puntos = _coords_texto_a_latlon(anillo.text)
        if puntos:
            lat_c = sum(p[0] for p in puntos) / len(puntos)
            lon_c = sum(p[1] for p in puntos) / len(puntos)
            return nombre_se, lat_c, lon_c, voltaje_kv

    # Respaldo: si no hay polígono, probar con un Point directo
    punto = raiz.find(f".//{NS_KML}Point/{NS_KML}coordinates")
    if punto is not None and punto.text:
        lat, lon = _coords_texto_a_latlon(punto.text)[0]
        return nombre_se, lat, lon, voltaje_kv

    return None


def _parsear_linea(ruta_kmz: Path):
    """Devuelve (nombre_linea, lista_torres, lista_subestaciones_inline).
    lista_torres: [(nombre, lat, lon), ...]  (excluye las que empiezan con 'SE ')
    lista_subestaciones_inline: [(nombre, lat, lon), ...]"""
    nombre_linea = ruta_kmz.stem
    raiz = _leer_kml_de_kmz(ruta_kmz)

    torres, subestaciones_inline = [], []
    contador_sin_nombre = 0

    for placemark in raiz.iter(f"{NS_KML}Placemark"):
        nombre_el = placemark.find(f"{NS_KML}name")
        nombre = nombre_el.text.strip() if nombre_el is not None and nombre_el.text else None

        punto = placemark.find(f"{NS_KML}Point/{NS_KML}coordinates")
        if punto is None or not punto.text:
            continue  # ignora el Placemark de la LineString (CONDUCTOR_LT), ya cubierto por las torres

        puntos = _coords_texto_a_latlon(punto.text)
        if not puntos:
            continue
        lat, lon = puntos[0]

        if not nombre:
            contador_sin_nombre += 1
            nombre = f"T{contador_sin_nombre:02d}"

        if nombre.upper().startswith("SE "):
            subestaciones_inline.append((nombre, lat, lon))
        else:
            torres.append((nombre, lat, lon))

    return nombre_linea, torres, subestaciones_inline


@st.cache_data(ttl=3600, show_spinner="Leyendo archivos KMZ (líneas y subestaciones)...")
def cargar_lineas_y_subestaciones_kmz(carpeta: str = "kmz"):
    """Reemplazo de pd.read_excel('consolidado_total.xlsx') + SUBESTACIONES_POR_LINEA.

    Devuelve:
      df_torres: DataFrame con columnas Linea, Torre, Latitud, Longitud
                 (mismo formato que ya usa el resto de prueba01.py)
      subestaciones: dict {nombre: (lat, lon, voltaje_kv_o_None)}
    """
    carpeta_path = Path(carpeta)
    archivos_kmz = sorted(carpeta_path.glob("*.kmz"))
    if not archivos_kmz:
        raise FileNotFoundError(
            f"No se encontraron archivos .kmz en '{carpeta}/'. "
            "Sube ahí los KMZ de líneas y subestaciones."
        )

    registros_torres = []
    subestaciones = {}
    archivos_con_error = []

    # 1) Primero las subestaciones "oficiales" (con polígono y voltaje confirmado)
    for ruta in archivos_kmz:
        if not _es_archivo_subestacion(ruta.name):
            continue
        try:
            resultado = _parsear_subestacion(ruta)
            if resultado:
                nombre_se, lat, lon, voltaje_kv = resultado
                subestaciones[nombre_se] = (lat, lon, voltaje_kv)
            else:
                archivos_con_error.append(f"{ruta.name} (sin polígono ni punto reconocible)")
        except Exception as e:
            archivos_con_error.append(f"{ruta.name} ({e})")

    # 2) Luego las líneas: torres + subestaciones de extremo (solo si no vinieron
    #    ya de un archivo dedicado, para no perder el voltaje confirmado)
    for ruta in archivos_kmz:
        if _es_archivo_subestacion(ruta.name):
            continue
        try:
            nombre_linea, torres, subestaciones_inline = _parsear_linea(ruta)
            if not torres:
                archivos_con_error.append(f"{ruta.name} (sin torres reconocibles)")
                continue
            for nombre_torre, lat, lon in torres:
                registros_torres.append(
                    {"Linea": nombre_linea, "Torre": nombre_torre, "Latitud": lat, "Longitud": lon}
                )
            for nombre_se, lat, lon in subestaciones_inline:
                if nombre_se not in subestaciones:
                    subestaciones[nombre_se] = (lat, lon, None)
        except Exception as e:
            archivos_con_error.append(f"{ruta.name} ({e})")

    if archivos_con_error:
        st.warning("No se pudieron leer estos archivos KMZ:\n\n- " + "\n- ".join(archivos_con_error))

    df_torres = pd.DataFrame(registros_torres)
    df_torres["Latitud"] = pd.to_numeric(df_torres["Latitud"], errors="coerce")
    df_torres["Longitud"] = pd.to_numeric(df_torres["Longitud"], errors="coerce")
    df_torres["Torre"] = df_torres["Torre"].astype(str).str.strip()
    df_torres = df_torres.dropna(subset=["Latitud", "Longitud"]).reset_index(drop=True)

    return df_torres, subestaciones
