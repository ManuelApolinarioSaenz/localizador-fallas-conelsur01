"""Genera escritorio/web/datos.json para la versión de escritorio (un solo .exe).

Precalcula todo lo que la app de Streamlit calculaba en cada interacción:
circuitos completos (con origen en el pórtico y progresivas), subestaciones,
centros poblados rurales, vías y ríos/acequias del INEI.

Uso (desde la raíz del repositorio, con el entorno que tiene streamlit/pandas):
    python escritorio/generar_datos.py
"""
import json
import logging
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
os.chdir(RAIZ)
logging.disable(logging.CRITICAL)

import pandas as pd  # noqa: E402

from cargar_kmz import cargar_lineas_y_subestaciones_kmz  # noqa: E402
from circuitos import construir_circuitos  # noqa: E402


def r(v, n=6):
    return round(float(v), n)


def main():
    df, subestaciones, info_lineas, trazados = cargar_lineas_y_subestaciones_kmz("kmz")
    datos_lineas, partes_circuito, extremos, info_circuitos = construir_circuitos(
        df, info_lineas, trazados, subestaciones
    )

    # Trazos de dibujo: uno por archivo KMZ original (conserva aéreo/subterráneo)
    partes, indice_parte = [], {}
    for nombre_parte, cadenas in trazados.items():
        inf = info_lineas.get(nombre_parte, {})
        for cadena in cadenas or []:
            if len(cadena) < 2:
                continue
            indice_parte.setdefault(nombre_parte, []).append(len(partes))
            partes.append({
                "kv": inf.get("voltaje_kv"),
                "s": 1 if inf.get("tipo") == "Subterránea" else 0,
                "c": [[r(lon, 5), r(lat, 5)] for lat, lon in cadena],
            })

    circuitos = []
    for nombre, g in datos_lineas.items():
        inf = info_circuitos.get(nombre) or info_lineas.get(nombre, {})
        idx = [i for p in partes_circuito.get(nombre, [nombre]) for i in indice_parte.get(p, [])]
        circuitos.append({
            "n": nombre,
            "kv": inf.get("voltaje_kv"),
            "tipo": inf.get("tipo"),
            "se": list(extremos.get(nombre, (None, None))),
            "partes": idx,
            # [lon, lat, progresiva_m, nombre_torre]  ('' = vértice sin torre)
            "pts": [[r(lo), r(la), round(float(d), 1), t]
                    for lo, la, d, t in zip(g["Longitud"], g["Latitud"], g["Distancia_m"], g["Torre"])],
        })

    ses = []
    for nombre, se in subestaciones.items():
        if se.get("lat") is None or pd.isna(se.get("lat")):
            continue
        ses.append({
            "n": nombre,
            "kv": se.get("voltaje_kv"),
            "lon": r(se["lon"]), "lat": r(se["lat"]),
            "pol": [[r(lon), r(lat)] for lat, lon in (se.get("poligono") or [])],
        })

    cp = pd.read_csv("centros_poblados_rurales.csv", dtype={"ubigeo": str})
    centros = [[row.centro_poblado, row.distrito, row.provincia, row.departamento, r(row.lon), r(row.lat)]
               for row in cp.itertuples()]

    with open("vias_inei.json", encoding="utf-8") as f:
        vias = json.load(f)
    with open("rios_acequias_inei.json", encoding="utf-8") as f:
        rios = json.load(f)

    salida = {
        "generado": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
        "circuitos": circuitos,
        "partes": partes,
        "subestaciones": ses,
        "centros_poblados": centros,
        "vias": vias,
        "rios": rios,
    }
    destino = RAIZ / "escritorio" / "web" / "datos.json"
    destino.parent.mkdir(parents=True, exist_ok=True)
    with open(destino, "w", encoding="utf-8") as f:
        json.dump(salida, f, ensure_ascii=False, separators=(",", ":"))
    print(f"{destino}: {destino.stat().st_size / 1e6:.1f} MB · {len(circuitos)} circuitos · "
          f"{len(partes)} trazos · {len(ses)} SE · {len(centros)} CP · {len(vias)} vías · {len(rios)} ríos")


if __name__ == "__main__":
    main()
