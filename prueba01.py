import re
import io
import base64
from pathlib import Path

import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
import numpy as np
import requests

# =========================================================
# 0. COLORES DE MARCA CONELSUR
# =========================================================
AZUL_CONELSUR = "#0B3088"
VERDE_CONELSUR = "#00A651"
GRIS_CLARO = "#F5F7FA"

COLORES_TIPO = {
    "Poblado": "#FF8C00",
    "Carretera": "#696969",
    "Rio": "#1E90FF",
    "Cultivo": "#6B8E23",
    "Pastizal": "#9ACD32",
    "Eriazo": "#A0522D",
    "Bosque": "#2E7D32",
    "Mineria": "#222222",
    "Parque": "#228B22",
    "Telecom": "#8A2BE2",
    "Otro": "#808080",
}

st.set_page_config(
    layout="wide",
    page_title="Sistema de Localización de Fallas - SEIN",
    page_icon="⚡",
)

# =========================================================
# 1. ESTILOS DE MARCA (CSS) — el tema base (colores, fuente)
#    se fija en .streamlit/config.toml para los widgets nativos;
#    aquí se profundiza con tipografía corporativa (Google Fonts)
#    y color consistente en pestañas, checkboxes, sliders, etc.
# =========================================================
VERDE_CONELSUR_OSCURO = "#00803D"
AZUL_CONELSUR_CLARO = "#E9EEFA"

st.markdown(
    f"""
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@500;600;700&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">

    <style>
        html, body, [class*="st-"], .stApp, p, div, span, li, label, input, textarea, select {{
            font-family: 'Inter', 'Segoe UI', Arial, sans-serif;
        }}
        h1, h2, h3, h4, h5, h6,
        .conelsur-header h1,
        div[data-testid="stMetricValue"] {{
            font-family: 'Poppins', 'Segoe UI', Arial, sans-serif;
            font-weight: 600;
        }}

        .stApp {{
            background-color: {GRIS_CLARO};
        }}

        /* ---- Encabezado ---- */
        .conelsur-header {{
            background-color: #FFFFFF;
            padding: 16px 24px;
            border-bottom: 4px solid {VERDE_CONELSUR};
            display: flex;
            align-items: center;
            gap: 20px;
            margin-bottom: 24px;
        }}
        .conelsur-header img {{ height: 48px; }}
        .conelsur-header h1 {{
            color: {AZUL_CONELSUR};
            font-size: 26px;
            margin: 0;
        }}
        .conelsur-header p {{
            color: #555555;
            margin: 0;
            font-size: 14px;
            font-family: 'Inter', sans-serif;
        }}

        h2, h3 {{ color: {AZUL_CONELSUR}; }}

        /* ---- Panel lateral tipo tarjeta ---- */
        [data-testid="column"]:first-of-type {{
            background-color: #FFFFFF;
            border-radius: 12px;
            padding: 18px 20px 24px 20px;
            box-shadow: 0 2px 10px rgba(11, 48, 136, 0.08);
        }}

        /* ---- Botones ---- */
        .stButton > button, .stDownloadButton > button {{
            background-color: {AZUL_CONELSUR};
            color: white;
            border-radius: 6px;
            border: none;
            font-weight: 500;
        }}
        .stButton > button:hover, .stDownloadButton > button:hover {{
            background-color: {VERDE_CONELSUR};
            color: white;
        }}

        /* ---- Pestañas (st.tabs) ---- */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 4px;
            border-bottom: 2px solid {AZUL_CONELSUR_CLARO};
        }}
        .stTabs [data-baseweb="tab"] {{
            color: {AZUL_CONELSUR};
            font-weight: 500;
            padding: 8px 14px;
        }}
        .stTabs [aria-selected="true"] {{
            color: {VERDE_CONELSUR_OSCURO} !important;
            border-bottom: 3px solid {VERDE_CONELSUR} !important;
            font-weight: 600;
        }}

        /* ---- Checkboxes, sliders, radios con acento de marca ---- */
        input[type="checkbox"] {{ accent-color: {VERDE_CONELSUR}; }}
        div[data-baseweb="slider"] div[role="slider"] {{
            background-color: {VERDE_CONELSUR} !important;
            border-color: {VERDE_CONELSUR} !important;
        }}
        div[data-baseweb="slider"] > div > div {{
            background: {VERDE_CONELSUR} !important;
        }}

        /* ---- Inputs: borde azul al enfocar ---- */
        div[data-baseweb="input"]:focus-within,
        div[data-baseweb="select"]:focus-within,
        div[data-baseweb="textarea"]:focus-within {{
            border-color: {AZUL_CONELSUR} !important;
            box-shadow: 0 0 0 1px {AZUL_CONELSUR} !important;
        }}

        /* ---- Alertas con acento de marca a la izquierda ---- */
        div[data-testid="stAlertContainer"] {{
            border-left: 6px solid {VERDE_CONELSUR};
            border-radius: 6px;
        }}

        /* ---- Expanders y subheaders con tono de marca ---- */
        details > summary {{
            color: {AZUL_CONELSUR};
            font-weight: 600;
        }}

        /* ---- Leyenda de restricciones ---- */
        .leyenda-item {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            margin-right: 14px;
            font-size: 13px;
            color: #222222;
            font-family: 'Inter', sans-serif;
        }}
        .leyenda-swatch {{
            width: 14px;
            height: 14px;
            border-radius: 3px;
            display: inline-block;
        }}

        /* ---- Pie de página de marca ---- */
        .conelsur-footer {{
            margin-top: 28px;
            padding: 10px 0;
            text-align: center;
            font-size: 12px;
            color: #8A8A8A;
            border-top: 1px solid #E0E0E0;
            font-family: 'Inter', sans-serif;
        }}
    </style>
    """,
    unsafe_allow_html=True,
)

# =========================================================
# 2. ENCABEZADO CON LOGO
# =========================================================
def cargar_logo_base64(ruta: str) -> str:
    try:
        return base64.b64encode(Path(ruta).read_bytes()).decode()
    except FileNotFoundError:
        return ""

logo_b64 = cargar_logo_base64("conelsur_logo.jpg")

if logo_b64:
    st.markdown(
        f"""
        <div class="conelsur-header">
            <img src="data:image/jpeg;base64,{logo_b64}" alt="Conelsur">
            <div>
                <h1>Centro de Control: Localizador de Fallas Georreferenciado</h1>
                <p>Herramienta analítica para la optimización de tiempos de respuesta post-falla</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    st.title("⚡ Centro de Control: Localizador de Fallas Georreferenciado")
    st.markdown("Herramienta analítica para la optimización de tiempos de respuesta post-falla.")
    st.divider()

# =========================================================
# 3. FUNCIONES AUXILIARES
# =========================================================
def distancia_m(lat1, lon1, lat2, lon2):
    R = 6371000
    lat1, lon1, lat2, lon2 = map(np.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return 2 * R * np.arcsin(np.sqrt(a))


def punto_en_distancia(df_linea, dist_m):
    """Interpola lat/lon a lo largo de una línea dada una distancia acumulada en metros."""
    df_antes = df_linea[df_linea["Distancia_m"] <= dist_m]
    df_despues = df_linea[df_linea["Distancia_m"] > dist_m]

    if df_antes.empty:
        fila = df_linea.iloc[0]
        return fila["Latitud"], fila["Longitud"]
    if df_despues.empty:
        fila = df_linea.iloc[-1]
        return fila["Latitud"], fila["Longitud"]

    t_ant = df_antes.iloc[-1]
    t_pos = df_despues.iloc[0]

    if t_pos["Distancia_m"] != t_ant["Distancia_m"]:
        peso = (dist_m - t_ant["Distancia_m"]) / (t_pos["Distancia_m"] - t_ant["Distancia_m"])
    else:
        peso = 0

    lat = t_ant["Latitud"] + peso * (t_pos["Latitud"] - t_ant["Latitud"])
    lon = t_ant["Longitud"] + peso * (t_pos["Longitud"] - t_ant["Longitud"])
    return lat, lon


PATRON_FILA_EMERGENCIAS = re.compile(
    r'<th scope="row"[^>]*>\d+</th>\s*'
    r'<td[^>]*><span>(\d+)</span></td>\s*'
    r'<td[^>]*><span>([^<]+)</span></td>\s*'
    r'<td[^>]*emergency-direction"><p[^>]*>(.*?)</p></td>\s*'
    r'<td[^>]*><i[^>]*></i><span>(.*?)</span></td>\s*'
    r'<td[^>]*>\s*<span class="badge[^"]*"><i[^>]*></i><span>([^<]+)</span></span>\s*</td>\s*'
    r'<td[^>]*>\s*<ul[^>]*>(.*?)</ul>\s*</td>',
    re.DOTALL,
)


def parsear_lista_emergencias(html):
    """Extrae todas las filas de la tabla de '/24horas' (varias emergencias a la vez)."""
    filas = PATRON_FILA_EMERGENCIAS.findall(html)
    registros = []
    for parte, fecha_hora, direccion, tipo, estado, maquinas_html in filas:
        m = re.search(r"\((-?\d+\.?\d*),(-?\d+\.?\d*)\)", direccion)
        lat = float(m.group(1)) if m and (m.group(1) != "0" or m.group(2) != "0") else None
        lon = float(m.group(2)) if m and (m.group(1) != "0" or m.group(2) != "0") else None
        maquinas = re.findall(r"<span>([^<]+)</span>", maquinas_html)
        registros.append(
            {
                "parte": parte,
                "fecha_hora": fecha_hora.strip(),
                "direccion": direccion.strip(),
                "tipo": tipo.strip(),
                "estado": estado.strip(),
                "maquinas": ", ".join(maquinas),
                "lat": lat,
                "lon": lon,
            }
        )
    return pd.DataFrame(registros)


def punto_mas_cercano_en_linea(df_linea, lat, lon):
    """Devuelve (distancia_m, fila) de la torre más cercana de la línea a un punto dado."""
    distancias = distancia_m(df_linea["Latitud"].values, df_linea["Longitud"].values, lat, lon)
    idx = distancias.argmin()
    return distancias[idx], df_linea.iloc[idx]


def codigo_de_nombre_linea(nombre_linea):
    m = re.search(r"L-(\d+)", nombre_linea)
    return int(m.group(1)) if m else None


def codigos_en_texto(texto):
    return set(int(n) for n in re.findall(r"\d+", str(texto)))


def parsear_pagina_bomberos(html):
    """Extrae la emergencia (lat/lon, tipo, dirección, máquinas) del código fuente
    de una página 'Ubicación de la emergencia' de Bomberos Perú (sgonorte...gob.pe).
    No se consulta la página automáticamente (su robots.txt lo impide); el usuario
    pega el código fuente que ya tiene abierto en su navegador (Ctrl+U)."""
    m = re.search(r"L\.marker\(\[(-?\d+\.\d+),\s*(-?\d+\.\d+)\],\s*\{\s*icon:\s*emergencyIcon", html)
    if not m:
        return None

    resultado = {"lat": float(m.group(1)), "lon": float(m.group(2))}

    popup_match = re.search(
        r"icon:\s*emergencyIcon\s*\}\)\.addTo\(map\)\.bindPopup\('(.*?)'\)\.openPopup\(\)",
        html, re.DOTALL,
    )
    popup_html = popup_match.group(1) if popup_match else ""

    def extraer_campo(etiqueta):
        patt = re.search(
            rf'{etiqueta}.*?</tr>\s*<tr><td colspan="2">(.*?)</td></tr>',
            popup_html, re.DOTALL,
        )
        return patt.group(1).strip() if patt else None

    resultado["tipo"] = extraer_campo("TIPO DE EMERGENCIA:") or "No especificado"
    resultado["direccion"] = extraer_campo("DIRECCION:") or "No especificado"
    resultado["maquinas"] = extraer_campo("MAQUINAS:") or "No especificado"
    return resultado


@st.cache_data(ttl=600, show_spinner=False)
def obtener_sismos_usgs(min_lat, max_lat, min_lon, max_lon, dias=30, mag_min=3.5):
    """Sismos recientes vía el catálogo público de USGS (incluye Perú, sin clave)."""
    url = "https://earthquake.usgs.gov/fdsnws/event/1/query"
    params = {
        "format": "geojson",
        "starttime": (pd.Timestamp.utcnow() - pd.Timedelta(days=dias)).strftime("%Y-%m-%d"),
        "minlatitude": min_lat,
        "maxlatitude": max_lat,
        "minlongitude": min_lon,
        "maxlongitude": max_lon,
        "minmagnitude": mag_min,
    }
    r = requests.get(url, params=params, timeout=15)
    r.raise_for_status()
    data = r.json()

    registros = []
    for feat in data.get("features", []):
        coords = feat["geometry"]["coordinates"]
        props = feat["properties"]
        registros.append(
            {
                "lat": coords[1],
                "lon": coords[0],
                "profundidad_km": coords[2],
                "magnitud": props.get("mag"),
                "lugar": props.get("place"),
                "tiempo": pd.to_datetime(props.get("time"), unit="ms", utc=True),
            }
        )
    return pd.DataFrame(registros)


@st.cache_data(ttl=600, show_spinner=False)
def obtener_incendios_firms(map_key, min_lat, max_lat, min_lon, max_lon, dias=1):
    """Focos de calor activos vía NASA FIRMS (requiere MAP_KEY gratuita)."""
    bbox = f"{min_lon},{min_lat},{max_lon},{max_lat}"
    url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{map_key}/VIIRS_SNPP_NRT/{bbox}/{dias}"
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))
    if "latitude" not in df.columns:
        # FIRMS devuelve un CSV de una sola columna con el mensaje de error (p. ej. clave inválida)
        raise ValueError(df.to_string(index=False) if not df.empty else "Respuesta vacía de FIRMS")
    return df


# =========================================================
# 4. CARGAR DATOS
# =========================================================
df = pd.read_excel("consolidado_total.xlsx")
df.columns = df.columns.str.strip()
df["Latitud"] = pd.to_numeric(df["Latitud"], errors="coerce")
df["Longitud"] = pd.to_numeric(df["Longitud"], errors="coerce")
df["Torre"] = df["Torre"].astype(str).str.strip()

datos_lineas = {}
for linea, grupo in df.groupby("Linea"):
    grupo = grupo.reset_index(drop=True)
    grupo["Distancia_m"] = 0.0
    for i in range(1, len(grupo)):
        d = distancia_m(
            grupo.loc[i - 1, "Latitud"], grupo.loc[i - 1, "Longitud"],
            grupo.loc[i, "Latitud"], grupo.loc[i, "Longitud"],
        )
        grupo.loc[i, "Distancia_m"] = grupo.loc[i - 1, "Distancia_m"] + d
    datos_lineas[linea] = grupo

# Restricciones (zonas pobladas, cruces de carretera/río, etc.)
try:
    df_rest = pd.read_csv("restricciones_conelsur.csv", encoding="utf-8-sig")
    df_rest["Tipo"] = df_rest["Tipo"].astype(str).str.strip()
    restricciones_disponibles = True
except FileNotFoundError:
    df_rest = pd.DataFrame()
    restricciones_disponibles = False

# =========================================================
# 5. INTERFAZ — CONTROLES
# =========================================================
col_control, col_mapa = st.columns([1, 3])

with col_control:
    st.header("📋 Datos del Evento")

    linea_seleccionada = st.selectbox("Seleccione la Línea:", list(datos_lineas.keys()))
    df_linea = datos_lineas[linea_seleccionada]

    distancia_max_km = df_linea["Distancia_m"].max() / 1000

    distancia_falla_km = st.number_input(
        f"Distancia de falla (0 a {distancia_max_km:.2f} km):",
        min_value=0.0,
        max_value=float(distancia_max_km),
        value=distancia_max_km / 2,
        step=0.1,
    )
    distancia_falla_m = distancia_falla_km * 1000

    if restricciones_disponibles:
        mostrar_restricciones = st.checkbox("Mostrar restricciones en el mapa", value=True)
    else:
        mostrar_restricciones = False
        st.warning("No se encontró restricciones_conelsur.csv en el repositorio.")

    # ---------------------------------------------------
    # Ubicación de la falla
    # ---------------------------------------------------
    lat_falla, lon_falla = punto_en_distancia(df_linea, distancia_falla_m)

    df_antes = df_linea[df_linea["Distancia_m"] <= distancia_falla_m]
    df_despues = df_linea[df_linea["Distancia_m"] > distancia_falla_m]
    if df_despues.empty:
        t_anterior, t_posterior = df_antes.iloc[-2], df_antes.iloc[-1]
    else:
        t_anterior = df_antes.iloc[-1] if not df_antes.empty else df_linea.iloc[0]
        t_posterior = df_despues.iloc[0]

    st.success("📍 Ubicación estimada")
    st.write(f"Coordenadas: {lat_falla:.5f}, {lon_falla:.5f}")

    if t_anterior["Torre"] == t_posterior["Torre"]:
        st.write(f"Falla exacta en torre: {t_anterior['Torre']}")
    else:
        st.write(f"Entre: {t_anterior['Torre']} y {t_posterior['Torre']}")

    # ---------------------------------------------------
    # Restricciones de la línea seleccionada
    # ---------------------------------------------------
    df_rest_linea = pd.DataFrame()
    if restricciones_disponibles:
        codigo_linea_actual = codigo_de_nombre_linea(linea_seleccionada)
        mask = df_rest["Codigo_Linea"].apply(lambda s: codigo_linea_actual in codigos_en_texto(s))
        df_rest_linea = df_rest[mask].copy()

        if not df_rest_linea.empty:
            puntos_ini = df_rest_linea["Acumulado_Inicio_m"].apply(lambda d: punto_en_distancia(df_linea, d))
            puntos_fin = df_rest_linea["Acumulado_Fin_m"].apply(lambda d: punto_en_distancia(df_linea, d))
            df_rest_linea["lat_ini"] = puntos_ini.apply(lambda p: p[0])
            df_rest_linea["lon_ini"] = puntos_ini.apply(lambda p: p[1])
            df_rest_linea["lat_fin"] = puntos_fin.apply(lambda p: p[0])
            df_rest_linea["lon_fin"] = puntos_fin.apply(lambda p: p[1])

        # --- Chequeo automático: ¿el punto de falla cae en una restricción? ---
        st.subheader("🔎 Verificación en el punto de falla")
        margen_m = 25  # tolerancia de interpolación
        en_rango = df_rest_linea[
            (df_rest_linea["Acumulado_Inicio_m"] - margen_m <= distancia_falla_m)
            & (df_rest_linea["Acumulado_Fin_m"] + margen_m >= distancia_falla_m)
        ]

        if en_rango.empty:
            st.info("No se registran restricciones conocidas en este punto.")
        else:
            for _, r in en_rango.iterrows():
                detalle = (
                    f"**{r['Tipo']}** — {r['Zona_Geografica']}  \n"
                    f"{r['Texto_Original']}  \n"
                    f"Distancia horizontal al eje: {r['Distancia_Horizontal_m']:.0f} m · Fuente: {r['Fuente']}"
                )
                if r["Tipo"] == "Poblado" and r["Distancia_Horizontal_m"] < 100:
                    st.error(f"⚠️ Zona poblada cercana\n\n{detalle}")
                elif r["Fuente"] == "Cruce":
                    st.warning(f"🚧 Cruce con {r['Tipo'].lower()}\n\n{detalle}")
                else:
                    st.warning(detalle)

    # ---------------------------------------------------
    # Capas opcionales: sismos (USGS) e incendios (NASA FIRMS)
    # ---------------------------------------------------
    st.subheader("🛰️ Capas adicionales (opcional)")

    margen_grados = 0.5  # ~55 km de contexto alrededor de la línea
    min_lat_bbox = df_linea["Latitud"].min() - margen_grados
    max_lat_bbox = df_linea["Latitud"].max() + margen_grados
    min_lon_bbox = df_linea["Longitud"].min() - margen_grados
    max_lon_bbox = df_linea["Longitud"].max() + margen_grados

    mostrar_sismos = st.checkbox("Mostrar sismos recientes (USGS)", value=False)
    df_sismos = pd.DataFrame()
    if mostrar_sismos:
        dias_sismos = st.slider("Sismos: días hacia atrás", 1, 60, 30)
        mag_min = st.slider("Sismos: magnitud mínima", 2.5, 6.0, 3.5, step=0.1)
        try:
            df_sismos = obtener_sismos_usgs(
                min_lat_bbox, max_lat_bbox, min_lon_bbox, max_lon_bbox, dias_sismos, mag_min
            )
            if df_sismos.empty:
                st.info("Sin sismos registrados con esos filtros en el área de la línea.")
        except Exception as e:
            st.warning(f"No se pudo consultar el servicio de sismos (USGS): {e}")

    mostrar_incendios = st.checkbox("Mostrar incendios activos (NASA FIRMS)", value=False)
    df_incendios = pd.DataFrame()
    if mostrar_incendios:
        firms_key = st.text_input(
            "FIRMS MAP_KEY (gratis en firms.modaps.eosdis.nasa.gov/api/map_key)",
            type="password",
        )
        dias_incendios = st.slider("Incendios: días hacia atrás", 1, 7, 1)
        if firms_key:
            try:
                df_incendios = obtener_incendios_firms(
                    firms_key, min_lat_bbox, max_lat_bbox, min_lon_bbox, max_lon_bbox, dias_incendios
                )
                if df_incendios.empty:
                    st.info("Sin focos de calor detectados en el área de la línea.")
            except Exception as e:
                st.warning(f"No se pudo consultar FIRMS: {e}")
        else:
            st.caption("Ingresa tu MAP_KEY para activar esta capa.")

    # ---------------------------------------------------
    # Emergencias de Bomberos Perú (pegadas manualmente)
    # ---------------------------------------------------
    st.subheader("🚒 Emergencias de Bomberos (opcional)")
    st.caption(
        "El sitio de Bomberos bloquea el acceso automático. Copia el código fuente "
        "(clic derecho → 'Ver código fuente de la página', o Ctrl+U) y pégalo abajo."
    )

    tab_lista, tab_individual = st.tabs(["📋 Lista completa (/24horas)", "🔥 Una emergencia (numparte)"])

    emergencias_activas = pd.DataFrame()
    with tab_lista:
        st.caption(
            "Pega el código fuente de https://sgonorte.bomberosperu.gob.pe/24horas "
            "(la página con la tabla de emergencias de las últimas 24 horas)."
        )
        html_lista = st.text_area("Código fuente de la lista de emergencias", height=100, key="html_lista")
        if html_lista.strip():
            emergencias_activas = parsear_lista_emergencias(html_lista)
            if emergencias_activas.empty:
                st.warning("No se reconoció ninguna fila. Verifica que sea el código de la página /24horas.")
            else:
                solo_atendiendo = st.checkbox("Mostrar solo las que dicen ATENDIENDO", value=True)
                df_mostrar = emergencias_activas
                if solo_atendiendo:
                    df_mostrar = emergencias_activas[emergencias_activas["estado"] == "ATENDIENDO"]
                st.success(f"{len(df_mostrar)} emergencia(s) reconocida(s) (de {len(emergencias_activas)} en la tabla)")

                con_coords = df_mostrar.dropna(subset=["lat", "lon"])
                cercanas = []
                for _, r in con_coords.iterrows():
                    dist_m, torre = punto_mas_cercano_en_linea(df_linea, r["lat"], r["lon"])
                    if dist_m < 500:
                        cercanas.append((r, dist_m, torre))

                if cercanas:
                    st.error(f"⚠️ {len(cercanas)} emergencia(s) a menos de 500 m de **{linea_seleccionada}**")
                    for r, dist_m, torre in cercanas:
                        st.write(
                            f"**Parte {r['parte']}** — {r['tipo']}  \n"
                            f"{r['direccion']}  \n"
                            f"A {dist_m:.0f} m de la torre {torre['Torre']} · {r['estado']}"
                        )
                else:
                    st.info("Ninguna emergencia de la lista cae cerca de la línea seleccionada.")

                emergencias_activas = df_mostrar  # lo que se dibuja en el mapa

    emergencia = None
    with tab_individual:
        html_bomberos = st.text_area("Código fuente de la página de la emergencia", height=100, key="html_individual")
        if html_bomberos.strip():
            emergencia = parsear_pagina_bomberos(html_bomberos)
            if emergencia is None:
                st.warning("No se reconoció una emergencia en el código pegado. Verifica que sea la página correcta.")
            else:
                st.error(f"🔥 {emergencia['tipo']}")
                st.write(f"**Dirección:** {emergencia['direccion']}")
                st.write(f"**Máquinas:** {emergencia['maquinas']}")

                dist_torre_m, torre_cercana = punto_mas_cercano_en_linea(
                    df_linea, emergencia["lat"], emergencia["lon"]
                )
                if dist_torre_m < 500:
                    st.error(
                        f"⚠️ A solo {dist_torre_m:.0f} m de la torre {torre_cercana['Torre']} "
                        f"de **{linea_seleccionada}**"
                    )
                else:
                    st.info(
                        f"A {dist_torre_m/1000:.2f} km de la torre más cercana "
                        f"({torre_cercana['Torre']}) de la línea seleccionada"
                    )

# =========================================================
# 6. MAPA
# =========================================================
with col_mapa:
    m = folium.Map(location=[lat_falla, lon_falla], zoom_start=11)

    coord_linea = list(zip(df_linea["Latitud"], df_linea["Longitud"]))
    folium.PolyLine(coord_linea, color=AZUL_CONELSUR, weight=4).add_to(m)

    for _, fila in df_linea.iterrows():
        folium.CircleMarker(
            location=[fila["Latitud"], fila["Longitud"]],
            radius=4,
            color=AZUL_CONELSUR,
            fill=True,
            fill_color="white",
            popup=f"{fila['Torre']} (Km {fila['Distancia_m']/1000:.2f})",
        ).add_to(m)

    if mostrar_restricciones and not df_rest_linea.empty:
        capa_restricciones = folium.FeatureGroup(name="Restricciones")
        for _, r in df_rest_linea.iterrows():
            color = COLORES_TIPO.get(r["Tipo"], "#808080")
            popup_html = (
                f"<b>{r['Tipo']}</b> ({r['Fuente']})<br>"
                f"{r['Zona_Geografica']}<br>"
                f"{r['Texto_Original']}<br>"
                f"D. horizontal: {r['Distancia_Horizontal_m']:.0f} m"
            )
            if r["Acumulado_Inicio_m"] == r["Acumulado_Fin_m"]:
                folium.CircleMarker(
                    location=[r["lat_ini"], r["lon_ini"]],
                    radius=6,
                    color=color,
                    fill=True,
                    fill_color=color,
                    fill_opacity=0.8,
                    popup=popup_html,
                ).add_to(capa_restricciones)
            else:
                folium.PolyLine(
                    [[r["lat_ini"], r["lon_ini"]], [r["lat_fin"], r["lon_fin"]]],
                    color=color,
                    weight=6,
                    opacity=0.65,
                    popup=popup_html,
                ).add_to(capa_restricciones)
        capa_restricciones.add_to(m)

    if mostrar_sismos and not df_sismos.empty:
        capa_sismos = folium.FeatureGroup(name="Sismos recientes (USGS)")
        for _, s in df_sismos.iterrows():
            if s["magnitud"] < 4.5:
                color_sismo = "#FFD700"
            elif s["magnitud"] < 6.0:
                color_sismo = "#FF8C00"
            else:
                color_sismo = "#D32F2F"
            folium.CircleMarker(
                location=[s["lat"], s["lon"]],
                radius=3 + s["magnitud"] * 1.5,
                color=color_sismo,
                fill=True,
                fill_color=color_sismo,
                fill_opacity=0.6,
                popup=(
                    f"<b>M{s['magnitud']:.1f}</b> — {s['lugar']}<br>"
                    f"Profundidad: {s['profundidad_km']:.0f} km<br>"
                    f"{s['tiempo'].strftime('%Y-%m-%d %H:%M UTC')}"
                ),
            ).add_to(capa_sismos)
        capa_sismos.add_to(m)

    if mostrar_incendios and not df_incendios.empty:
        capa_incendios = folium.FeatureGroup(name="Incendios activos (FIRMS)")
        for _, f in df_incendios.iterrows():
            folium.CircleMarker(
                location=[f["latitude"], f["longitude"]],
                radius=5,
                color="#FF4500",
                fill=True,
                fill_color="#FF4500",
                fill_opacity=0.7,
                popup=(
                    "🔥 Foco de calor<br>"
                    f"Fecha: {f.get('acq_date', '?')} {f.get('acq_time', '')}<br>"
                    f"FRP: {f.get('frp', '?')} MW · Confianza: {f.get('confidence', '?')}"
                ),
            ).add_to(capa_incendios)
        capa_incendios.add_to(m)

    if emergencia is not None:
        capa_emergencia = folium.FeatureGroup(name="Emergencia Bomberos")
        folium.Marker(
            location=[emergencia["lat"], emergencia["lon"]],
            popup=(
                f"<b>{emergencia['tipo']}</b><br>"
                f"{emergencia['direccion']}<br>"
                f"Máquinas: {emergencia['maquinas']}"
            ),
            icon=folium.Icon(color="red", icon="fire", prefix="fa"),
        ).add_to(capa_emergencia)
        capa_emergencia.add_to(m)

    if not emergencias_activas.empty:
        capa_lista = folium.FeatureGroup(name="Emergencias activas (lista)")
        for _, r in emergencias_activas.dropna(subset=["lat", "lon"]).iterrows():
            color_estado = "red" if r["estado"] == "ATENDIENDO" else "gray"
            folium.Marker(
                location=[r["lat"], r["lon"]],
                popup=(
                    f"<b>Parte {r['parte']}</b> ({r['estado']})<br>"
                    f"{r['tipo']}<br>"
                    f"{r['direccion']}<br>"
                    f"{r['fecha_hora']}<br>"
                    f"Máquinas: {r['maquinas']}"
                ),
                icon=folium.Icon(color=color_estado, icon="fire", prefix="fa"),
            ).add_to(capa_lista)
        capa_lista.add_to(m)

    hay_capas_opcionales = (
        (mostrar_restricciones and not df_rest_linea.empty)
        or (mostrar_sismos and not df_sismos.empty)
        or (mostrar_incendios and not df_incendios.empty)
        or (emergencia is not None)
        or (not emergencias_activas.empty)
    )
    if hay_capas_opcionales:
        folium.LayerControl(collapsed=False).add_to(m)

    folium.Marker(
        location=[lat_falla, lon_falla],
        popup=f"Falla Km {distancia_falla_km:.2f}",
        icon=folium.Icon(color="green", icon="bolt", prefix="fa"),
    ).add_to(m)

    st_folium(m, width="100%", height=600)

    if mostrar_restricciones and not df_rest_linea.empty:
        tipos_presentes = sorted(df_rest_linea["Tipo"].unique())
        leyenda_html = "".join(
            f'<span class="leyenda-item"><span class="leyenda-swatch" '
            f'style="background-color:{COLORES_TIPO.get(t, "#808080")}"></span>{t}</span>'
            for t in tipos_presentes
        )
        st.markdown(leyenda_html, unsafe_allow_html=True)

st.markdown(
    '<div class="conelsur-footer">Cuerpo General de Bomberos Voluntarios del Perú — '
    'datos de referencia · CONELSUR — Centro de Control de Operaciones de Transmisión</div>',
    unsafe_allow_html=True,
)
