@echo off
REM ============================================================
REM START_ALL.bat — Arranca los 3 procesos del bot SMC 5-activos:
REM   1. bot_engine.py       (genera señales y ejecuta órdenes)
REM   2. result_tracker.py   (breakeven + trailing de posiciones abiertas)
REM   3. sync_trades_supabase.py (sincroniza cierres hacia el dashboard)
REM
REM Incluye detección básica de procesos duplicados para no abrir
REM dos instancias del mismo script por accidente.
REM ============================================================

setlocal

tasklist /FI "IMAGENAME eq python.exe" /FI "WINDOWTITLE eq bot_engine*" 2>NUL | find /I "python.exe" >NUL
if not errorlevel 1 (
    echo [AVISO] bot_engine.py ya parece estar corriendo. Cierra esa ventana antes de continuar.
    pause
    exit /b
)

echo Iniciando bot_engine.py...
start "bot_engine" cmd /k "cd /d %~dp0 && python bot_engine.py"

timeout /t 3 /nobreak >NUL

echo Iniciando result_tracker.py...
start "result_tracker" cmd /k "cd /d %~dp0 && python result_tracker.py"

timeout /t 3 /nobreak >NUL

echo Iniciando sync_trades_supabase.py...
start "sync_trades" cmd /k "cd /d %~dp0 && python sync_trades_supabase.py"

echo.
echo Los 3 procesos se abrieron en ventanas separadas.
echo Cierra cada ventana individualmente para detener ese proceso.
pause
