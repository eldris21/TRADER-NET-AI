@echo off
REM ============================================================
REM START_ALL.bat — Arranca el bot Golden Zone (IGZ).
REM
REM Desde la actualizacion del 2026-08-13, bot_engine.py hace TODO:
REM   - genera senales y coloca/cancela ordenes limite
REM   - sincroniza llenados y cierres hacia Supabase
REM   - aplica breakeven (SL a la entrada al alcanzar 1R)
REM
REM result_tracker.py y sync_trades_supabase.py quedan DESACTIVADOS:
REM son del bot anterior y harian el mismo trabajo en paralelo
REM (moverian los SL con reglas viejas y escribirian las mismas
REM filas en Supabase). Para reactivar uno, quitale el REM.
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

REM --- DESACTIVADO: gestor de posiciones del bot viejo (breakeven 70% + trailing) ---
REM start "result_tracker" cmd /k "cd /d %~dp0 && python result_tracker.py"

REM --- DESACTIVADO: sincronizador viejo de cierres (bot_engine ya lo hace) ---
REM start "sync_trades" cmd /k "cd /d %~dp0 && python sync_trades_supabase.py"

echo.
echo bot_engine iniciado en su propia ventana.
echo Cierra esa ventana para detener el bot.
pause
