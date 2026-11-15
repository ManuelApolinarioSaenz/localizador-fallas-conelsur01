@echo off
REM ==========================================================================
REM  Genera LocalizadorFallas.exe (un solo archivo, sin Python en la PC destino)
REM
REM  Requisitos SOLO en la PC que compila:
REM    - Python con: streamlit pandas numpy (para generar_datos.py) y pyinstaller
REM      Indique su python.exe en la variable PYTHON (abajo) o tenga uno en PATH.
REM    - escritorio\config.json con el token de Mapbox (no se sube a GitHub):
REM        {"mapbox_token": "pk...."}
REM  Resultado: escritorio\dist\LocalizadorFallas.exe
REM ==========================================================================
setlocal
cd /d "%~dp0"
if "%PYTHON%"=="" set PYTHON=python

echo [1/2] Generando datos (KMZ, centros poblados, vias, rios)...
"%PYTHON%" generar_datos.py || goto :error

if not exist config.json (
  echo   AVISO: no hay config.json - el .exe usara mapas de Carto/Esri sin Mapbox.
  echo {}> config.json
)

echo [2/2] Empaquetando el .exe...
"%PYTHON%" -m PyInstaller --noconfirm --clean --onefile --noconsole --name LocalizadorFallas ^
  --icon "%~dp0icono.ico" ^
  --version-file "%~dp0version_info.txt" ^
  --add-data "%~dp0web;web" --add-data "%~dp0config.json;." ^
  --exclude-module tkinter --exclude-module numpy --exclude-module pandas --exclude-module PIL ^
  --exclude-module streamlit --exclude-module pyarrow ^
  --distpath dist --workpath build --specpath build ^
  servidor.py || goto :error

echo.
echo Listo: %~dp0dist\LocalizadorFallas.exe
exit /b 0

:error
echo.
echo *** Error al generar el ejecutable ***
exit /b 1
