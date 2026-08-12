"""
structure.py — Detección de estructura de mercado (SMC) reutilizable
para cualquier símbolo y timeframe: pivotes (swings), impulsos,
Fibonacci de retroceso, y cambios de estructura (CHoCH / BOS).

Todo esto trabaja sobre un DataFrame de pandas con columnas:
['time', 'open', 'high', 'low', 'close'] ordenado de más antiguo a
más reciente (como lo entrega MT5 copy_rates_from_pos).
"""

from dataclasses import dataclass
from typing import Literal, Optional

import pandas as pd

import config


Direction = Literal["ALCISTA", "BAJISTA"]


@dataclass
class Pivot:
    index: int
    time: pd.Timestamp
    price: float
    tipo: Literal["HIGH", "LOW"]


@dataclass
class Impulso:
    inicio: Pivot          # extremo donde comenzó el impulso (0% / 100% del fibo)
    fin: Pivot              # extremo donde terminó el impulso (100% / 0% del fibo)
    direccion: Direction


@dataclass
class Retroceso:
    impulso: Impulso
    nivel_alcanzado: float   # 0.0 - 1.0, qué tan profundo llegó el retroceso
    precio_actual: float
    valido: bool             # True si nivel_alcanzado >= FIBO_RETROCESO_MINIMO y <= MAXIMO


@dataclass
class CambioEstructura:
    tipo: Literal["CHOCH", "BOS"]
    direccion: Direction
    pivot_roto: Pivot        # el swing que se rompió para confirmar el cambio
    vela_confirmacion: int   # índice de la vela que cerró rompiendo el pivote
    precio_cierre: float


# ============================================================
# PIVOTES (fractales simples)
# ============================================================

def detectar_pivotes(df: pd.DataFrame, lookback: int = config.PIVOT_LOOKBACK) -> list[Pivot]:
    """
    Fractal simple: una vela es pivote HIGH si su high es el máximo
    entre 'lookback' velas antes y después; análogo para LOW.
    """
    pivotes: list[Pivot] = []
    n = len(df)
    for i in range(lookback, n - lookback):
        ventana = df.iloc[i - lookback: i + lookback + 1]
        vela = df.iloc[i]

        if vela["high"] == ventana["high"].max() and (ventana["high"] == vela["high"]).sum() == 1:
            pivotes.append(Pivot(index=i, time=vela["time"], price=vela["high"], tipo="HIGH"))

        if vela["low"] == ventana["low"].min() and (ventana["low"] == vela["low"]).sum() == 1:
            pivotes.append(Pivot(index=i, time=vela["time"], price=vela["low"], tipo="LOW"))

    pivotes.sort(key=lambda p: p.index)
    return pivotes


# ============================================================
# IMPULSO (timeframe superior, ej. M5)
# ============================================================

def calcular_atr(df: pd.DataFrame, periodo: int = config.ATR_PERIOD) -> float:
    """ATR simple (SMA de True Range) sobre las últimas 'periodo' velas cerradas."""
    high = df["high"]
    low = df["low"]
    close_prev = df["close"].shift(1)

    tr = pd.concat([
        (high - low).abs(),
        (high - close_prev).abs(),
        (low - close_prev).abs(),
    ], axis=1).max(axis=1)

    return float(tr.rolling(periodo).mean().iloc[-1])


def identificar_ultimo_impulso(df: pd.DataFrame) -> Optional[Impulso]:
    """
    Toma los pivotes más recientes y arma la última pierna direccional
    (de un LOW confirmado a un HIGH confirmado, o viceversa), filtrando
    impulsos demasiado pequeños (ruido) según MIN_IMPULSO_ATR_MULT.
    """
    pivotes = detectar_pivotes(df)
    if len(pivotes) < 2:
        return None

    ultimo = pivotes[-1]
    anterior = pivotes[-2]

    # Debe ser un par HIGH/LOW alternado para ser un impulso válido
    if ultimo.tipo == anterior.tipo:
        return None

    if ultimo.tipo == "HIGH":
        direccion: Direction = "ALCISTA"
        inicio, fin = anterior, ultimo
    else:
        direccion = "BAJISTA"
        inicio, fin = anterior, ultimo

    atr = calcular_atr(df)
    tamano_impulso = abs(fin.price - inicio.price)

    if atr <= 0 or tamano_impulso < atr * config.MIN_IMPULSO_ATR_MULT:
        return None  # impulso muy pequeño frente al ATR actual, se descarta como ruido

    return Impulso(inicio=inicio, fin=fin, direccion=direccion)


def evaluar_retroceso(impulso: Impulso, precio_actual: float) -> Retroceso:
    """
    Calcula qué tan profundo ha retrocedido el precio dentro del impulso
    (0.0 = no ha retrocedido nada, 1.0 = retrocedió el 100% del impulso).
    """
    rango = abs(impulso.fin.price - impulso.inicio.price)
    if rango == 0:
        return Retroceso(impulso=impulso, nivel_alcanzado=0.0, precio_actual=precio_actual, valido=False)

    if impulso.direccion == "ALCISTA":
        # el impulso subió, el retroceso baja desde impulso.fin.price
        recorrido = impulso.fin.price - precio_actual
    else:
        recorrido = precio_actual - impulso.fin.price

    nivel = recorrido / rango
    valido = config.FIBO_RETROCESO_MINIMO <= nivel <= config.FIBO_RETROCESO_MAXIMO

    return Retroceso(impulso=impulso, nivel_alcanzado=nivel, precio_actual=precio_actual, valido=valido)


# ============================================================
# CHoCH / BOS (timeframe de confirmación, ej. M1)
# ============================================================

def buscar_choch(df_m1: pd.DataFrame, direccion_impulso_original: Direction) -> Optional[CambioEstructura]:
    """
    Busca un CHoCH en M1: una ruptura de estructura EN CONTRA de la
    tendencia menor reciente de M1, que señala el posible fin del
    retroceso y el regreso a la dirección del impulso original.

    Ej: impulso original alcista -> precio retrocede (bajista en M1)
    -> CHoCH = rompe un HIGH menor en M1 hacia arriba (cambia de carácter).
    """
    pivotes = detectar_pivotes(df_m1)
    if len(pivotes) < 2:
        return None

    # Dirección que debe romper el CHoCH: la misma del impulso original
    direccion_esperada = direccion_impulso_original

    for i in range(len(pivotes) - 1, 0, -1):
        pivot = pivotes[i]
        # Buscamos el pivote CONTRARIO a la dirección esperada más reciente
        # (el que la estructura menor en contra dejó), y confirmamos que
        # una vela posterior cerró rompiéndolo en la dirección esperada.
        if direccion_esperada == "ALCISTA" and pivot.tipo == "HIGH":
            velas_despues = df_m1.iloc[pivot.index + 1:]
            ruptura = velas_despues[velas_despues["close"] > pivot.price]
            if not ruptura.empty:
                idx_ruptura = ruptura.index[0]
                return CambioEstructura(
                    tipo="CHOCH",
                    direccion="ALCISTA",
                    pivot_roto=pivot,
                    vela_confirmacion=idx_ruptura,
                    precio_cierre=float(df_m1.loc[idx_ruptura, "close"]),
                )
        if direccion_esperada == "BAJISTA" and pivot.tipo == "LOW":
            velas_despues = df_m1.iloc[pivot.index + 1:]
            ruptura = velas_despues[velas_despues["close"] < pivot.price]
            if not ruptura.empty:
                idx_ruptura = ruptura.index[0]
                return CambioEstructura(
                    tipo="CHOCH",
                    direccion="BAJISTA",
                    pivot_roto=pivot,
                    vela_confirmacion=idx_ruptura,
                    precio_cierre=float(df_m1.loc[idx_ruptura, "close"]),
                )

    return None


def buscar_bos(df_m1: pd.DataFrame, choch: CambioEstructura) -> Optional[CambioEstructura]:
    """
    Después de un CHoCH confirmado, busca el BOS: una ruptura ADICIONAL
    de estructura EN LA MISMA DIRECCIÓN del CHoCH (confirma que la
    continuación es real, no solo una reacción de un tramo).
    """
    df_post_choch = df_m1.iloc[choch.vela_confirmacion:].reset_index(drop=True)
    pivotes = detectar_pivotes(df_post_choch)

    for pivot in pivotes:
        if choch.direccion == "ALCISTA" and pivot.tipo == "HIGH":
            velas_despues = df_post_choch.iloc[pivot.index + 1:]
            ruptura = velas_despues[velas_despues["close"] > pivot.price]
            if not ruptura.empty:
                idx_local = ruptura.index[0]
                idx_global = idx_local + choch.vela_confirmacion
                return CambioEstructura(
                    tipo="BOS",
                    direccion="ALCISTA",
                    pivot_roto=pivot,
                    vela_confirmacion=idx_global,
                    precio_cierre=float(df_post_choch.loc[idx_local, "close"]),
                )
        if choch.direccion == "BAJISTA" and pivot.tipo == "LOW":
            velas_despues = df_post_choch.iloc[pivot.index + 1:]
            ruptura = velas_despues[velas_despues["close"] < pivot.price]
            if not ruptura.empty:
                idx_local = ruptura.index[0]
                idx_global = idx_local + choch.vela_confirmacion
                return CambioEstructura(
                    tipo="BOS",
                    direccion="BAJISTA",
                    pivot_roto=pivot,
                    vela_confirmacion=idx_global,
                    precio_cierre=float(df_post_choch.loc[idx_local, "close"]),
                )

    return None


def calcular_entrada_50_bos(df_m1: pd.DataFrame, choch: CambioEstructura, bos: CambioEstructura) -> float:
    """
    La entrada se ejecuta al 50% de la pierna del BOS: la distancia
    entre el pivote roto por el CHoCH (origen de la pierna) y el
    precio donde se confirmó el BOS.
    """
    origen = choch.pivot_roto.price
    fin = bos.precio_cierre
    return origen + (fin - origen) * (1 - config.FIBO_ENTRADA_EN_BOS)
