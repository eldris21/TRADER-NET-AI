"""
config.py — Configuración central del bot SMC multi-activo.

Estrategia única: Impulso (M5) + Retroceso válido >=50% Fibonacci
+ confirmación CHoCH -> BOS en M1 + entrada al 50% de la pierna del BOS.

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
# correr en real. Los que traen duda están comentados con nota.

SYMBOLS = [
    "US100Cash",   # Nasdaq
    "US30Cash",    # Dow Jones
    "XAUUSD",      # Oro — confirma si tu broker usa "GOLD" en vez de XAUUSD
    "EURUSD",
    "XAGUSD",      # Plata — confirma nombre exacto en tu broker (a veces "SILVER")
]

# ============================================================
# IDENTIFICACIÓN / INFRAESTRUCTURA (reutilizada de TradingPro-Nasdaq)
# ============================================================
MAGIC_NUMBER = 20260801

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://cgvidgcgtuzgcuaszqsg.supabase.co")
# OJO: para ESCRIBIR (INSERT/UPDATE) el bot necesita la service_role key,
# NO la anon key que usa el dashboard (esa es solo lectura pública).
# Cópiala desde Supabase -> Project Settings -> API -> service_role.
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")  # canal "Nasdaq & US30 Signals" / @ea500drbot

# ============================================================
# GESTIÓN DE RIESGO
# ============================================================
MAX_LOSSES_PER_DAY_TOTAL = 3     # compartido entre los 5 símbolos, no por símbolo
RISK_PERCENT_PER_TRADE = 0.5     # % del balance arriesgado por operación (ajustar)
ATR_PERIOD = 14
ATR_SL_BUFFER_MULT = 0.25        # colchón extra sobre el extremo del CHoCH, en múltiplos de ATR

# Breakeven + trailing (mismo patrón usado en TradingProEA para oro)
BREAKEVEN_AT_PCT_TO_TP1 = 0.70   # mueve a breakeven cuando el precio recorre 70% de la distancia a TP1
TRAILING_ATR_MULT = 1.2          # trailing stop = ATR * este múltiplo, activa después del breakeven

# ============================================================
# PARÁMETROS DE ESTRATEGIA (Impulso + Retroceso + CHoCH/BOS)
# ============================================================
TF_IMPULSO = "M5"                 # timeframe donde se mide el impulso y el fibo
TF_CONFIRMACION = "M1"            # timeframe donde se busca CHoCH -> BOS

FIBO_RETROCESO_MINIMO = 0.50      # retroceso debe alcanzar AL MENOS 50% del impulso
FIBO_RETROCESO_MAXIMO = 0.786     # más allá de esto se considera impulso invalidado (no es "retroceso", es reversión)
FIBO_ENTRADA_EN_BOS = 0.50        # la entrada se ejecuta al 50% de la pierna del BOS en M1

PIVOT_LOOKBACK = 3                # velas a cada lado para confirmar un swing high/low (fractal simple)
MIN_IMPULSO_ATR_MULT = 3.0        # el impulso en M5 debe medir al menos N * ATR(M5) para no operar ruido

TP1_RR = 1.5                      # TP1 en múltiplos del riesgo (SL)
TP2_RR = 2.5                      # TP2 en múltiplos del riesgo (SL)

# Sin restricción de killzone para esta estrategia (a diferencia del bot de oro).
RESTRINGIR_A_KILLZONE = False

# Pendiente: filtro de noticias de alto impacto (NFP, CPI, FOMC). No implementado
# todavía en este bot — si operas EURUSD/XAUUSD/XAGUSD cerca de estos eventos,
# hazlo manualmente hasta portar news_engine.py del bot de oro.
NEWS_FILTER_ENABLED = False


@dataclass
class RuntimeState:
    """Estado compartido en memoria durante la ejecución del bot."""
    losses_today: int = 0
    last_reset_date: str = ""  # 'YYYY-MM-DD', para saber cuándo resetear el contador
    signals_sent_ids: set = field(default_factory=set)  # evita reenviar la misma señal
