"""
signal_engine.py — Orquesta la estrategia completa por símbolo:

1. En M5: identifica el último impulso válido (filtrado por ATR).
2. Evalúa si el precio actual ya retrocedió >=50% (y <=78.6%) de ese impulso.
   Si no, descarta — no se opera.
3. Si el retroceso es válido, baja a M1 y busca CHoCH en la dirección
   del impulso original.
4. Si hay CHoCH, busca BOS posterior en la misma dirección.
5. Si hay BOS, calcula la entrada al 50% de esa pierna del BOS,
   el SL (más allá del pivote roto por el CHoCH + colchón ATR),
   y TP1/TP2 por múltiplos de R:R.

Devuelve un objeto Senal listo para pasar a bot_engine.py, o None si
no se cumplen todas las condiciones.
"""

import logging
from dataclasses import dataclass
from typing import Optional

import config
import data_engine
import structure

logger = logging.getLogger("signal_engine")


@dataclass
class Senal:
    symbol: str
    direccion: str            # "BUY" / "SELL"
    precio_entrada: float
    stop_loss: float
    take_profit: float        # TP1 (el que se guarda como take_profit principal en idx_senales)
    take_profit_2: float      # TP2, se guarda en metadata
    estrategia: str = "Impulso+Retroceso50+CHoCH-BOS-M1"
    metadata: Optional[dict] = None


def _direccion_a_orden(direccion_impulso: str) -> str:
    return "BUY" if direccion_impulso == "ALCISTA" else "SELL"


def evaluar_symbol(symbol: str) -> Optional[Senal]:
    """Corre el pipeline completo de la estrategia para un símbolo. Devuelve Senal o None."""

    df_m5 = data_engine.obtener_velas(symbol, config.TF_IMPULSO, cantidad=300)
    if df_m5.empty or len(df_m5) < config.PIVOT_LOOKBACK * 2 + 5:
        return None

    impulso = structure.identificar_ultimo_impulso(df_m5)
    if impulso is None:
        return None  # no hay impulso reciente lo suficientemente grande

    precio_ahora = data_engine.precio_actual(symbol)
    if precio_ahora is None:
        return None

    retroceso = structure.evaluar_retroceso(impulso, precio_ahora)
    if not retroceso.valido:
        logger.debug(
            "%s: retroceso %.1f%% no válido (necesita %.0f%%-%.0f%%)",
            symbol, retroceso.nivel_alcanzado * 100,
            config.FIBO_RETROCESO_MINIMO * 100, config.FIBO_RETROCESO_MAXIMO * 100,
        )
        return None

    # Retroceso válido -> bajar a M1 a buscar las dos confirmaciones
    df_m1 = data_engine.obtener_velas(symbol, config.TF_CONFIRMACION, cantidad=300)
    if df_m1.empty:
        return None

    choch = structure.buscar_choch(df_m1, impulso.direccion)
    if choch is None:
        logger.debug("%s: retroceso válido pero sin CHoCH en M1 todavía", symbol)
        return None

    bos = structure.buscar_bos(df_m1, choch)
    if bos is None:
        logger.debug("%s: CHoCH confirmado pero sin BOS en M1 todavía", symbol)
        return None

    # Las dos confirmaciones están — calcular niveles de la operación
    entrada = structure.calcular_entrada_50_bos(df_m1, choch, bos)

    atr_m1 = structure.calcular_atr(df_m1)
    buffer = atr_m1 * config.ATR_SL_BUFFER_MULT

    if choch.direccion == "ALCISTA":
        sl = choch.pivot_roto.price - buffer
        riesgo = entrada - sl
        tp1 = entrada + riesgo * config.TP1_RR
        tp2 = entrada + riesgo * config.TP2_RR
    else:
        sl = choch.pivot_roto.price + buffer
        riesgo = sl - entrada
        tp1 = entrada - riesgo * config.TP1_RR
        tp2 = entrada - riesgo * config.TP2_RR

    if riesgo <= 0:
        logger.warning("%s: riesgo calculado <= 0, se descarta señal (revisar datos)", symbol)
        return None

    return Senal(
        symbol=symbol,
        direccion=_direccion_a_orden(choch.direccion),
        precio_entrada=round(entrada, 5),
        stop_loss=round(sl, 5),
        take_profit=round(tp1, 5),
        take_profit_2=round(tp2, 5),
        metadata={
            "impulso_inicio": impulso.inicio.price,
            "impulso_fin": impulso.fin.price,
            "retroceso_pct": round(retroceso.nivel_alcanzado * 100, 2),
            "choch_pivot": choch.pivot_roto.price,
            "bos_precio": bos.precio_cierre,
            "atr_m1": round(atr_m1, 5),
            "rr_tp1": config.TP1_RR,
            "rr_tp2": config.TP2_RR,
        },
    )


def evaluar_todos_los_simbolos(simbolos_activos: list[str]) -> list[Senal]:
    """Corre evaluar_symbol() para cada símbolo disponible y devuelve las señales encontradas."""
    senales = []
    for symbol in simbolos_activos:
        try:
            senal = evaluar_symbol(symbol)
            if senal:
                senales.append(senal)
                logger.info("Señal detectada: %s %s @ %s", senal.symbol, senal.direccion, senal.precio_entrada)
        except Exception:
            logger.exception("Error evaluando %s", symbol)
    return senales
