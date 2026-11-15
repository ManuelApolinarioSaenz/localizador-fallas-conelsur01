"""Lanzador local del Localizador de Fallas (versión de escritorio, un solo .exe).

Se abre igual que el Instructivo de Avisos y OM:
  1. Sirve la app web (web/) solo en este equipo (127.0.0.1).
  2. La abre en una ventana de aplicación (Microsoft Edge o Chrome en modo --app;
     si no hay ninguno, el navegador predeterminado).
  3. Al cerrar la ventana, la app se apaga sola en pocos segundos.
  4. Si ya está abierta, un segundo doble clic solo abre otra ventana.
Rutas:
  /api/ping     -> firma de la app (detección de instancia abierta) y latido
  /api/config   -> token de Mapbox (config.json empaquetado o junto al .exe)
  /api/bomberos -> proxy de la hoja de emergencias de Bomberos (CORS)
  /api/adios    -> la ventana se cerró (o se recargó)
Errores: cuadro de mensaje y registro en %LOCALAPPDATA%\\LocalizadorFallas\\registro.log
Solo usa la biblioteca estándar de Python.
"""
import ctypes
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.request
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

TITULO = "Localizador de Fallas Georreferenciado (Conelsur)"
FIRMA = b"localizador-fallas-conelsur"
PUERTO_INICIAL = int(os.environ.get("LOCALIZADOR_PUERTO", 8765))
URL_BOMBEROS = ("https://docs.google.com/spreadsheets/d/"
                "1n_YelAX4D_mFQbXLduWTpjFLfzYOElzSYM8FiiWBhto/export?format=csv")
SIN_LATIDO_S = int(os.environ.get("LOCALIZADOR_CIERRE_S", 75))  # sin señales de ninguna ventana -> apagar
TRAS_CIERRE_S = 6                # tras cerrar la última ventana, espera por si fue una recarga
LIMITE_PRIMERA_CONEXION_S = 180  # si la ventana nunca llegó a abrir

DIR_DATOS = os.path.join(os.environ.get("LOCALAPPDATA", tempfile.gettempdir()), "LocalizadorFallas")
os.makedirs(DIR_DATOS, exist_ok=True)
LOG = os.path.join(DIR_DATOS, "registro.log")
_log = open(LOG, "w", encoding="utf-8", buffering=1)
if sys.stdout is None or getattr(sys, "frozen", False):
    sys.stdout = _log
    sys.stderr = _log


def log(msg):
    _log.write(time.strftime("%Y-%m-%d %H:%M:%S ") + msg + "\n")


def mensaje(texto, error=False):
    try:
        ctypes.windll.user32.MessageBoxW(None, texto, TITULO, 0x10 if error else 0x40)
    except Exception:  # noqa: BLE001
        print(texto)


def carpeta_recursos():
    return getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))


def carpeta_exe():
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


WEB = os.path.join(carpeta_recursos(), "web")


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


class Estado:
    ultimo_latido = None
    cierre_en = None
    inicio = time.time()
    bomberos = (0.0, b"")


# -------------------------------------------------------------------------------------------------
# Servidor local
# -------------------------------------------------------------------------------------------------
class Manejador(SimpleHTTPRequestHandler):
    extensions_map = {**SimpleHTTPRequestHandler.extensions_map,
                      ".js": "text/javascript", ".css": "text/css", ".json": "application/json",
                      ".svg": "image/svg+xml"}

    def __init__(self, *a, **k):
        super().__init__(*a, directory=WEB, **k)

    def log_message(self, *a):
        pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        super().end_headers()

    def _responder(self, codigo, cuerpo, tipo="text/plain; charset=utf-8"):
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(cuerpo)))
        self.end_headers()
        self.wfile.write(cuerpo)

    def do_GET(self):
        ruta = self.path.split("?")[0]
        if ruta == "/api/ping":
            Estado.ultimo_latido = time.time()
            Estado.cierre_en = None
            return self._responder(200, FIRMA)
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
        ruta = self.path.split("?")[0]
        if ruta == "/api/adios":
            Estado.cierre_en = time.time()
            return self._responder(200, b"")
        if ruta == "/api/latido":   # compatibilidad con la versión anterior de la web
            Estado.ultimo_latido = time.time()
            Estado.cierre_en = None
            return self._responder(200, b"ok")
        self._responder(404, b"")

    def _bomberos(self):
        hora, cuerpo = Estado.bomberos
        if time.time() - hora > 60 or not cuerpo:
            try:
                req = urllib.request.Request(URL_BOMBEROS, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, timeout=20) as r:
                    cuerpo = r.read()
                Estado.bomberos = (time.time(), cuerpo)
            except Exception as e:  # sin internet, hoja caída, etc.
                log(f"bomberos: {e}")
                if not cuerpo:
                    return self._responder(502, str(e).encode())
        self._responder(200, cuerpo, "text/csv; charset=utf-8")


class Servidor(ThreadingHTTPServer):
    """Toma el puerto en exclusiva: en Windows, SO_REUSEADDR permitiría compartirlo con otra app."""
    allow_reuse_address = False
    daemon_threads = True

    def server_bind(self):
        if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def es_nuestro(puerto):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{puerto}/api/ping", timeout=1) as r:
            return r.read() == FIRMA
    except Exception:  # noqa: BLE001
        return False


def puerto_ocupado(puerto):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.3)
        return s.connect_ex(("127.0.0.1", puerto)) == 0


def vigilante(servidor):
    """Apaga la app cuando ya no queda ninguna ventana abierta."""
    while True:
        time.sleep(1.5)
        ahora = time.time()
        if Estado.ultimo_latido is None:
            if ahora - Estado.inicio > LIMITE_PRIMERA_CONEXION_S:
                break
            continue
        if Estado.cierre_en and ahora - Estado.cierre_en > TRAS_CIERRE_S and Estado.ultimo_latido < Estado.cierre_en:
            break
        if ahora - Estado.ultimo_latido > SIN_LATIDO_S:
            break
    log("sin ventanas abiertas: cerrando")
    servidor.shutdown()


# -------------------------------------------------------------------------------------------------
# Ventana de aplicación
# -------------------------------------------------------------------------------------------------
def navegador_app():
    """Ruta de Edge o Chrome para abrir en modo aplicación (sin barras del navegador)."""
    candidatos = []
    for var in ("PROGRAMFILES(X86)", "PROGRAMFILES", "LOCALAPPDATA"):
        base = os.environ.get(var)
        if base:
            candidatos += [os.path.join(base, "Microsoft", "Edge", "Application", "msedge.exe"),
                           os.path.join(base, "Google", "Chrome", "Application", "chrome.exe")]
    candidatos += [shutil.which("msedge") or "", shutil.which("chrome") or ""]
    return next((c for c in candidatos if c and os.path.isfile(c)), None)


def geometria_ventana():
    """Tamaño y posición de la ventana ajustados al área útil de la pantalla de cada PC."""
    try:
        class RECT(ctypes.Structure):
            _fields_ = [("l", ctypes.c_long), ("t", ctypes.c_long), ("r", ctypes.c_long), ("b", ctypes.c_long)]
        ctypes.windll.user32.SetProcessDPIAware()
        area = RECT()
        ctypes.windll.user32.SystemParametersInfoW(0x30, 0, ctypes.byref(area), 0)  # SPI_GETWORKAREA
        aw, ah = area.r - area.l, area.b - area.t
        escala = ctypes.windll.user32.GetDpiForSystem() / 96 if hasattr(ctypes.windll.user32, "GetDpiForSystem") else 1
        # Chrome/Edge interpretan --window-size en píxeles lógicos (sin escala de Windows)
        w, h = min(1500, int(aw / escala * 0.96)), min(940, int(ah / escala * 0.94))
        x, y = int((aw / escala - w) / 2 + area.l / escala), int((ah / escala - h) / 2 + area.t / escala)
        return [f"--window-size={w},{h}", f"--window-position={max(0, x)},{max(0, y)}"]
    except Exception:  # noqa: BLE001
        return ["--start-maximized"]


def abrir_ventana(url):
    if os.environ.get("LOCALIZADOR_SIN_NAVEGADOR"):
        return
    exe = navegador_app()
    if exe:
        try:
            subprocess.Popen([exe, f"--app={url}", *geometria_ventana(), "--no-first-run"],
                             creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), close_fds=True)
            return
        except OSError:
            pass
    webbrowser.open(url)


def main():
    # 1. Si ya está abierto, solo abrir otra ventana
    for p in range(PUERTO_INICIAL, PUERTO_INICIAL + 5):
        if es_nuestro(p):
            log(f"ya estaba abierto en el puerto {p}")
            abrir_ventana(f"http://127.0.0.1:{p}/")
            return
    # Evita dos arranques simultáneos (doble clic repetido)
    try:
        ctypes.windll.kernel32.CreateMutexW(None, False, f"Global\\LocalizadorFallas_Conelsur_{PUERTO_INICIAL}")
        if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
            return
    except AttributeError:
        pass  # fuera de Windows

    if not os.path.isfile(os.path.join(WEB, "index.html")):
        raise FileNotFoundError(f"No se encontró la app en {WEB}")

    servidor = None
    for p in range(PUERTO_INICIAL, PUERTO_INICIAL + 30):
        if puerto_ocupado(p):
            continue
        try:
            servidor = Servidor(("127.0.0.1", p), Manejador)
            break
        except OSError:
            continue
    if servidor is None:
        raise RuntimeError(f"No se encontró un puerto libre entre {PUERTO_INICIAL} y {PUERTO_INICIAL + 30}.")
    url = f"http://127.0.0.1:{servidor.server_address[1]}/"
    log(f"iniciado en {url} · web={WEB}")

    threading.Thread(target=vigilante, args=(servidor,), daemon=True).start()
    abrir_ventana(url)
    servidor.serve_forever(poll_interval=0.5)
    servidor.server_close()
    log("servidor detenido")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001
        import traceback
        traceback.print_exc()
        mensaje(f"No se pudo iniciar el Localizador de Fallas:\n{e}\n\nDetalle en: {LOG}", error=True)
        os._exit(1)
    os._exit(0)
