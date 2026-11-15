"use strict";
/* Reporte PDF del Localizador de Fallas.
   Activa temporalmente TODAS las capas, consulta los datos en línea (Bomberos,
   clima), captura el mapa (vista general + detalle satélite + detalle calle),
   arma el PDF con jsPDF y restaura la configuración que tenía el usuario.
   Usa las variables y funciones globales de app.js. */

const PDF = {
  azul: [11, 48, 136], azulClaro: [233, 238, 250], verde: [0, 166, 81], verdeOsc: [0, 128, 61],
  verdeClaro: [227, 247, 236], texto: [26, 26, 26], gris: [90, 97, 107], grisClaro: [227, 230, 236],
  rojo: [198, 40, 40], rojoClaro: [253, 236, 236], ambar: [183, 121, 31], ambarClaro: [255, 246, 224],
  m: 14,          // margen (mm)
};
const CAPAS_REPORTE = ["chkSE", "chkIncendios", "chkClima", "chkCP", "chkRios", "chkVias"];

const imgRayo = new Image();
imgRayo.src = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(RAYO_SVG);

// jsPDF con fuentes estándar solo admite Latin-1: normalizar caracteres especiales
const limpiar = (s) => String(s ?? "")
  .replace(/[–—]/g, "-").replace(/[‘’]/g, "'").replace(/[“”]/g, '"')
  .replace(/≤/g, "<=").replace(/≥/g, ">=").replace(/…/g, "...")
  .replace(/[^\x00-\xFF]/g, "");

const paso = (t) => { $("pasoReporte").textContent = t; };
const dormir = (ms) => new Promise((r) => setTimeout(r, ms));

function esperarMapa(maxMs = 20000) {
  return new Promise((resolver) => {
    const t = setTimeout(resolver, maxMs);
    mapa.once("idle", () => { clearTimeout(t); setTimeout(resolver, 200); });
    mapa.triggerRepaint();
  });
}

// ------------------------------------------------------------------ captura del mapa
function metrosPorPixel() {
  const lat = mapa.getCenter().lat;
  return (40075016.686 * Math.cos(lat * Math.PI / 180)) / (512 * Math.pow(2, mapa.getZoom()));
}

function capturarMapa(conEtiquetasSE) {
  const src = mapa.getCanvas();
  const W = src.width, H = src.height, k = W / src.clientWidth;
  const cv = document.createElement("canvas");
  cv.width = W; cv.height = H;
  const g = cv.getContext("2d");
  try { g.drawImage(src, 0, 0); } catch (e) { return null; }

  // Etiquetas de subestaciones (en la app son elementos HTML, no están en el lienzo)
  if (conEtiquetasSE) {
    g.font = `600 ${11.5 * k}px Segoe UI, Arial, sans-serif`;
    g.textBaseline = "middle"; g.lineJoin = "round";
    for (const s of D.subestaciones) {
      const p = mapa.project([s.lon, s.lat]);
      if (p.x < 0 || p.y < 0 || p.x > src.clientWidth || p.y > src.clientHeight) continue;
      const txt = s.kv ? `${s.n} · ${s.kv} kV` : s.n;
      g.strokeStyle = "rgba(0,0,0,.85)"; g.lineWidth = 3.5 * k;
      g.strokeText(txt, (p.x + 8) * k, p.y * k);
      g.fillStyle = "#fff"; g.fillText(txt, (p.x + 8) * k, p.y * k);
    }
  }

  // Marcador de falla: halo + rayo + etiqueta
  const e = 1.6 * k;  // en el PDF la imagen se reduce: marcador y etiqueta más grandes
  const p = mapa.project(E.falla), x = p.x * k, y = p.y * k, r = 22 * e;
  g.fillStyle = "rgba(229,57,53,.22)"; g.beginPath(); g.arc(x, y, r + 8 * e, 0, 2 * Math.PI); g.fill();
  g.strokeStyle = "rgba(229,57,53,.6)"; g.lineWidth = 2 * e; g.beginPath(); g.arc(x, y, r + 7 * e, 0, 2 * Math.PI); g.stroke();
  if (imgRayo.complete) g.drawImage(imgRayo, x - r, y - r, 2 * r, 2 * r);
  const etq = `FALLA · ${fmtKm(E.distM)} km`;
  g.font = `600 ${13 * e}px Segoe UI, Arial, sans-serif`;
  const tw = g.measureText(etq).width, pad = 8 * e, hEt = 22 * e, yEt = y - r - 12 * e - hEt;
  g.fillStyle = "#C62828";
  g.beginPath(); g.roundRect(x - tw / 2 - pad, yEt, tw + 2 * pad, hEt, 4 * e); g.fill();
  g.fillStyle = "#fff"; g.textAlign = "center"; g.textBaseline = "middle";
  g.fillText(etq, x, yEt + hEt / 2); g.textAlign = "left";

  // Escala gráfica
  const mpp = metrosPorPixel();
  const opciones = [50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000, 50000];
  const largoM = opciones.reduce((a, b) => (Math.abs(b / mpp - 150) < Math.abs(a / mpp - 150) ? b : a));
  const px = (largoM / mpp) * k, x0 = 16 * k, y0 = H - 18 * k;
  g.fillStyle = "rgba(255,255,255,.85)"; g.fillRect(x0 - 6 * k, y0 - 20 * k, px + 12 * k, 28 * k);
  g.strokeStyle = "#1A1A1A"; g.lineWidth = 2 * k;
  g.beginPath(); g.moveTo(x0, y0 - 6 * k); g.lineTo(x0, y0); g.lineTo(x0 + px, y0); g.lineTo(x0 + px, y0 - 6 * k); g.stroke();
  g.fillStyle = "#1A1A1A"; g.font = `${11 * k}px Segoe UI, Arial, sans-serif`; g.textBaseline = "alphabetic";
  g.fillText(largoM >= 1000 ? `${largoM / 1000} km` : `${largoM} m`, x0, y0 - 9 * k);

  // Créditos del mapa base
  const cred = TOKEN ? "© Mapbox © OpenStreetMap" : (E.vista === "satelite" ? "Imágenes © Esri" : "© OpenStreetMap © CARTO");
  g.font = `${10 * k}px Segoe UI, Arial, sans-serif`;
  const cw = g.measureText(cred).width;
  g.fillStyle = "rgba(255,255,255,.8)"; g.fillRect(W - cw - 14 * k, H - 18 * k, cw + 10 * k, 15 * k);
  g.fillStyle = "#333"; g.fillText(cred, W - cw - 9 * k, H - 7 * k);

  try {
    return { url: cv.toDataURL("image/jpeg", 0.86), aspecto: H / W };
  } catch (e) {
    return null;   // lienzo "contaminado" (teselas sin CORS)
  }
}

async function capturaConVista(vista, encuadre) {
  E.vista = vista;
  document.querySelectorAll(".segmentado button").forEach((b) => b.classList.toggle("activo", b.dataset.vista === vista));
  cambiarMapaBase();
  dibujarVias();
  if (encuadre.limites) mapa.fitBounds(encuadre.limites, { padding: 70, duration: 0, maxZoom: 15 });
  else mapa.jumpTo({ center: encuadre.centro, zoom: encuadre.zoom });
  await esperarMapa();
  await dormir(300);
  return capturarMapa($("chkSE").checked);
}

// ------------------------------------------------------------------ datos del reporte
function datosReporte() {
  const c = circ(), L = largo(c), dI = desdeInicioM();
  const [lon, lat] = E.falla;
  const prog = (p) => (E.desdeInicio ? p[2] : L - p[2]);

  // Torres adyacentes al punto de falla (2 antes y 2 después)
  const nom = c.pts.filter((p) => p[3]);
  const iAnt = Math.max(0, nom.indexOf(E.torresFalla.ant));
  const torres = nom.slice(Math.max(0, iAnt - 2), iAnt + 4).map((p) => ({
    nombre: p[3], prog: prog(p), dFalla: Math.abs(p[2] - dI), lat: p[1], lon: p[0],
  }));

  // Accesos e hidrografía
  const accesos = Object.keys(NOMBRES_VIAS).map((t) => {
    const m = masCercano(E.viasCaja.filter((v) => v.t === t));
    return { tipo: NOMBRES_VIAS[t], clave: t, d: m.e ? m.d : null };
  });
  const hidro = ["Río", "Acequia"].map((t) => {
    const m = masCercano(E.hidroCaja.filter((v) => v.t === t));
    return { tipo: t, nombre: m.e && m.e.n ? m.e.n.replace(/^Rio /, "Río ") : "", d: m.e ? m.d : null };
  });
  let se = null;
  for (const s of D.subestaciones) {
    const d = haversine(lon, lat, s.lon, s.lat);
    if (!se || d < se.d) se = { nombre: s.n, kv: s.kv, d };
  }

  // Centros poblados
  const cp = E.cpLinea.map((x) => ({ ...x, df: haversine(x.lon, x.lat, lon, lat) }));
  const cpFalla = cp.filter((x) => x.df <= 3000).sort((a, b) => a.df - b.df);
  const bandas = [
    ["Hasta 100 m del eje", cp.filter((x) => x.d <= 100).length],
    ["De 100 a 300 m", cp.filter((x) => x.d > 100 && x.d <= 300).length],
    ["De 300 m a 1 km", cp.filter((x) => x.d > 300 && x.d <= 1000).length],
    ["De 1 a 5 km", cp.filter((x) => x.d > 1000).length],
  ];

  // Incendios
  const conCoord = E.incendios.filter((x) => isFinite(x.lat) && isFinite(x.lon) && !(x.lat === 0 && x.lon === 0));
  const incendios = conCoord.map((x) => ({
    ...x, dLinea: distAPolilinea(x.lon, x.lat, c.pts).d, dFalla: haversine(x.lon, x.lat, lon, lat),
  }));
  const incCerca = incendios.filter((x) => x.estado === "ATENDIENDO" && (x.dLinea < 5000 || x.dFalla < 10000))
    .sort((a, b) => a.dLinea - b.dLinea);

  // Clima a lo largo de la línea (muestras del mapa de calor)
  let climaLinea = { tormenta: 0, lluvia: 0, total: 0 };
  try {
    const datos = mapa.getSource("clima").serialize().data;
    for (const f of datos.features || []) {
      climaLinea.total++;
      if (f.properties.peso >= 1) climaLinea.tormenta++;
      else if (f.properties.peso >= 0.35) climaLinea.lluvia++;
    }
  } catch (e) { /* sin datos */ }

  // Alertas y precauciones
  const alertas = [];
  const add = (nivel, txt) => alertas.push({ nivel, txt });
  const incCrit = incendios.filter((x) => x.estado === "ATENDIENDO" && x.dLinea < 100);
  const inc500 = incendios.filter((x) => x.estado === "ATENDIENDO" && x.dLinea < 500);
  if (incCrit.length) add("alta", `Incendio en atención a menos de 100 m de la línea (${incCrit[0].dir}).`);
  else if (inc500.length) add("alta", `${inc500.length} incendio(s) en atención a menos de 500 m de la línea.`);
  const incFalla = incendios.filter((x) => x.estado === "ATENDIENDO" && x.dFalla < 5000);
  if (incFalla.length) add("media", `${incFalla.length} incendio(s) en atención a menos de 5 km del punto de falla.`);
  const cf = E.climaFalla;
  if (cf) {
    if (cf.tormenta) add("alta", `Tormenta eléctrica en el punto de falla (${cf.desc}). Evaluar condiciones antes de intervenir.`);
    else if (cf.lluvia > 0) add("media", `Lluvia en el punto de falla: ${cf.lluvia.toFixed(1)} mm/h (${cf.desc}).`);
    if (cf.ll24 >= 10) add("media", `Lluvia acumulada de ${cf.ll24.toFixed(1)} mm en 24 h: posibles accesos afectados o terreno inestable.`);
  }
  if (climaLinea.tormenta) add("media", `Tormenta eléctrica en ${climaLinea.tormenta} de ${climaLinea.total} puntos muestreados a lo largo de la línea.`);
  const cp300 = cpFalla.filter((x) => x.df <= 300);
  if (cp300.length) add("media", `Centro poblado ${cp300[0].nombre} a ${Math.round(cp300[0].df)} m del punto de falla: coordinar con la población.`);
  else if (cpFalla.length) add("info", `Centro poblado más cercano a la falla: ${cpFalla[0].nombre} (${(cpFalla[0].df / 1000).toFixed(2)} km).`);
  const vehic = accesos.filter((a) => a.clave !== "Herradura" && a.d != null).sort((a, b) => a.d - b.d)[0];
  if (!vehic) add("media", "No se identificó acceso vehicular en un radio de 5 km del punto de falla.");
  else if (vehic.d > 1000) add("media", `Acceso vehicular más cercano a ${fmtDist(vehic.d)} (${vehic.tipo.toLowerCase()}): prever tramo a pie.`);
  else add("info", `Acceso vehicular más cercano: ${vehic.tipo.toLowerCase()} a ${fmtDist(vehic.d)}.`);
  const rio = hidro[0];
  if (rio.d != null && rio.d < 300) add("media", `${rio.nombre || "Río"} a ${fmtDist(rio.d)} del punto de falla: posible cruce o crecida.`);
  if (se) add("info", `Subestación más cercana: ${se.nombre} a ${fmtDist(se.d)}.`);
  if (!alertas.some((a) => a.nivel !== "info")) add("info", "Sin alertas de incendios, clima ni centros poblados próximos en el punto de falla.");

  const orden = { alta: 0, media: 1, info: 2 };
  alertas.sort((a, b) => orden[a.nivel] - orden[b.nivel]);
  return { c, L, lon, lat, torres, accesos, hidro, se, cpFalla, bandas, incendios, incCerca, climaLinea, alertas };
}

// ------------------------------------------------------------------ armado del PDF
async function logoDataURL() {
  try {
    const b = await fetch("logo.png").then((r) => r.blob());
    return await new Promise((res) => { const fr = new FileReader(); fr.onload = () => res(fr.result); fr.readAsDataURL(b); });
  } catch (e) { return null; }
}

function crearPDF(R, mapas, logo) {
  const { jsPDF } = window.jspdf;
  const doc = new jsPDF({ unit: "mm", format: "a4" });
  const AW = 210, AH = 297, M = PDF.m, AU = AW - 2 * M;
  let y = M;
  const ahora = new Date();
  const fecha = ahora.toLocaleDateString("es-PE") + " " + ahora.toLocaleTimeString("es-PE", { hour: "2-digit", minute: "2-digit" });

  const color = (c, tipo = "text") => (tipo === "text" ? doc.setTextColor(...c) : tipo === "fill" ? doc.setFillColor(...c) : doc.setDrawColor(...c));
  const txt = (s, x, yy, o = {}) => doc.text(limpiar(s), x, yy, o);
  const fuente = (estilo = "normal", tam = 9) => { doc.setFont("helvetica", estilo); doc.setFontSize(tam); };
  const nuevaPagina = () => { doc.addPage(); y = M + 4; };
  const asegurar = (alto) => { if (y + alto > AH - 16) nuevaPagina(); };

  function seccion(t) {
    asegurar(14);
    y += 3;
    fuente("bold", 9.5); color(PDF.azul); txt(t.toUpperCase(), M, y);
    color(PDF.grisClaro, "draw"); doc.setLineWidth(0.3); doc.line(M, y + 1.8, AW - M, y + 1.8);
    y += 7;
  }

  function pares(filas, columnas = 2) {
    const anchoCol = AU / columnas, etqW = anchoCol * 0.38;
    for (let i = 0; i < filas.length; i += columnas) {
      let alto = 5.2;
      const lineas = filas.slice(i, i + columnas).map(([, v]) => doc.splitTextToSize(limpiar(v), anchoCol - etqW - 4));
      alto = Math.max(alto, ...lineas.map((l) => l.length * 4 + 1.2));
      asegurar(alto);
      filas.slice(i, i + columnas).forEach(([k, v], j) => {
        const x = M + j * anchoCol;
        fuente("normal", 8.5); color(PDF.gris); txt(k, x, y);
        fuente("bold", 8.5); color(PDF.texto); doc.text(lineas[j], x + etqW, y);
      });
      y += alto;
    }
    y += 1;
  }

  function tabla(cols, filas, vacio) {
    if (!filas.length) {
      asegurar(7); fuente("italic", 8.5); color(PDF.gris); txt(vacio || "Sin registros.", M, y); y += 6; return;
    }
    const total = cols.reduce((s, c) => s + c.w, 0), esc = AU / total;
    const cabecera = () => {
      asegurar(7);
      color(PDF.azulClaro, "fill"); doc.rect(M, y - 4, AU, 6, "F");
      fuente("bold", 7.8); color(PDF.azul);
      let x = M;
      for (const c of cols) {
        const w = c.w * esc;
        txt(c.t.toUpperCase(), c.der ? x + w - 1.5 : x + 1.5, y, c.der ? { align: "right" } : {});
        x += w;
      }
      y += 5;
    };
    cabecera();
    filas.forEach((f, i) => {
      const celdas = f.map((v, j) => doc.splitTextToSize(limpiar(v), cols[j].w * esc - 3));
      const alto = Math.max(...celdas.map((l) => l.length)) * 3.7 + 1.6;
      if (y + alto > AH - 16) { nuevaPagina(); cabecera(); }
      if (i % 2) { color([247, 248, 251], "fill"); doc.rect(M, y - 3.6, AU, alto, "F"); }
      fuente("normal", 8.2); color(PDF.texto);
      let x = M;
      celdas.forEach((l, j) => {
        const w = cols[j].w * esc;
        doc.text(l, cols[j].der ? x + w - 1.5 : x + 1.5, y, cols[j].der ? { align: "right" } : {});
        x += w;
      });
      y += alto;
    });
    y += 2;
  }

  function imagenMapa(mapaCap, titulo, alturaMax) {
    seccion(titulo);
    if (!mapaCap) {
      asegurar(12); fuente("italic", 9); color(PDF.gris);
      txt("No se pudo capturar el mapa (sin conexión con el servidor de mapas).", M, y); y += 8; return;
    }
    let w = AU, h = w * mapaCap.aspecto;
    if (alturaMax && h > alturaMax) { h = alturaMax; w = h / mapaCap.aspecto; }
    asegurar(h + 2);
    doc.addImage(mapaCap.url, "JPEG", M + (AU - w) / 2, y - 2, w, h);
    color(PDF.grisClaro, "draw"); doc.setLineWidth(0.3); doc.rect(M + (AU - w) / 2, y - 2, w, h);
    y += h + 3;
  }

  function leyenda() {
    const items = [
      ["l", [229, 57, 53], "220 kV"], ["l", [46, 125, 50], "138 kV"], ["l", [245, 124, 0], "69 kV"],
      ["l", [21, 101, 192], "60 kV y 50 kV"], ["l", PDF.azul, "Línea seleccionada"], ["d", [17, 17, 17], "Tramo subterráneo"],
      ["l", [33, 33, 33], "Carretera asfaltada"], ["l", [141, 110, 99], "Carretera afirmada"], ["l", [255, 179, 0], "Camino carrozable"],
      ["d", [171, 71, 188], "Camino de herradura"], ["l", [41, 182, 246], "Río"], ["l", [128, 222, 234], "Acequia"],
      ["p", [211, 47, 47], "C. poblado hasta 100 m"], ["p", [245, 124, 0], "C. poblado 100 a 300 m"], ["p", [253, 216, 53], "C. poblado más de 300 m"],
      ["p", [214, 40, 40], "Incendio en atención"], ["p", [255, 152, 0], "Incendio cerrado"], ["p", [74, 20, 134], "Tormenta / lluvia"],
      ["f", [17, 17, 17], "Patio de subestación"], ["x", PDF.rojo, "Punto de falla estimado"],
    ];
    const col = 4, ancho = AU / col, filas = Math.ceil(items.length / col);
    asegurar(filas * 4.6 + 4);
    fuente("normal", 7.6);
    items.forEach(([tipo, c, t], i) => {
      const x = M + (i % col) * ancho, yy = y + Math.floor(i / col) * 4.6;
      color(c, "draw"); color(c, "fill"); doc.setLineWidth(0.9);
      if (tipo === "l") doc.line(x, yy - 1.1, x + 7, yy - 1.1);
      if (tipo === "d") { doc.setLineDashPattern([1.2, 0.9], 0); doc.line(x, yy - 1.1, x + 7, yy - 1.1); doc.setLineDashPattern([], 0); }
      if (tipo === "p") { doc.setLineWidth(0.2); color([60, 60, 60], "draw"); doc.circle(x + 3.5, yy - 1.1, 1.2, "FD"); }
      if (tipo === "f") doc.rect(x + 1.5, yy - 2.6, 4, 3, "F");
      if (tipo === "x") doc.circle(x + 3.5, yy - 1.1, 1.6, "F");
      color(PDF.texto); txt(t, x + 9, yy);
    });
    y += filas * 4.6 + 2;
  }

  // ---------------- Página 1: encabezado, datos, alertas, vista general
  if (logo) doc.addImage(logo, "PNG", M, M - 2, 39, 8);
  fuente("normal", 8); color(PDF.gris);
  txt(`Generado: ${fecha}`, AW - M, M + 1, { align: "right" });
  txt(`Datos de líneas al ${D.generado}`, AW - M, M + 5, { align: "right" });
  y = M + 17;
  fuente("bold", 16); color(PDF.azul); txt("Reporte de localización de falla", M, y);
  y += 6;
  fuente("normal", 10.5); color(PDF.gris); txt(R.c.n, M, y);
  y += 3;
  color(PDF.verde, "fill"); doc.rect(M, y, AU, 0.8, "F");
  y += 5;

  // Indicadores
  const kpis = [
    ["Distancia de falla", `${fmtKm(E.distM)} km`], ["Longitud de la línea", `${fmtKm(R.L)} km`],
    ["Tensión nominal", R.c.kv ? `${R.c.kv} kV` : "-"], ["Torres", String(R.c.pts.filter((p) => p[3] && !p[3].startsWith("Pórtico")).length)],
  ];
  const kw = (AU - 9) / 4;
  kpis.forEach(([k, v], i) => {
    const x = M + i * (kw + 3);
    color([248, 249, 252], "fill"); doc.rect(x, y, kw, 15, "F");
    color(i === 0 ? PDF.verde : PDF.azul, "fill"); doc.rect(x, y, kw, 0.9, "F");
    fuente("bold", 7); color(PDF.gris); txt(k.toUpperCase(), x + 3, y + 5);
    fuente("bold", 13); color(i === 0 ? PDF.verdeOsc : PDF.azul); txt(v, x + 3, y + 12);
  });
  y += 21;

  seccion("Datos del evento");
  const ta = E.torresFalla;
  pares([
    ["Línea", R.c.n], ["Medido desde", extremoActual()],
    ["Tensión / tipo", [R.c.kv ? `${R.c.kv} kV` : "Sin dato", R.c.tipo].filter(Boolean).join(" · ")], ["Distancia de falla", `${fmtKm(E.distM)} km`],
    ["Entre torres", E.detalleTorres], ["Coordenadas", `${R.lat.toFixed(5)}, ${R.lon.toFixed(5)}`],
    ["Longitud total", `${fmtKm(R.L)} km`], ["Extremos", etiquetasExtremos(R.c).join("  /  ")],
  ]);
  fuente("normal", 8.5); color(PDF.azul);
  doc.textWithLink(limpiar("Abrir el punto de falla en Google Maps"), M, y, { url: `https://www.google.com/maps?q=${R.lat.toFixed(6)},${R.lon.toFixed(6)}` });
  y += 4;

  seccion("Alertas y precauciones");
  for (const a of R.alertas) {
    const fondo = a.nivel === "alta" ? PDF.rojoClaro : a.nivel === "media" ? PDF.ambarClaro : PDF.azulClaro;
    const borde = a.nivel === "alta" ? PDF.rojo : a.nivel === "media" ? PDF.ambar : PDF.azul;
    const etq = a.nivel === "alta" ? "ALTA" : a.nivel === "media" ? "MEDIA" : "INFO";
    fuente("normal", 8.5);
    const lineas = doc.splitTextToSize(limpiar(a.txt), AU - 22);
    const alto = lineas.length * 3.9 + 2.6;
    asegurar(alto + 1);
    color(fondo, "fill"); doc.rect(M, y - 3.5, AU, alto, "F");
    color(borde, "fill"); doc.rect(M, y - 3.5, 0.9, alto, "F");
    fuente("bold", 7.2); color(borde); txt(etq, M + 3, y);
    fuente("normal", 8.5); color(PDF.texto); doc.text(lineas, M + 17, y);
    y += alto + 1.2;
  }

  imagenMapa(mapas.general, "Vista general de la línea", AH - 16 - y - 12);

  // ---------------- Página 2: detalle del punto de falla
  nuevaPagina();
  imagenMapa(mapas.satelite, "Detalle del punto de falla - imagen satelital", 92);
  imagenMapa(mapas.calle, "Detalle del punto de falla - mapa de calles", 92);
  asegurar(36);  // la leyenda va completa en la misma hoja
  seccion("Leyenda");
  leyenda();

  // ---------------- Página 3: tablas
  nuevaPagina();
  seccion(`Torres adyacentes al punto de falla (progresiva desde ${extremoActual()})`);
  tabla([{ t: "Torre", w: 22 }, { t: "Progresiva", w: 30, der: true }, { t: "Distancia a la falla", w: 30, der: true },
    { t: "Latitud", w: 26, der: true }, { t: "Longitud", w: 26, der: true }],
  R.torres.map((t) => [t.nombre, `${fmtKm(t.prog)} km`, fmtDist(t.dFalla), t.lat.toFixed(5), t.lon.toFixed(5)]));

  seccion("Accesos e hidrografía cercanos al punto de falla");
  tabla([{ t: "Elemento", w: 60 }, { t: "Detalle", w: 60 }, { t: "Distancia", w: 30, der: true }], [
    ...R.accesos.map((a) => [a.tipo, "Red vial INEI", a.d == null ? "Más de 5 km" : fmtDist(a.d)]),
    ...R.hidro.map((h) => [h.tipo, h.nombre || "-", h.d == null ? "Más de 5 km" : fmtDist(h.d)]),
    ...(R.se ? [["Subestación más cercana", `${R.se.nombre}${R.se.kv ? " · " + R.se.kv + " kV" : ""}`, fmtDist(R.se.d)]] : []),
  ]);

  seccion("Centros poblados rurales próximos al punto de falla (hasta 3 km)");
  tabla([{ t: "Centro poblado", w: 46 }, { t: "Distrito", w: 34 }, { t: "Provincia", w: 34 }, { t: "A la falla", w: 22, der: true }, { t: "Al eje", w: 18, der: true }],
    R.cpFalla.slice(0, 25).map((x) => [x.nombre, x.distrito, x.provincia, `${(x.df / 1000).toFixed(2)} km`, `${Math.round(x.d)} m`]),
    "Sin centros poblados rurales a menos de 3 km del punto de falla.");
  fuente("normal", 8.5); color(PDF.gris);
  asegurar(6);
  txt(`Centros poblados rurales a lo largo de toda la línea (hasta 5 km del eje): ${R.bandas.map(([k, n]) => `${k.toLowerCase()}: ${n}`).join(" · ")}.`, M, y, { maxWidth: AU });
  y += 9;

  seccion("Incendios en atención cercanos (Bomberos)");
  tabla([{ t: "Ubicación", w: 70 }, { t: "Fecha y hora", w: 32 }, { t: "A la línea", w: 22, der: true }, { t: "A la falla", w: 22, der: true }],
    R.incCerca.slice(0, 20).map((x) => [x.dir, x.fecha, fmtDist(x.dLinea), fmtDist(x.dFalla)]),
    `Sin incendios en atención a menos de 5 km de la línea. Registro nacional: ${E.incendios.filter((x) => x.estado === "ATENDIENDO").length} en atención, ${E.incendios.filter((x) => x.estado === "CERRADO").length} cerrados.`);

  seccion("Condiciones meteorológicas (Open-Meteo)");
  const cf = E.climaFalla;
  pares(cf ? [
    ["Condición actual", cf.desc], ["Lluvia actual", `${cf.lluvia.toFixed(1)} mm/h`],
    ["Acumulado 24 h", `${cf.ll24.toFixed(1)} mm`], ["Viento", `${cf.viento.toFixed(0)} km/h`],
    ["Tormenta en la línea", `${R.climaLinea.tormenta} de ${R.climaLinea.total} puntos`], ["Lluvia en la línea", `${R.climaLinea.lluvia} de ${R.climaLinea.total} puntos`],
  ] : [["Estado", "No se pudo consultar el clima (sin conexión)."]]);

  seccion("Notas y fuentes");
  fuente("normal", 7.8); color(PDF.gris);
  const notas = [
    "Ubicación estimada por interpolación a lo largo del trazado real de la línea (KMZ), con origen en el pórtico de la subestación indicada. No considera la flecha del conductor; la distancia reportada por el relé puede diferir.",
    "Centros poblados, red vial, ríos y acequias: INEI (SIGE Atlas). Precisión aproximada de 5 a 10 m; algunos datos pueden no estar actualizados.",
    "Incendios: registro de emergencias de Bomberos Perú. Clima: Open-Meteo (condición actual y acumulado de 24 h). Mapas base: Mapbox / OpenStreetMap / Esri / CARTO.",
  ];
  for (const n of notas) {
    const l = doc.splitTextToSize(limpiar("- " + n), AU);
    asegurar(l.length * 3.5 + 1); doc.text(l, M, y); y += l.length * 3.5 + 1.2;
  }

  // Pie de página
  const n = doc.getNumberOfPages();
  for (let i = 1; i <= n; i++) {
    doc.setPage(i);
    color(PDF.grisClaro, "draw"); doc.setLineWidth(0.3); doc.line(M, AH - 11, AW - M, AH - 11);
    fuente("normal", 7.5); color(PDF.gris);
    txt("CONELSUR · Sistema de Localización de Fallas SEIN", M, AH - 7);
    txt(`${R.c.n.split(" ")[0]} · ${fmtKm(E.distM)} km · Página ${i} de ${n}`, AW - M, AH - 7, { align: "right" });
  }
  return doc;
}

// ------------------------------------------------------------------ orquestación
async function generarReporte() {
  const boton = $("btnReporte");
  boton.disabled = true;
  $("generandoReporte").hidden = false;

  // Estado del usuario, para restaurarlo al final
  const previo = {
    capas: Object.fromEntries(CAPAS_REPORTE.map((id) => [id, $(id).checked])),
    vias: Array.from(document.querySelectorAll("[data-via]")).map((x) => x.checked),
    vista: E.vista, oscuro: E.oscuro,
    camara: { center: mapa.getCenter(), zoom: mapa.getZoom(), bearing: mapa.getBearing(), pitch: mapa.getPitch() },
  };
  const tarjeta = document.querySelector(".mapa-card");
  try {
    paso("Activando todas las capas");
    if (E.oscuro) $("chkOscuro").click();
    document.querySelectorAll("[data-via]").forEach((x) => { x.checked = true; });
    for (const id of CAPAS_REPORTE) {
      if (!$(id).checked) { $(id).checked = true; $(id).dispatchEvent(new Event("change")); }
    }
    dibujarVias(); actualizarLeyenda();

    paso("Consultando incendios y clima");
    await Promise.allSettled([cargarIncendios(), cargarClimaLinea(), cargarClimaFalla()]);
    dibujarIncendios();

    paso("Calculando distancias y alertas");
    const R = datosReporte();

    tarjeta.classList.add("captura");
    mapa.resize();
    const c = circ();
    const caja = cajaDe(c.pts.map((p) => [p[0], p[1]]));
    paso("Capturando vista general (1 de 3)");
    const general = await capturaConVista("calle", { limites: [[caja[0], caja[1]], [caja[2], caja[3]]] });
    paso("Capturando detalle satelital (2 de 3)");
    const satelite = await capturaConVista("satelite", { centro: E.falla, zoom: 14.3 });
    paso("Capturando detalle de calles (3 de 3)");
    const calle = await capturaConVista("calle", { centro: E.falla, zoom: 14.3 });

    paso("Armando el PDF");
    const doc = crearPDF(R, { general, satelite, calle }, await logoDataURL());
    const f = new Date(), dos = (v) => String(v).padStart(2, "0");
    const nombre = `Reporte_falla_${c.n.split(" ")[0]}_${f.getFullYear()}${dos(f.getMonth() + 1)}${dos(f.getDate())}_${dos(f.getHours())}${dos(f.getMinutes())}.pdf`;
    doc.save(nombre);
    E.ultimoReporte = { nombre, paginas: doc.getNumberOfPages(), alertas: R.alertas, mapas: [general, satelite, calle].map((m) => !!m) };
  } catch (e) {
    console.error(e);
    alert("No se pudo generar el reporte: " + e.message);
  } finally {
    // Restaurar la configuración del usuario
    tarjeta.classList.remove("captura");
    mapa.resize();
    document.querySelectorAll("[data-via]").forEach((x, i) => { x.checked = previo.vias[i]; });
    for (const id of CAPAS_REPORTE) {
      if ($(id).checked !== previo.capas[id]) { $(id).checked = previo.capas[id]; $(id).dispatchEvent(new Event("change")); }
    }
    E.vista = previo.vista;
    document.querySelectorAll(".segmentado button").forEach((b) => b.classList.toggle("activo", b.dataset.vista === E.vista));
    if (previo.oscuro !== E.oscuro) $("chkOscuro").click(); else cambiarMapaBase();
    dibujarVias(); actualizarLeyenda();
    mapa.jumpTo(previo.camara);
    $("generandoReporte").hidden = true;
    boton.disabled = false;
  }
}

$("btnReporte").addEventListener("click", generarReporte);
