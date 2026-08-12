"""
data_engine.py — Conexión a MT5 y obtención de velas para los 5 símbolos.

Requiere el paquete MetaTrader5 (solo funciona en Windows, con el
terminal MT5 abierto y logueado en la cuenta correspondiente).
"""

import logging
from datetime import datetime

import MetaTrader5 as mt5
import pandas as pd

import config

logger = logging.getLogger("data_engine")

TIMEFRAME_MAP = {
    "M1": mt5.TIMEFRAME_M1,
    "M5": mt5.TIMEFRAME_M5,
    "M15": mt5.TIMEFRAME_M15,
}


def conectar() -> bool:
    """Inicializa la conexión con la terminal MT5 ya abierta y logueada."""
    if not mt5.initialize():
        logger.error("No se pudo inicializar MT5: %s", mt5.last_error())
        return False
    logger.info("Conectado a MT5 — cuenta %s", mt5.account_info().login if mt5.account_info() else "?")
    return True


def desconectar() -> None:
    mt5.shutdown()


def verificar_simbolos() -> list[str]:
    """
    Confirma que cada símbolo en config.SYMBOLS existe y está visible
    en Market Watch. Devuelve la lista de símbolos que SÍ están OK;
    loggea un error por cada uno que falte (revisar sufijo del broker).
    """
    disponibles = []
    for symbol in config.SYMBOLS:
        info = mt5.symbol_info(symbol)
        if info is None:
            logger.error(
                "Símbolo '%s' no existe en este broker. Revisa el nombre exacto "
                "en Market Watch (puede tener sufijo, ej. '%s.m').", symbol, symbol
            )
            continue
        if not info.visible:
            mt5.symbol_select(symbol, True)
        disponibles.append(symbol)
    return disponibles


def obtener_velas(symbol: str, timeframe: str, cantidad: int = 300) -> pd.DataFrame:
    """
    Devuelve un DataFrame con las últimas 'cantidad' velas cerradas
    de un símbolo/timeframe, ordenadas de más antiguo a más reciente.
    """
    tf = TIMEFRAME_MAP[timeframe]
    rates = mt5.copy_rates_from_pos(symbol, tf, 1, cantidad)  # desde pos 1 = excluye la vela en formación
    if rates is None or len(rates) == 0:
        logger.warning("Sin datos para %s %s", symbol, timeframe)
        return pd.DataFrame()

    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    return df[["time", "open", "high", "low", "close", "tick_volume"]]


def precio_actual(symbol: str) -> float | None:
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        return None
    return float(tick.bid)


def info_simbolo(symbol: str):
    return mt5.symbol_info(symbol)
