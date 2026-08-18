"""
config.py — Configuración central del bot Golden Zone multi-activo.

Estrategia única (port del indicador "Impulso + Golden Zone [IGZ] v4"):
  - Swings confirmados por giro de REV_MULT_ATR x ATR en velas cerradas (M5).
  - COMPRA: par HL -> nuevo HH => Golden Zone = 50%-61.8% del fibo HL->HH.
  - VENTA : par LH -> nuevo LL => espejo.
  - Entrada: ORDEN LÍMITE en el nivel 50%.
  - Zona invalidada (y orden cancelada) si el precio cierra más allá del ancla.

Aplica a los 5 activos definidos en SYMBOLS. Opera sin restricción de
killzone (24/5, según horario de mercado de cada símbolo).
"""

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

load_dotenv()  # carga variables desde el archivo .env en la misma carpeta

# ============================================================
# SÍMBOLOS
# ============================================================
# IMPORTANTE: ajusta estos nombres exactos al como los expone tu
# broker (XMGlobal). Algunos brokers agregan sufijos como ".m",
# ".pro", "cash", etc. Verifica en MT5 -> Market Watch antes de
# correr en real.

# SOLO GOLD ACTIVO por decisión del usuario (2026-08-13). Los demás
# quedan PAUSADOS hasta nuevo aviso — para reactivar uno, descoméntalo.
SYMBOLS = [
    "GOLD",        # Oro — confirmado con tu broker
    # "US100Cash", # Nasdaq — PAUSADO hasta nuevo aviso
    # "US30Cash",  # Dow Jones — PAUSADO hasta nuevo aviso
    # "EURUSD",    # PAUSADO hasta nuevo aviso
    # "SILVER",    # Plata — PAUSADO hasta nuevo aviso
]

# ============================================================
# IDENTIFICACIÓN / INFRAESTRUCTURA (reutilizada de TradingPro-Nasdaq)
# ============================================================
MAGIC_NUMBER = 20260801

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://cgvidgcgtuzgcuaszqsg.supabase.co")
# OJO: para ESCRIBIR (INSERT/UPDATE) el bot necesita la service_role key,
# NO la anon key que usa el dashboard (esa es solo lectura pública).
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")  # canal "Nasdaq & US30 Signals"

# ============================================================
# GESTIÓN DE RIESGO
# ============================================================
MAX_LOSSES_PER_DAY_TOTAL = 3     # pérdidas: compartido entre todos los símbolos activos
MAX_SIGNALS_PER_DAY_TOTAL = 6    # máx. señales EJECUTADAS por día; al llegar, el bot
                                 # deja de operar hasta mañana (igual que con las pérdidas)

# ============================================================
# LOTAJE FIJO POR SÍMBOLO
# ============================================================
# Lote fijo definido manualmente por símbolo. Los símbolos que aún no
# tienen valor asignado usan LOTE_DEFAULT_SEGURO hasta que se definan
# aquí explícitamente (los lotes finales se definirán al terminar la
# configuración del bot).
FIXED_LOTS = {
    "GOLD": 0.05,          # definido por el usuario (2026-08-13)
    # "US100Cash": 1.0,    # símbolo pausado
    # "US30Cash": ...,   # pendiente de definir
    # "EURUSD": ...,     # pendiente de definir
    # "SILVER": ...,     # pendiente de definir
}
LOTE_DEFAULT_SEGURO = 0.01  # usado SOLO si el símbolo no está en FIXED_LOTS todavía

# Breakeven + trailing
BREAKEVEN_AT_R = 1.0             # mueve el SL a la entrada cuando la operación va ganando
                                 # este múltiplo del riesgo (1.0 = al llegar a 1:1).
                                 # Se mide contra la distancia entrada->SL, así que sigue
                                 # siendo correcto aunque cambie el TP1_RR.
TRAILING_ATR_MULT = 1.2          # trailing stop = ATR * este múltiplo (pendiente de implementar)

# ============================================================
# PARÁMETROS DE ESTRATEGIA — GOLDEN ZONE (IGZ)
# ============================================================
TF_ESTRUCTURA = "M1"             # timeframe donde se calculan swings y zonas (cambiado de M5 el 2026-08-17)
VELAS_ANALISIS = 1500            # velas cerradas por ciclo (~25h de M1, para que la estructura tenga contexto)

ATR_PERIOD = 14
REV_MULT_ATR = 4.0               # "Umbral de giro (x ATR)" del indicador:
                                 # un swing se confirma al cerrar en contra del
                                 # extremo más de este múltiplo de ATR.
                                 # Alto (3-6) = solo estructura mayor.

FIBO_ZONA_INICIO = 0.50          # borde de la Golden Zone más cercano al extremo
FIBO_ZONA_FIN = 0.618            # borde más cercano al ancla
# La entrada es una ORDEN LÍMITE en el nivel FIBO_ZONA_INICIO (50%).

ATR_SL_BUFFER_MULT = 0.25        # colchón extra del SL más allá del ancla, en múltiplos de ATR

TP1_RR = 2.0                     # TP1 en múltiplos del riesgo (SL) — R:R 1:2
TP2_RR = 2.5                     # TP2 en múltiplos del riesgo (SL) — informativo,
                                 # la orden lleva TP1 hasta que exista gestor de posiciones

# Sin restricción de killzone para esta estrategia.
RESTRINGIR_A_KILLZONE = False

# Pendiente: filtro de noticias de alto impacto (NFP, CPI, FOMC).
NEWS_FILTER_ENABLED = False


# ============================================================
# COMPATIBILIDAD — parámetros de la estrategia anterior que aún
# usan módulos viejos (structure.py / result_tracker.py).
# Eliminar cuando esos módulos se adapten o se retiren.
# ============================================================
PIVOT_LOOKBACK = 3
BREAKEVEN_AT_PCT_TO_TP1 = 0.70   # solo para result_tracker viejo; el bot usa BREAKEVEN_AT_R
TF_IMPULSO = "M5"
TF_CONFIRMACION = "M1"
FIBO_RETROCESO_MINIMO = 0.50
FIBO_RETROCESO_MAXIMO = 0.786
FIBO_ENTRADA_EN_BOS = 0.50
MIN_IMPULSO_ATR_MULT = 3.0
RISK_PERCENT_PER_TRADE = 6.0


@dataclass
class RuntimeState:
    """Estado compartido en memoria durante la ejecución del bot."""
    losses_today: int = 0
    last_reset_date: str = ""  # 'YYYY-MM-DD', para saber cuándo resetear el contador
    signals_sent_ids: set = field(default_factory=set)  # evita reenviar la misma señal
    signals_today: int = 0     # señales ejecutadas hoy (respaldo en memoria del conteo en Supabase)
    limite_avisado: str = ""   # 'YYYY-MM-DD' del último aviso de límite, para avisar solo una vez
