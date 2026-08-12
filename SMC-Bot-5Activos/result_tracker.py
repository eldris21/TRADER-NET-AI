"""
result_tracker.py — Gestiona las posiciones ya abiertas por este bot
(filtradas por magic_number): mueve a breakeven cuando el precio ha
recorrido BREAKEVEN_AT_PCT_TO_TP1 hacia el TP1, y activa un trailing
stop basado en ATR una vez que está en breakeven.

Corre en un loop separado (o se integra al ciclo principal de
bot_engine.py) — aquí se deja como módulo independiente para poder
correrlo cada pocos segundos sin esperar el ciclo completo de señales.
"""

import logging
import time

import MetaTrader5 as mt5

import config
import data_engine
import structure

logger = logging.getLogger("result_tracker")


def _posiciones_del_bot():
    posiciones = mt5.positions_get()
    if posiciones is None:
        return []
    return [p for p in posiciones if p.magic == config.MAGIC_NUMBER]


def _mover_a_breakeven(posicion) -> None:
    nuevo_sl = posicion.price_open
    request = {
        "action": mt5.TRADE_ACTION_SLTP,
        "symbol": posicion.symbol,
        "position": posicion.ticket,
        "sl": nuevo_sl,
        "tp": posicion.tp,
    }
    result = mt5.order_send(request)
    if result and result.retcode == mt5.TRADE_RETCODE_DONE:
        logger.info("Breakeven aplicado a ticket %s (%s)", posicion.ticket, posicion.symbol)
    else:
        logger.warning("No se pudo aplicar breakeven a ticket %s: %s", posicion.ticket, result)


def _aplicar_trailing(posicion, atr_actual: float) -> None:
    distancia = atr_actual * config.TRAILING_ATR_MULT

    if posicion.type == mt5.ORDER_TYPE_BUY:
        nuevo_sl = posicion.price_current - distancia
        mejora = nuevo_sl > posicion.sl
    else:
        nuevo_sl = posicion.price_current + distancia
        mejora = nuevo_sl < posicion.sl

    if not mejora:
        return  # el trailing solo se mueve a favor, nunca en contra

    request = {
        "action": mt5.TRADE_ACTION_SLTP,
        "symbol": posicion.symbol,
        "position": posicion.ticket,
        "sl": round(nuevo_sl, 5),
        "tp": posicion.tp,
    }
    result = mt5.order_send(request)
    if result and result.retcode == mt5.TRADE_RETCODE_DONE:
        logger.info("Trailing actualizado ticket %s -> SL %.5f", posicion.ticket, nuevo_sl)


def gestionar_posiciones() -> None:
    for posicion in _posiciones_del_bot():
        # ¿Ya está en breakeven? (SL == precio de entrada, con tolerancia)
        en_breakeven = abs(posicion.sl - posicion.price_open) < 1e-6

        if not en_breakeven and posicion.tp:
            distancia_total_tp = abs(posicion.tp - posicion.price_open)
            if distancia_total_tp <= 0:
                continue
            if posicion.type == mt5.ORDER_TYPE_BUY:
                avance = posicion.price_current - posicion.price_open
            else:
                avance = posicion.price_open - posicion.price_current

            pct_avance = avance / distancia_total_tp
            if pct_avance >= config.BREAKEVEN_AT_PCT_TO_TP1:
                _mover_a_breakeven(posicion)
            continue  # no aplicar trailing en el mismo ciclo que el breakeven

        if en_breakeven:
            df_m1 = data_engine.obtener_velas(posicion.symbol, "M1", cantidad=50)
            if df_m1.empty:
                continue
            atr_actual = structure.calcular_atr(df_m1)
            _aplicar_trailing(posicion, atr_actual)


def main() -> None:
    if not data_engine.conectar():
        logger.error("No se pudo conectar a MT5.")
        return
    logger.info("result_tracker iniciado (breakeven %.0f%%, trailing ATR x%.1f)",
                config.BREAKEVEN_AT_PCT_TO_TP1 * 100, config.TRAILING_ATR_MULT)
    try:
        while True:
            gestionar_posiciones()
            time.sleep(15)
    except KeyboardInterrupt:
        logger.info("Detenido manualmente.")
    finally:
        data_engine.desconectar()


if __name__ == "__main__":
    main()
