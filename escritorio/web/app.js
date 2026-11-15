"use strict";
/* Localizador de Fallas CONELSUR — versión de escritorio (todo se calcula en
   el navegador; el servidor local solo entrega archivos y hace de proxy). */

// ------------------------------------------------------------------ constantes
const COLORES_KV = { 220: "#E53935", 138: "#2E7D32", 69: "#F57C00", 60: "#1565C0", 50: "#1565C0" };
const COLOR_SIN_KV = "#AEB8D1";
const AZUL = "#0B3088";
const COLORES_HIDRO = { "Río": "#29B6F6", "Acequia": "#80DEEA" };
const COLORES_VIAS = { Asfaltada: "#212121", Afirmada: "#8D6E63", Carrozable: "#FFB300", Herradura: "#AB47BC" };
const NOMBRES_VIAS = {
  Asfaltada: "Carretera asfaltada", Afirmada: "Carretera afirmada",
  Carrozable: "Camino carrozable", Herradura: "Camino de herradura",
};
const DESCRIPCION_CLIMA = {
  0: "Despejado", 1: "Mayormente despejado", 2: "Parcialmente nublado", 3: "Nublado",
  45: "Niebla", 48: "Niebla con escarcha", 51: "Llovizna ligera", 53: "Llovizna moderada",
  55: "Llovizna intensa", 56: "Llovizna helada ligera", 57: "Llovizna helada intensa",
  61: "Lluvia ligera", 63: "Lluvia moderada", 65: "Lluvia intensa", 66: "Lluvia helada ligera",
  67: "Lluvia helada intensa", 71: "Nevada ligera", 73: "Nevada moderada", 75: "Nevada intensa",
  77: "Granos de nieve", 80: "Chubascos ligeros", 81: "Chubascos moderados", 82: "Chubascos violentos",
  85: "Chubascos de nieve ligeros", 86: "Chubascos de nieve intensos", 95: "Tormenta eléctrica",
  96: "Tormenta con granizo ligero", 99: "Tormenta con granizo fuerte",
};
const TORMENTA = new Set([95, 96, 99]);
const RAYO_SVG =
  '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="46" height="46">' +
  '<circle cx="32" cy="32" r="29" fill="#C62828" stroke="#FFFFFF" stroke-width="4"/>' +
  '<path d="M36 8 L17 36 L30 36 L26 56 L47 26 L34 26 Z" fill="#FFD600" stroke="#1A1A1A" ' +
  'stroke-width="2.5" stroke-linejoin="round"/></svg>';

// ------------------------------------------------------------------ estado
let D = null;                 // datos.json
let TOKEN = null;             // token de Mapbox (del servidor local)
let mapa = null;
let marcadorFalla = null;
let marcadoresSE = [];
const E = {
  idx: 0, desdeInicio: true, distM: 0, vista: "calle", oscuro: false,
  cpLinea: [], viasCaja: [], hidroCaja: [], incendios: [], climaLinea: [],
};
const $ = (id) => document.getElementById(id);

// ------------------------------------------------------------------ geometría
function haversine(lon1, lat1, lon2, lat2) {
  const R = 6371000, r = Math.PI / 180;
  const a = Math.sin((lat2 - lat1) * r / 2) ** 2 +
    Math.cos(lat1 * r) * Math.cos(lat2 * r) * Math.sin((lon2 - lon1) * r / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(a));
}

/** Distancia (m) de un punto a una polilínea [[lon,lat,(prog)],...] y progresiva
    en el punto más cercano (si la polilínea trae la 3a coordenada). */
function distAPolilinea(lon, lat, coords) {
  const kx = 111320 * Math.cos(lat * Math.PI / 180), ky = 110574;
  let mejor = Infinity, prog = null;
  for (let i = 0; i < coords.length - 1; i++) {
    const ax = (coords[i][0] - lon) * kx, ay = (coords[i][1] - lat) * ky;
    const bx = (coords[i + 1][0] - lon) * kx, by = (coords[i + 1][1] - lat) * ky;
    const vx = bx - ax, vy = by - ay, l2 = vx * vx + vy * vy;
    const t = l2 > 0 ? Math.max(0, Math.min(1, -(ax * vx + ay * vy) / l2)) : 0;
    const d = Math.hypot(ax + t * vx, ay + t * vy);
    if (d < mejor) {
      mejor = d;
      if (coords[i].length > 2) prog = coords[i][2] + t * (coords[i + 1][2] - coords[i][2]);
    }
  }
  return { d: mejor, prog };
}

function puntoEnDistancia(pts, d) {
  if (d <= pts[0][2]) return [pts[0][0], pts[0][1]];
  const n = pts.length;
  if (d >= pts[n - 1][2]) return [pts[n - 1][0], pts[n - 1][1]];
  let lo = 0, hi = n - 1;
  while (hi - lo > 1) { const m = (lo + hi) >> 1; if (pts[m][2] <= d) lo = m; else hi = m; }
  const a = pts[lo], b = pts[hi], w = b[2] > a[2] ? (d - a[2]) / (b[2] - a[2]) : 0;
  return [a[0] + w * (b[0] - a[0]), a[1] + w * (b[1] - a[1])];
}

function cajaDe(coords, margen = 0) {
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const c of coords) { x0 = Math.min(x0, c[0]); y0 = Math.min(y0, c[1]); x1 = Math.max(x1, c[0]); y1 = Math.max(y1, c[1]); }
  return [x0 - margen, y0 - margen, x1 + margen, y1 + margen];
}
const seCruzan = (a, b) => a[0] <= b[2] && a[2] >= b[0] && a[1] <= b[3] && a[3] >= b[1];

// ------------------------------------------------------------------ formato
const fmtKm = (m) => (m / 1000).toFixed(2);
const fmtDist = (m) => (m >= 1000 ? `${(m / 1000).toFixed(2)} km` : `${Math.round(m)} m`);
const norm = (s) => String(s).normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const filasDato = (filas) => filas.map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join("");
const circ = () => D.circuitos[E.idx];
const largo = (c = circ()) => c.pts[c.pts.length - 1][2];
const desdeInicioM = () => (E.desdeInicio ? E.distM : largo() - E.distM);
function etiquetasExtremos(c = circ()) {
  const nombradas = c.pts.filter((p) => p[3]);
  let a = c.se[0] || `Inicio de la línea (${nombradas.length ? nombradas[0][3] : "—"})`;
  let b = c.se[1] || `Fin de la línea (${nombradas.length ? nombradas[nombradas.length - 1][3] : "—"})`;
  if (a === b) b += " (extremo final)";
  return [a, b];
}
const extremoActual = () => etiquetasExtremos()[E.desdeInicio ? 0 : 1];

// ------------------------------------------------------------------ mapa base
function fuenteBase() {
  if (TOKEN) {
    const estilo = E.vista === "satelite" ? "satellite-streets-v12" : (E.oscuro ? "dark-v11" : "streets-v12");
    return {
      type: "raster", tileSize: 512, maxzoom: 20,
      tiles: [`https://api.mapbox.com/styles/v1/mapbox/${estilo}/tiles/512/{z}/{x}/{y}@2x?access_token=${TOKEN}`],
      attribution: "© Mapbox © OpenStreetMap",
    };
  }
  if (E.vista === "satelite") {
    return {
      type: "raster", tileSize: 256, maxzoom: 19,
      tiles: ["https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"],
      attribution: "Imágenes © Esri",
    };
  }
  const t = E.oscuro ? "dark_all" : "light_all";
  return {
    type: "raster", tileSize: 256, maxzoom: 20,
    tiles: ["a", "b", "c"].map((s) => `https://${s}.basemaps.cartocdn.com/${t}/{z}/{x}/{y}@2x.png`),
    attribution: "© OpenStreetMap © CARTO",
  };
}

function cambiarMapaBase() {
  if (!mapa.getStyle()) return;
  const antes = mapa.getStyle().layers.find((l) => l.id !== "fondo" && l.id !== "base");
  if (mapa.getLayer("base")) mapa.removeLayer("base");
  if (mapa.getSource("base")) mapa.removeSource("base");
  mapa.addSource("base", fuenteBase());
  mapa.addLayer({ id: "base", type: "raster", source: "base" }, antes ? antes.id : undefined);
  mapa.setPaintProperty("fondo", "background-color", E.oscuro ? "#0F141C" : "#E8ECF0");
}

const fc = (features) => ({ type: "FeatureCollection", features });
const linea = (coords, props) => ({ type: "Feature", properties: props, geometry: { type: "LineString", coordinates: coords } });
const punto = (coord, props) => ({ type: "Feature", properties: props, geometry: { type: "Point", coordinates: coord } });

function crearCapas() {
  const vacio = fc([]);
  for (const id of ["lineas", "sel", "portico", "torres", "se", "hidro", "vias", "cp", "incendios", "clima"]) {
    mapa.addSource(id, { type: "geojson", data: vacio });
  }
  mapa.addLayer({ id: "clima", type: "heatmap", source: "clima", layout: { visibility: "none" },
    paint: {
      "heatmap-weight": ["get", "peso"], "heatmap-intensity": 1.5, "heatmap-radius": 70,
      "heatmap-color": ["interpolate", ["linear"], ["heatmap-density"],
        0, "rgba(237,231,246,0)", 0.25, "rgba(203,178,227,0.5)", 0.5, "rgba(158,119,199,0.67)",
        0.75, "rgba(122,68,172,0.82)", 1, "rgba(74,20,134,1)"],
    } });
  mapa.addLayer({ id: "se-relleno", type: "fill", source: "se", layout: { visibility: "none" },
    paint: { "fill-color": "#111111", "fill-opacity": 0.43 } });
  mapa.addLayer({ id: "se-borde", type: "line", source: "se", layout: { visibility: "none" },
    paint: { "line-color": "#111111", "line-width": 1.5 } });
  mapa.addLayer({ id: "hidro", type: "line", source: "hidro", layout: { visibility: "none", "line-cap": "round" },
    paint: { "line-color": ["get", "color"], "line-width": ["get", "ancho"], "line-opacity": 0.9 } });
  mapa.addLayer({ id: "vias", type: "line", source: "vias", filter: ["!=", ["get", "t"], "Herradura"],
    layout: { visibility: "none", "line-cap": "round" },
    paint: { "line-color": ["get", "color"], "line-width": ["get", "ancho"], "line-opacity": 0.92 } });
  mapa.addLayer({ id: "vias-herradura", type: "line", source: "vias", filter: ["==", ["get", "t"], "Herradura"],
    layout: { visibility: "none" },
    paint: { "line-color": COLORES_VIAS.Herradura, "line-width": 2, "line-dasharray": [2, 2] } });
  mapa.addLayer({ id: "lineas", type: "line", source: "lineas", filter: ["==", ["get", "s"], 0],
    layout: { "line-cap": "round", "line-join": "round" },
    paint: { "line-color": ["get", "color"], "line-width": 2, "line-opacity": 0.8 } });
  mapa.addLayer({ id: "lineas-sub", type: "line", source: "lineas", filter: ["==", ["get", "s"], 1],
    paint: { "line-color": ["get", "color"], "line-width": 2, "line-dasharray": [2, 1.5] } });
  mapa.addLayer({ id: "sel", type: "line", source: "sel", layout: { "line-cap": "round", "line-join": "round" },
    paint: { "line-color": AZUL, "line-width": 4.5 } });
  mapa.addLayer({ id: "portico", type: "line", source: "portico",
    paint: { "line-color": AZUL, "line-width": 3, "line-dasharray": [1, 1] } });
  mapa.addLayer({ id: "torres", type: "circle", source: "torres",
    paint: { "circle-radius": ["interpolate", ["linear"], ["zoom"], 8, 2, 13, 4.5],
      "circle-color": AZUL, "circle-stroke-color": "#fff", "circle-stroke-width": 1 } });
  mapa.addLayer({ id: "cp", type: "circle", source: "cp", layout: { visibility: "none" },
    paint: { "circle-radius": 6, "circle-color": ["get", "color"], "circle-stroke-color": "#282828", "circle-stroke-width": 1 } });
  mapa.addLayer({ id: "incendios-halo", type: "circle", source: "incendios", layout: { visibility: "none" },
    filter: ["==", ["get", "atencion"], 1],
    paint: { "circle-radius": 16, "circle-color": "rgba(255,87,34,0.28)" } });
  mapa.addLayer({ id: "incendios", type: "circle", source: "incendios", layout: { visibility: "none" },
    paint: { "circle-radius": 7, "circle-color": ["get", "color"], "circle-stroke-color": "#fff", "circle-stroke-width": 1.5 } });

  // Trazos de todas las líneas (fijos)
  const nombresPorParte = {};
  D.circuitos.forEach((c) => c.partes.forEach((i) => (nombresPorParte[i] = (nombresPorParte[i] || []).concat(c.n))));
  mapa.getSource("lineas").setData(fc(D.partes.map((p, i) => linea(p.c, {
    color: COLORES_KV[p.kv] || COLOR_SIN_KV, s: p.s,
    nombre: (nombresPorParte[i] || ["Línea"]).slice(0, 2).join(" / "),
    info: [p.kv ? `${p.kv} kV` : null, p.s ? "Tramo subterráneo" : "Tramo aéreo"].filter(Boolean).join(" · "),
  }))));
  mapa.getSource("se").setData(fc(D.subestaciones.filter((s) => s.pol.length > 2).map((s) => ({
    type: "Feature", properties: { nombre: s.n, info: s.kv ? `${s.kv} kV` : "" },
    geometry: { type: "Polygon", coordinates: [s.pol.concat([s.pol[0]])] },
  }))));

  // Ventanas emergentes al pasar el mouse
  const popup = new maplibregl.Popup({ closeButton: false, closeOnClick: false, offset: 10, maxWidth: "320px" });
  const interactivas = ["torres", "cp", "incendios", "vias", "vias-herradura", "hidro", "sel", "lineas", "lineas-sub", "se-relleno"];
  mapa.on("mousemove", (ev) => {
    const capas = interactivas.filter((id) => mapa.getLayer(id) && mapa.getLayoutProperty(id, "visibility") !== "none");
    const f = mapa.queryRenderedFeatures(ev.point, { layers: capas })[0];
    mapa.getCanvas().style.cursor = f ? "pointer" : "";
    if (!f) { popup.remove(); return; }
    const p = f.properties;
    popup.setLngLat(ev.lngLat).setHTML(`<b>${esc(p.nombre)}</b>${p.info ? `<span class="det">${esc(p.info)}</span>` : ""}`).addTo(mapa);
  });
  mapa.on("mouseout", () => popup.remove());
}

// ------------------------------------------------------------------ línea seleccionada
function llenarSelector(filtro = "") {
  const sel = $("selLinea"), f = norm(filtro);
  sel.innerHTML = "";
  D.circuitos.forEach((c, i) => {
    if (f && !norm(c.n).includes(f)) return;
    const o = document.createElement("option");
    o.value = i; o.textContent = c.n; if (i === E.idx) o.selected = true;
    sel.appendChild(o);
  });
  if (sel.options.length && !Array.from(sel.options).some((o) => +o.value === E.idx)) {
    sel.selectedIndex = 0; seleccionarLinea(+sel.value);
  }
}

function seleccionarLinea(i) {
  E.idx = i;
  const c = circ(), L = largo(c);
  $("infoLinea").innerHTML = [c.kv ? `${c.kv} kV` : "Tensión no identificada", c.tipo]
    .filter(Boolean).map((t) => `<span class="chip">${esc(t)}</span>`).join("");
  const [a, b] = etiquetasExtremos(c);
  E.desdeInicio = true;
  $("extremos").innerHTML = [a, b].map((t, k) =>
    `<label><input type="radio" name="extremo" value="${k}" ${k === 0 ? "checked" : ""}> ${esc(t)}</label>`).join("");
  $("extremos").querySelectorAll("input").forEach((r) => r.addEventListener("change", () => {
    E.desdeInicio = r.value === "0"; actualizarFalla(); actualizarCapasDeLinea(false);
  }));
  $("numDist").max = (L / 1000).toFixed(2);
  $("rangoDist").max = Math.round(L);
  $("maxDist").textContent = `Máx. ${fmtKm(L)} km`;
  E.distM = L / 2;

  const nombradas = c.pts.filter((p) => p[3] && !p[3].startsWith("Pórtico"));
  $("kpiTorres").textContent = nombradas.length;
  $("kpiLongitud").innerHTML = `${(L / 1000).toFixed(2)}<small>km</small>`;
  $("kpiKv").innerHTML = c.kv ? `${c.kv}<small>kV</small>` : "—";

  const coords = c.pts.map((p) => [p[0], p[1]]);
  mapa.getSource("sel").setData(fc([linea(coords, { nombre: c.n, info: `Línea seleccionada${c.kv ? ` · ${c.kv} kV` : ""}` })]));
  const vanos = [];
  for (const k of [0, c.pts.length - 1]) {
    if (c.pts[k][3] && c.pts[k][3].startsWith("Pórtico") && c.pts.length > 1) {
      const v = c.pts[k === 0 ? 1 : k - 1];
      vanos.push(linea([[v[0], v[1]], [c.pts[k][0], c.pts[k][1]]], { nombre: "Vano de llegada", info: c.pts[k][3] }));
    }
  }
  mapa.getSource("portico").setData(fc(vanos));

  const caja = cajaDe(coords);
  mapa.fitBounds([[caja[0], caja[1]], [caja[2], caja[3]]], { padding: 60, duration: 600, maxZoom: 15 });

  // Capas que dependen de la zona de la línea
  const cajaCapas = cajaDe(coords, 0.05);
  E.viasCaja = D.vias.filter((v) => seCruzan(v.caja || (v.caja = cajaDe(v.p)), cajaCapas));
  E.hidroCaja = D.rios.filter((v) => seCruzan(v.caja || (v.caja = cajaDe(v.p)), cajaCapas));
  calcularCP();
  actualizarCapasDeLinea(true);
  sincronizarDistancia();
  actualizarFalla();
  if ($("chkClima").checked) cargarClimaLinea();
}

function actualizarCapasDeLinea() {
  const c = circ(), L = largo(c);
  mapa.getSource("torres").setData(fc(c.pts.filter((p) => p[3]).map((p) => punto([p[0], p[1]], {
    nombre: p[3].startsWith("Pórtico") ? p[3] : `Torre ${p[3]}`,
    info: `${fmtKm(E.desdeInicio ? p[2] : L - p[2])} km desde ${extremoActual()}`,
  }))));
  dibujarVias(); dibujarHidro(); dibujarCP(); dibujarIncendios();
}

// ------------------------------------------------------------------ falla
function sincronizarDistancia() {
  $("numDist").value = fmtKm(E.distM);
  $("rangoDist").value = Math.round(E.distM);
}

function actualizarFalla() {
  const c = circ(), dI = desdeInicioM();
  const [lon, lat] = puntoEnDistancia(c.pts, dI);
  E.falla = [lon, lat];

  // Torres (con nombre) que encierran la falla
  const nom = c.pts.filter((p) => p[3]);
  let ant = nom[0], pos = nom[nom.length - 1];
  for (let k = 0; k < nom.length; k++) {
    if (nom[k][2] <= dI) ant = nom[k];
    if (nom[k][2] > dI) { pos = nom[k]; break; }
  }
  const tramo = ant === pos || !pos ? `Torre ${ant[3]}` : `${ant[3]} – ${pos[3]}`;
  E.detalleTorres = tramo;
  E.torresFalla = { ant, pos };

  $("kpiFalla").innerHTML = `${fmtKm(E.distM)}<small>km</small>`;
  $("tarjUbicacion").innerHTML = filasDato([
    ["Medido desde", esc(extremoActual())],
    ["Progresiva", `${fmtKm(E.distM)} km`],
    ["Entre torres", esc(tramo)],
    ["Latitud", lat.toFixed(5)],
    ["Longitud", lon.toFixed(5)],
  ]);

  if (!marcadorFalla) {
    const el = document.createElement("div");
    el.className = "marcador-falla";
    el.innerHTML = `<div class="etiqueta-falla"></div><div class="rayo">${RAYO_SVG}</div>`;
    marcadorFalla = new maplibregl.Marker({ element: el, anchor: "bottom", offset: [0, 23] }).setLngLat([lon, lat]).addTo(mapa);
  }
  marcadorFalla.setLngLat([lon, lat]);
  marcadorFalla.getElement().querySelector(".etiqueta-falla").textContent = `FALLA · ${fmtKm(E.distM)} km`;

  actualizarCercanos();
  actualizarTablaCP();
  programarClimaFalla();
}

// ------------------------------------------------------------------ vías y ríos
function tiposViaActivos() {
  return new Set(Array.from(document.querySelectorAll("[data-via]")).filter((x) => x.checked).map((x) => x.dataset.via));
}
/** En modo oscuro (mapa de calle oscuro) el negro de la carretera asfaltada no se ve. */
const colorVia = (t) => (t === "Asfaltada" && E.oscuro && E.vista === "calle" ? "#ECEFF1" : COLORES_VIAS[t]);
function dibujarVias() {
  const on = $("chkVias").checked, tipos = tiposViaActivos();
  ["vias", "vias-herradura"].forEach((id) => mapa.setLayoutProperty(id, "visibility", on ? "visible" : "none"));
  mapa.getSource("vias").setData(fc(on ? E.viasCaja.filter((v) => tipos.has(v.t)).map((v) => linea(v.p, {
    t: v.t, nombre: NOMBRES_VIAS[v.t], info: "Fuente: INEI", color: colorVia(v.t),
    ancho: v.t === "Asfaltada" ? 4 : v.t === "Afirmada" ? 3 : 2,
  })) : []));
}
function dibujarHidro() {
  const on = $("chkRios").checked;
  mapa.setLayoutProperty("hidro", "visibility", on ? "visible" : "none");
  mapa.getSource("hidro").setData(fc(on ? E.hidroCaja.map((v) => linea(v.p, {
    nombre: v.n ? v.n.replace(/^Rio /, "Río ") : v.t, info: `${v.t} · Fuente: INEI`, color: COLORES_HIDRO[v.t], ancho: v.t === "Río" ? 3 : 2,
  })) : []));
}
function masCercano(lista) {
  let mejor = { d: Infinity, e: null };
  for (const e of lista) {
    const r = distAPolilinea(E.falla[0], E.falla[1], e.p);
    if (r.d < mejor.d) mejor = { d: r.d, e };
  }
  return mejor;
}
function actualizarCercanos() {
  const filas = [];
  if ($("chkVias").checked) {
    const tipos = tiposViaActivos();
    for (const t of Object.keys(NOMBRES_VIAS)) {
      if (!tipos.has(t)) continue;
      const m = masCercano(E.viasCaja.filter((v) => v.t === t));
      if (m.e && m.d <= 5000) filas.push([NOMBRES_VIAS[t], fmtDist(m.d)]);
    }
  }
  if ($("chkRios").checked) {
    for (const t of ["Río", "Acequia"]) {
      const m = masCercano(E.hidroCaja.filter((v) => v.t === t));
      if (m.e && m.d <= 5000) filas.push([t === "Río" && m.e.n ? esc(m.e.n.replace(/^Rio /, "Río ")) : t, fmtDist(m.d)]);
    }
  }
  $("bloqueCercano").hidden = !filas.length;
  $("tarjCercano").innerHTML = filasDato(filas);
}

// ------------------------------------------------------------------ centros poblados
function calcularCP() {
  const c = circ(), m = 0.06;
  const caja = cajaDe(c.pts, m);
  E.cpLinea = [];
  for (const [nombre, distrito, provincia, dpto, lon, lat] of D.centros_poblados) {
    if (lon < caja[0] || lon > caja[2] || lat < caja[1] || lat > caja[3]) continue;
    const r = distAPolilinea(lon, lat, c.pts);
    if (r.d <= 5000) E.cpLinea.push({ nombre, distrito, provincia, dpto, lon, lat, d: r.d, prog: r.prog });
  }
  E.cpLinea.sort((a, b) => a.d - b.d);
}
const radioCP = () => +$("selRadioCP").value;
function dibujarCP() {
  const on = $("chkCP").checked, L = largo();
  mapa.setLayoutProperty("cp", "visibility", on ? "visible" : "none");
  const lista = on ? E.cpLinea.filter((x) => x.d <= radioCP()) : [];
  mapa.getSource("cp").setData(fc(lista.map((x) => punto([x.lon, x.lat], {
    nombre: `Centro poblado ${x.nombre}`,
    info: `${x.distrito}, ${x.provincia} · ${Math.round(x.d)} m del eje · ${fmtKm(E.desdeInicio ? x.prog : L - x.prog)} km desde ${extremoActual()}`,
    color: x.d <= 100 ? "#D32F2F" : x.d <= 300 ? "#F57C00" : "#FDD835",
  }))));
  const etq = radioCP() < 1000 ? `${radioCP()} m` : `${radioCP() / 1000} km`;
  $("resumenCP").textContent = `${lista.length} ${lista.length === 1 ? "centro poblado rural" : "centros poblados rurales"} a ${etq} o menos de la línea.`;
  actualizarTablaCP();
}
function actualizarTablaCP() {
  if (!$("chkCP").checked || !E.falla) { $("tablaCP").innerHTML = ""; return; }
  const cerca = E.cpLinea.filter((x) => x.d <= radioCP())
    .map((x) => ({ ...x, df: haversine(x.lon, x.lat, E.falla[0], E.falla[1]) }))
    .filter((x) => x.df <= 3000).sort((a, b) => a.df - b.df);
  $("tablaCP").innerHTML = !cerca.length
    ? `<div class="alerta azul">Sin centros poblados rurales a menos de 3 km del punto de falla.</div>`
    : `<div class="etq">Próximos al punto de falla (hasta 3 km)</div><table class="tabla"><tr><th>Centro poblado</th><th>Distrito</th><th class="num">A la falla</th><th class="num">Al eje</th></tr>` +
      cerca.map((x) => `<tr><td>${esc(x.nombre)}</td><td>${esc(x.distrito)}</td><td class="num">${(x.df / 1000).toFixed(2)} km</td><td class="num">${Math.round(x.d)} m</td></tr>`).join("") +
      `</table>`;
}

// ------------------------------------------------------------------ incendios (Bomberos)
function parsearCSV(texto) {
  const filas = []; let fila = [], campo = "", comillas = false;
  for (let i = 0; i < texto.length; i++) {
    const ch = texto[i];
    if (comillas) {
      if (ch === '"') { if (texto[i + 1] === '"') { campo += '"'; i++; } else comillas = false; }
      else campo += ch;
    } else if (ch === '"') comillas = true;
    else if (ch === ",") { fila.push(campo); campo = ""; }
    else if (ch === "\n" || ch === "\r") {
      if (ch === "\r" && texto[i + 1] === "\n") i++;
      fila.push(campo); filas.push(fila); fila = []; campo = "";
    } else campo += ch;
  }
  if (campo || fila.length) { fila.push(campo); filas.push(fila); }
  return filas;
}
let temporizadorIncendios = null;
async function cargarIncendios() {
  const panel = $("panelIncendios");
  try {
    const r = await fetch("/api/bomberos", { cache: "no-store" });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const filas = parsearCSV(await r.text());
    const cab = filas.shift().map((h) => h.trim());
    const col = (n) => cab.indexOf(n);
    const iTipo = col("Tipo"), iEst = col("Estado"), iDir = col("Dirección / Distrito"),
      iFecha = col("Fecha Hora"), iMaq = col("Máquina"), iCoord = col("Coordenada");
    E.incendios = filas.filter((f) => (f[iTipo] || "").toUpperCase().includes("INCENDIO")).map((f) => {
      const [la, lo] = String(f[iCoord] || "").split(",").map(Number);
      return { tipo: f[iTipo], estado: (f[iEst] || "").toUpperCase(), dir: f[iDir] || "", fecha: f[iFecha] || "",
        maq: f[iMaq] || "", lat: la, lon: lo };
    });
  } catch (e) {
    E.incendios = [];
    panel.innerHTML = `<div class="alerta ambar"><b>Sin conexión</b>No se pudo consultar la información de Bomberos (${esc(e.message)}).</div>`;
    dibujarIncendios(); return;
  }
  dibujarIncendios();
}
function dibujarIncendios() {
  const on = $("chkIncendios").checked;
  ["incendios", "incendios-halo"].forEach((id) => mapa.setLayoutProperty(id, "visibility", on ? "visible" : "none"));
  if (!on) return;
  const conCoord = E.incendios.filter((x) => isFinite(x.lat) && isFinite(x.lon) && !(x.lat === 0 && x.lon === 0));
  mapa.getSource("incendios").setData(fc(conCoord.map((x) => punto([x.lon, x.lat], {
    nombre: x.tipo, info: `${x.estado === "ATENDIENDO" ? "En atención" : "Cerrado"} · ${x.dir} · ${x.fecha} · Unidades: ${x.maq || "—"}`,
    atencion: x.estado === "ATENDIENDO" ? 1 : 0, color: x.estado === "ATENDIENDO" ? "#D62828" : "#FF9800",
  }))));
  const nAt = E.incendios.filter((x) => x.estado === "ATENDIENDO").length;
  const nCe = E.incendios.filter((x) => x.estado === "CERRADO").length;
  const c = circ();
  const cerca = conCoord.filter((x) => x.estado === "ATENDIENDO")
    .map((x) => ({ ...x, d: distAPolilinea(x.lon, x.lat, c.pts).d })).filter((x) => x.d < 500).sort((a, b) => a.d - b.d);
  let html = `<div><span class="estado rojo">${nAt} <span>en atención</span></span>` +
    `<span class="estado naranja">${nCe} <span>cerrados</span></span></div>` +
    `<div class="nota">Cobertura nacional · actualización cada 90 s</div>`;
  if (cerca.length) {
    if (cerca.some((x) => x.d < 100)) {
      html += `<div class="alerta roja"><b>Alerta crítica</b>Incendio en atención a menos de 100 m de la línea.</div>`;
    }
    html += `<div class="alerta roja"><b>Incendios cercanos</b>${cerca.length} ${cerca.length === 1 ? "incendio en atención" : "incendios en atención"} a menos de 500 m de la línea.</div>`;
    html += `<ul class="lista-alerta">` + cerca.map((x) =>
      `<li>${esc(x.dir)}<small>${Math.round(x.d)} m de la línea · ${esc(x.fecha)}</small></li>`).join("") + `</ul>`;
  }
  $("panelIncendios").innerHTML = html;
}

// ------------------------------------------------------------------ clima (Open-Meteo)
async function cargarClimaLinea() {
  const c = circ(), paso = Math.max(1, Math.floor(c.pts.length / 12));
  const muestra = c.pts.filter((_, k) => k % paso === 0).slice(0, 25);
  try {
    const url = "https://api.open-meteo.com/v1/forecast?current=precipitation,weather_code&timezone=America%2FLima" +
      `&latitude=${muestra.map((p) => p[1].toFixed(5)).join(",")}&longitude=${muestra.map((p) => p[0].toFixed(5)).join(",")}`;
    const r = await fetch(url); if (!r.ok) throw new Error(`HTTP ${r.status}`);
    let res = await r.json(); if (!Array.isArray(res)) res = [res];
    mapa.getSource("clima").setData(fc(muestra.map((p, k) => {
      const cur = (res[k] || {}).current || {};
      const peso = TORMENTA.has(cur.weather_code) ? 1 : (cur.precipitation || 0) > 0 ? 0.35 : 0.04;
      return punto([p[0], p[1]], { peso });
    })));
  } catch (e) {
    $("panelClima").innerHTML = `<div class="alerta ambar"><b>Sin conexión</b>No se pudo consultar el clima (${esc(e.message)}).</div>`;
  }
}
let temporizadorClima = null;
function programarClimaFalla() {
  if (!$("chkClima").checked) return;
  clearTimeout(temporizadorClima);
  temporizadorClima = setTimeout(cargarClimaFalla, 600);
}
async function cargarClimaFalla() {
  const [lon, lat] = E.falla;
  try {
    const url = `https://api.open-meteo.com/v1/forecast?latitude=${lat.toFixed(5)}&longitude=${lon.toFixed(5)}` +
      "&current=precipitation,weather_code,wind_speed_10m&hourly=precipitation,weather_code&past_days=1&forecast_days=1&timezone=America%2FLima";
    const r = await fetch(url); if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const j = await r.json(), cur = j.current || {}, cod = cur.weather_code;
    E.climaFalla = {
      cod, desc: DESCRIPCION_CLIMA[cod] || `Código ${cod}`, lluvia: cur.precipitation || 0,
      ll24: ((j.hourly || {}).precipitation || []).slice(0, 24).reduce((s, v) => s + (v || 0), 0),
      viento: cur.wind_speed_10m ?? 0, tormenta: TORMENTA.has(cod),
    };
    const desc = DESCRIPCION_CLIMA[cod] || `Código ${cod}`, lluvia = cur.precipitation || 0;
    const ll24 = ((j.hourly || {}).precipitation || []).slice(0, 24).reduce((s, v) => s + (v || 0), 0);
    const clase = TORMENTA.has(cod) ? "roja" : lluvia > 0 ? "ambar" : "azul";
    const titulo = TORMENTA.has(cod) ? "Riesgo de descarga atmosférica" : lluvia > 0 ? "Lluvia en el punto de falla" : "Sin lluvia en el punto de falla";
    $("panelClima").innerHTML = `<div class="alerta ${clase}"><b>${titulo}</b>${esc(desc)}</div>` +
      `<dl class="tabla-dato">${filasDato([
        ["Lluvia actual", `${lluvia.toFixed(1)} mm/h`],
        ["Acumulado 24 h", `${ll24.toFixed(1)} mm`],
        ["Viento", `${(cur.wind_speed_10m ?? 0).toFixed(0)} km/h`],
      ])}</dl>`;
  } catch (e) {
    $("panelClima").innerHTML = `<div class="alerta ambar"><b>Sin conexión</b>No se pudo consultar el clima (${esc(e.message)}).</div>`;
  }
}

// ------------------------------------------------------------------ subestaciones
function dibujarSE() {
  const on = $("chkSE").checked;
  ["se-relleno", "se-borde"].forEach((id) => mapa.setLayoutProperty(id, "visibility", on ? "visible" : "none"));
  marcadoresSE.forEach((m) => m.remove()); marcadoresSE = [];
  if (!on) return;
  for (const s of D.subestaciones) {
    const el = document.createElement("div");
    el.className = "etiqueta-se";
    el.textContent = s.kv ? `${s.n} · ${s.kv} kV` : s.n;
    marcadoresSE.push(new maplibregl.Marker({ element: el }).setLngLat([s.lon, s.lat]).addTo(mapa));
  }
}

// ------------------------------------------------------------------ leyenda
function actualizarLeyenda() {
  const it = (estilo, txt) => `<div class="it">${estilo}<span>${txt}</span></div>`;
  const ln = (c, dash) => `<span class="ln" style="border-color:${c};${dash ? "border-top-style:dashed;" : ""}"></span>`;
  const pt = (c) => `<span class="pt" style="background:${c}"></span>`;
  const grupo = (t) => `<div class="grupo">${t}</div>`;
  let h = grupo("Líneas de transmisión") +
    it(ln(COLORES_KV[220]), "220 kV") + it(ln(COLORES_KV[138]), "138 kV") +
    it(ln(COLORES_KV[69]), "69 kV") + it(ln(COLORES_KV[60]), "60 kV y 50 kV") +
    it(ln(AZUL), "Línea seleccionada") + it(ln(E.oscuro ? "#C8D0DC" : "#111", true), "Tramo subterráneo");
  if ($("chkVias").checked) {
    const tipos = tiposViaActivos();
    h += grupo("Red vial");
    for (const t of Object.keys(NOMBRES_VIAS)) if (tipos.has(t)) h += it(ln(colorVia(t), t === "Herradura"), NOMBRES_VIAS[t]);
  }
  if ($("chkRios").checked) h += grupo("Hidrografía") + it(ln(COLORES_HIDRO["Río"]), "Río") + it(ln(COLORES_HIDRO.Acequia), "Acequia");
  if ($("chkCP").checked) h += grupo("Centros poblados rurales") + it(pt("#D32F2F"), "Hasta 100 m del eje") + it(pt("#F57C00"), "De 100 a 300 m") + it(pt("#FDD835"), "Más de 300 m");
  if ($("chkIncendios").checked) h += grupo("Incendios") + it(pt("#D62828"), "En atención") + it(pt("#FF9800"), "Cerrado");
  if ($("chkClima").checked) h += grupo("Clima") + it(pt("#4A1486"), "Tormenta eléctrica") + it(pt("#9E77C7"), "Lluvia");
  $("leyenda").innerHTML = h;
}

// ------------------------------------------------------------------ eventos
function conectarEventos() {
  $("buscarLinea").addEventListener("input", (e) => llenarSelector(e.target.value));
  $("selLinea").addEventListener("change", (e) => seleccionarLinea(+e.target.value));
  $("rangoDist").addEventListener("input", (e) => {
    E.distM = +e.target.value; $("numDist").value = fmtKm(E.distM); actualizarFalla();
  });
  $("numDist").addEventListener("input", (e) => {
    const v = parseFloat(e.target.value);
    if (!isFinite(v)) return;
    E.distM = Math.max(0, Math.min(largo(), v * 1000)); $("rangoDist").value = Math.round(E.distM); actualizarFalla();
  });
  $("numDist").addEventListener("change", sincronizarDistancia);

  document.querySelectorAll(".segmentado button").forEach((b) => b.addEventListener("click", () => {
    document.querySelectorAll(".segmentado button").forEach((x) => x.classList.toggle("activo", x === b));
    E.vista = b.dataset.vista; cambiarMapaBase(); dibujarVias(); actualizarLeyenda();
  }));
  $("chkOscuro").addEventListener("change", (e) => {
    E.oscuro = e.target.checked; document.body.classList.toggle("oscuro", E.oscuro);
    cambiarMapaBase(); dibujarVias(); actualizarLeyenda();
  });

  $("chkSE").addEventListener("change", () => { dibujarSE(); actualizarLeyenda(); });
  $("chkIncendios").addEventListener("change", (e) => {
    $("panelIncendios").hidden = !e.target.checked;
    clearInterval(temporizadorIncendios);
    if (e.target.checked) {
      $("panelIncendios").innerHTML = `<div class="nota">Consultando información de Bomberos…</div>`;
      cargarIncendios(); temporizadorIncendios = setInterval(cargarIncendios, 90000);
    } else dibujarIncendios();
    actualizarLeyenda();
  });
  $("chkClima").addEventListener("change", (e) => {
    $("panelClima").hidden = !e.target.checked;
    mapa.setLayoutProperty("clima", "visibility", e.target.checked ? "visible" : "none");
    if (e.target.checked) { $("panelClima").innerHTML = `<div class="nota">Consultando clima…</div>`; cargarClimaLinea(); cargarClimaFalla(); }
    actualizarLeyenda();
  });
  $("chkCP").addEventListener("change", (e) => { $("panelCP").hidden = !e.target.checked; dibujarCP(); actualizarLeyenda(); });
  $("selRadioCP").addEventListener("change", dibujarCP);
  $("chkRios").addEventListener("change", () => { dibujarHidro(); actualizarCercanos(); actualizarLeyenda(); });
  $("chkVias").addEventListener("change", (e) => {
    $("panelVias").hidden = !e.target.checked; dibujarVias(); actualizarCercanos(); actualizarLeyenda();
  });
  document.querySelectorAll("[data-via]").forEach((x) => x.addEventListener("change", () => {
    dibujarVias(); actualizarCercanos(); actualizarLeyenda();
  }));
}

// ------------------------------------------------------------------ inicio
async function iniciar() {
  try {
    const cfg = await fetch("/api/config", { cache: "no-store" }).then((r) => (r.ok ? r.json() : {})).catch(() => ({}));
    TOKEN = cfg.mapbox_token || null;
    D = await fetch("datos.json").then((r) => r.json());
  } catch (e) {
    $("cargando").innerHTML = `<div>No se pudieron cargar los datos: ${esc(e.message)}</div>`;
    return;
  }
  $("fechaDatos").textContent = `Datos al ${D.generado}`;
  // Latido: el servidor local se cierra solo cuando el navegador deja de enviarlo
  setInterval(() => fetch("/api/latido", { method: "POST" }).catch(() => {}), 20000);
  fetch("/api/latido", { method: "POST" }).catch(() => {});

  mapa = new maplibregl.Map({
    container: "mapa",
    style: { version: 8, sources: {}, layers: [{ id: "fondo", type: "background", paint: { "background-color": "#E8ECF0" } }] },
    center: [-76.0, -11.5], zoom: 6, attributionControl: { compact: true },
    preserveDrawingBuffer: true,  // necesario para capturar el mapa en el reporte PDF
  });
  mapa.addControl(new maplibregl.NavigationControl({ visualizePitch: false }), "top-right");
  mapa.addControl(new maplibregl.ScaleControl({ unit: "metric" }), "bottom-left");
  mapa.on("load", () => {
    mapa.addSource("base", fuenteBase());
    mapa.addLayer({ id: "base", type: "raster", source: "base" });
    crearCapas();
    conectarEventos();
    llenarSelector();
    seleccionarLinea(0);
    actualizarLeyenda();
    if (!TOKEN) {
      $("avisoMapa").hidden = false;
      $("avisoMapa").textContent = "Mapa base alternativo: Carto (calle) y Esri (satélite). No se configuró el token de Mapbox.";
    }
    $("cargando").remove();
  });
}
iniciar();
