"""Servidor local del Localizador de Fallas (versión de escritorio, un solo .exe).

- Sirve la app web (web/) empaquetada dentro del .exe.
- /api/config   -> token de Mapbox (config.json empaquetado o junto al .exe)
- /api/bomberos -> proxy de la hoja de emergencias de Bomberos (el navegador no
                   puede leerla directo por CORS)
- /api/latido   -> el navegador avisa que sigue abierto; si deja de hacerlo, el
                   servidor se cierra solo.
Solo usa la biblioteca estándar de Python.
"""
import json
import os
import socket
import sys
import threading
import time
import urllib.request
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

NOMBRE = "localizador-fallas-conelsur"
PUERTO_PREFERIDO = 8765
URL_BOMBEROS = ("https://docs.google.com/spreadsheets/d/"
                "1n_YelAX4D_mFQbXLduWTpjFLfzYOElzSYM8FiiWBhto/export?format=csv")
CIERRE_SIN_LATIDO_S = int(os.environ.get("LOCALIZADOR_CIERRE_S", 180))  # navegador cerrado -> 3 min
ESPERA_PRIMER_LATIDO_S = 600   # si el navegador nunca abrió la app


def carpeta_recursos():
    return getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))


def carpeta_exe():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


WEB = os.path.join(carpeta_recursos(), "web")
LOG = os.path.join(os.environ.get("TEMP", carpeta_exe()), "localizador_fallas.log")


def log(msg):
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + msg + "\n")
    except OSError:
        pass


def leer_config():
    """config.json junto al .exe (si existe) tiene prioridad sobre el empaquetado."""
    for ruta in (os.path.join(carpeta_exe(), "config.json"), os.path.join(carpeta_recursos(), "config.json")):
        if os.path.exists(ruta):
            try:
                with open(ruta, encoding="utf-8") as f:
                    return json.load(f)
            except (OSError, ValueError) as e:
                log(f"config inválida {ruta}: {e}")
    return {}


CONFIG = leer_config()
estado = {"ultimo_latido": None, "inicio": time.time(), "bomberos": (0.0, b"")}


class Manejador(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=WEB, **k)

    def log_message(self, *a):
        pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def _responder(self, codigo, cuerpo, tipo):
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def do_GET(self):
        ruta = self.path.split("?")[0]
        if ruta == "/api/ping":
            return self._responder(200, NOMBRE.encode(), "text/plain")
        if ruta == "/api/config":
            datos = {"mapbox_token": CONFIG.get("mapbox_token")}
            return self._responder(200, json.dumps(datos).encode(), "application/json")
        if ruta == "/api/bomberos":
            return self._bomberos()
        if ruta == "/datos.json":
            externo = os.path.join(carpeta_exe(), "datos.json")
            if os.path.exists(externo):   # datos actualizados junto al .exe
                with open(externo, "rb") as f:
                    return self._responder(200, f.read(), "application/json")
        return super().do_GET()

    def do_POST(self):
        if self.path.split("?")[0] == "/api/latido":
            estado["ultimo_latido"] = time.time()
            return self._responder(200, b"ok", "text/plain")
        self._responder(404, b"", "text/plain")

    def _bomberos(self):
        hora, cuerpo = estado["bomberos"]
        if time.time() - hora > 60 or not cuerpo:
            try:
                req = urllib.request.Request(URL_BOMBEROS, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=20) as r:
                    cuerpo = r.read()
                estado["bomberos"] = (time.time(), cuerpo)
            except Exception as e:  # sin internet, hoja caída, etc.
                log(f"bomberos: {e}")
                if not cuerpo:
                    return self._responder(502, str(e).encode(), "text/plain")
        self._responder(200, cuerpo, "text/csv; charset=utf-8")


def instancia_abierta():
    """Si ya hay un Localizador corriendo, devuelve su URL."""
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{PUERTO_PREFERIDO}/api/ping", timeout=1.5) as r:
            if r.read().decode() == NOMBRE:
                return f"http://127.0.0.1:{PUERTO_PREFERIDO}/"
    except Exception:
        pass
    return None


def puerto_libre():
    for p in [PUERTO_PREFERIDO] + list(range(PUERTO_PREFERIDO + 1, PUERTO_PREFERIDO + 20)):
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", p))
                return p
            except OSError:
                continue
    return 0


def vigilar_cierre(servidor):
    while True:
        time.sleep(min(10, max(1, CIERRE_SIN_LATIDO_S // 3)))
        ahora, ultimo = time.time(), estado["ultimo_latido"]
        if ultimo is None and ahora - estado["inicio"] > ESPERA_PRIMER_LATIDO_S:
            break
        if ultimo is not None and ahora - ultimo > CIERRE_SIN_LATIDO_S:
            break
    log("sin navegador abierto: cerrando")
    servidor.shutdown()


def main():
    url = instancia_abierta()
    if url:
        log(f"ya estaba abierto en {url}")
        if not os.environ.get("LOCALIZADOR_SIN_NAVEGADOR"):
            webbrowser.open(url)
        return
    puerto = puerto_libre()
    servidor = ThreadingHTTPServer(("127.0.0.1", puerto), Manejador)
    url = f"http://127.0.0.1:{servidor.server_address[1]}/"
    log(f"iniciado en {url} · web={WEB}")
    threading.Thread(target=vigilar_cierre, args=(servidor,), daemon=True).start()
    if not os.environ.get("LOCALIZADOR_SIN_NAVEGADOR"):
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    servidor.serve_forever()
    # Salida inmediata: no esperar conexiones keep-alive que el navegador dejó abiertas
    log("servidor detenido")
    os._exit(0)


if __name__ == "__main__":
    main()
