"""
signal_engine.py — Estrategia GOLDEN ZONE estructural.

Port fiel del indicador Pine "Impulso + Golden Zone [IGZ] v4":

  COMPRAS: cuando existe un HL confirmado y después se confirma un nuevo HH,
           se proyecta el fibo desde ese HL (100%) hasta el HH (0%).
           Golden Zone = bloque 50% - 61.8%.
  VENTAS:  espejo — LH confirmado y después un nuevo LL.

  - Un swing se confirma cuando el precio CIERRA en contra del extremo
    más de REV_MULT_ATR * ATR (igual que el input "Umbral de giro" del
    indicador). Solo velas cerradas => sin repaint.
  - La zona vive hasta que el precio cierra más allá del ancla (HL/LH)
    => INVALIDADA, o hasta que un nuevo par estructural la reemplaza.

Traducción a operativa (decisiones del usuario, 2026-08-13):
  - Timeframe de estructura: M5 (config.TF_ESTRUCTURA).
  - Entrada: ORDEN LÍMITE en el nivel 50% del fibo (borde superior de la
    zona de compra / borde inferior de la zona de venta).
  - SL: en el ancla (HL/LH) ± colchón de ATR_SL_BUFFER_MULT * ATR.
  - TP1/TP2: múltiplos TP1_RR / TP2_RR del riesgo.

Interfaz hacia bot_engine (sin cambios):
  - clase Senal
  - evaluar_todos_los_simbolos(simbolos) -> list[Senal]
Interfaz nueva (para cancelar límites huérfanas):
  - zona_viva(symbol) -> dict | None
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

import pandas as pd

import config
import data_engine

logger = logging.getLogger("signal_engine")

ESTRATEGIA = f"IGZ-GoldenZone-{config.TF_ESTRUCTURA}"


@dataclass
class Senal:
    symbol: str
    estrategia: str
    direccion: str          # "BUY" | "SELL"
    precio_entrada: float   # nivel 50% del fibo (orden límite)
    stop_loss: float
    take_profit: float      # TP1
    take_profit_2: float    # TP2 (informativo; la orden lleva TP1)
    metadata: dict = field(default_factory=dict)


# Estado del módulo (en memoria):
#  - _zonas_emitidas: ids de zonas ya convertidas en señal, para no repetir.
#  - _zonas_vivas:    zona actualmente vigente por símbolo (o None), usada
#                     por bot_engine para cancelar órdenes límite huérfanas.
_zonas_emitidas: set[str] = set()
_zonas_vivas: dict[str, Optional[dict]] = {}


# ============================================================
# ATR estilo Pine (ta.atr usa RMA / suavizado de Wilder)
# ============================================================

def _atr_rma(df: pd.DataFrame, period: int) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)
    tr = pd.concat(
        [high - low, (high - prev_close).abs(), (low - prev_close).abs()],
        axis=1,
    ).max(axis=1)
    return tr.ewm(alpha=1.0 / period, adjust=False).mean()


# ============================================================
# MOTOR DE SWINGS + GOLDEN ZONE (réplica del script Pine)
# ============================================================

def _procesar_simbolo(symbol: str, df: pd.DataFrame) -> Optional[dict]:
    """
    Recorre las velas cerradas replicando el módulo 1 y 2 del indicador.
    Devuelve la zona VIVA al cierre de la última vela (dict) o None.

    dict de zona:
      direccion   "BUY"/"SELL"
      top, bot    bordes de la Golden Zone (50% y 61.8%)
      entrada     nivel 50% (top en compras, bot en ventas)
      anchor      HL/LH que ancla el fibo (nivel de invalidación)
      extremo     precio del HH/LL
      creada_en   timestamp (str) de la vela que confirmó el par
      tapped      True si el precio ya tocó la zona (mitigada)
      atr         ATR en la última vela (para el colchón del SL)
    """
    atr = _atr_rma(df, config.ATR_PERIOD)

    dir_ = 0                 # 1 alcista, -1 bajista, 0 sin iniciar
    ext_p = None             # extremo provisional del tramo actual
    last_hi_p = None; last_hi_t = None   # último swing high confirmado (precio, etiqueta)
    last_lo_p = None; last_lo_t = None   # último swing low confirmado

    zona: Optional[dict] = None

    o = df["open"].to_numpy(); h = df["high"].to_numpy()
    l = df["low"].to_numpy();  c = df["close"].to_numpy()
    t = df["time"].astype(str).to_numpy()
    a = atr.to_numpy()

    for i in range(len(df)):
        if pd.isna(a[i]) or a[i] <= 0:
            continue

        new_high = False; new_low = False
        conf_p = None; conf_tag = None

        # ---- módulo 1: motor de swings ----
        if dir_ == 0:
            dir_ = 1 if c[i] >= o[i] else -1
            ext_p = h[i] if dir_ == 1 else l[i]
        elif dir_ == 1:
            if h[i] > ext_p:
                ext_p = h[i]
            elif c[i] < ext_p - config.REV_MULT_ATR * a[i]:
                conf_tag = "H" if last_hi_p is None else ("HH" if ext_p > last_hi_p else "LH")
                last_hi_p = ext_p; last_hi_t = conf_tag
                new_high = True; conf_p = ext_p
                dir_ = -1; ext_p = l[i]
        else:
            if l[i] < ext_p:
                ext_p = l[i]
            elif c[i] > ext_p + config.REV_MULT_ATR * a[i]:
                conf_tag = "L" if last_lo_p is None else ("LL" if ext_p < last_lo_p else "HL")
                last_lo_p = ext_p; last_lo_t = conf_tag
                new_low = True; conf_p = ext_p
                dir_ = 1; ext_p = h[i]

        # ---- módulo 2: creación de la Golden Zone ----
        if new_high and conf_tag == "HH" and last_lo_p is not None and last_lo_t == "HL":
            rng = conf_p - last_lo_p
            zona = {
                "direccion": "BUY",
                "top": conf_p - config.FIBO_ZONA_INICIO * rng,   # 50%
                "bot": conf_p - config.FIBO_ZONA_FIN * rng,      # 61.8%
                "anchor": last_lo_p,
                "extremo": conf_p,
                "creada_en": t[i],
                "tapped": False,
            }
        elif new_low and conf_tag == "LL" and last_hi_p is not None and last_hi_t == "LH":
            rng = last_hi_p - conf_p
            zona = {
                "direccion": "SELL",
                "top": conf_p + config.FIBO_ZONA_FIN * rng,      # 61.8%
                "bot": conf_p + config.FIBO_ZONA_INICIO * rng,   # 50%
                "anchor": last_hi_p,
                "extremo": conf_p,
                "creada_en": t[i],
                "tapped": False,
            }

        # ---- módulo 2: mantenimiento (invalidación / mitigación) ----
        if zona is not None:
            invalida = (c[i] < zona["anchor"]) if zona["direccion"] == "BUY" else (c[i] > zona["anchor"])
            if invalida:
                zona = None
            elif not zona["tapped"] and l[i] <= zona["top"] and h[i] >= zona["bot"]:
                zona["tapped"] = True

    if zona is not None:
        zona["entrada"] = zona["top"] if zona["direccion"] == "BUY" else zona["bot"]
        zona["atr"] = float(a[-1])
    return zona


# ============================================================
# CONSTRUCCIÓN DE LA SEÑAL
# ============================================================

def _redondear(valor: float, digits: int) -> float:
    # float() nativo: los np.float64 de pandas no son serializables a JSON (Supabase)
    return float(round(float(valor), digits))


def _construir_senal(symbol: str, zona: dict) -> Optional[Senal]:
    info = data_engine.info_simbolo(symbol)
    digits = info.digits if info else 5

    colchon = config.ATR_SL_BUFFER_MULT * zona["atr"]
    entrada = zona["entrada"]

    if zona["direccion"] == "BUY":
        sl = zona["anchor"] - colchon
        riesgo = entrada - sl
        tp1 = entrada + config.TP1_RR * riesgo
        tp2 = entrada + config.TP2_RR * riesgo
    else:
        sl = zona["anchor"] + colchon
        riesgo = sl - entrada
        tp1 = entrada - config.TP1_RR * riesgo
        tp2 = entrada - config.TP2_RR * riesgo

    if riesgo <= 0:
        logger.warning("%s: riesgo no positivo (entrada %.5f / SL %.5f) — señal descartada.",
                       symbol, entrada, sl)
        return None

    return Senal(
        symbol=symbol,
        estrategia=ESTRATEGIA,
        direccion=zona["direccion"],
        precio_entrada=_redondear(entrada, digits),
        stop_loss=_redondear(sl, digits),
        take_profit=_redondear(tp1, digits),
        take_profit_2=_redondear(tp2, digits),
        metadata={
            "zona_top": _redondear(zona["top"], digits),
            "zona_bot": _redondear(zona["bot"], digits),
            "ancla": _redondear(zona["anchor"], digits),
            "extremo": _redondear(zona["extremo"], digits),
            "zona_creada_en": zona["creada_en"],
            "tf": config.TF_ESTRUCTURA,
            "rev_mult_atr": config.REV_MULT_ATR,
        },
    )


# ============================================================
# API HACIA bot_engine
# ============================================================

def evaluar_todos_los_simbolos(simbolos: list[str]) -> list[Senal]:
    """
    Recalcula la estructura completa por símbolo sobre las últimas velas
    (resistente a reinicios) y devuelve una señal por cada zona NUEVA.
    Deja el estado de zonas vivas disponible vía zona_viva().
    """
    senales: list[Senal] = []
    for symbol in simbolos:
        df = data_engine.obtener_velas(symbol, config.TF_ESTRUCTURA, config.VELAS_ANALISIS)
        if df.empty or len(df) < config.ATR_PERIOD * 3:
            logger.warning("%s: velas insuficientes para evaluar estructura.", symbol)
            _zonas_vivas[symbol] = None
            continue

        zona = _procesar_simbolo(symbol, df)
        _zonas_vivas[symbol] = zona

        # Latido: deja constancia de cada análisis, haya o no zona.
        if zona is None:
            logger.info("%s: %d velas %s analizadas — sin zona activa (esperando nuevo par HL→HH o LH→LL).",
                        symbol, len(df), config.TF_ESTRUCTURA)
            continue
        logger.info("%s: %d velas %s analizadas — zona %s viva [%.5f - %.5f]%s.",
                    symbol, len(df), config.TF_ESTRUCTURA, zona["direccion"],
                    zona["bot"], zona["top"], " (ya mitigada)" if zona.get("tapped") else "")

        zona_id = f"{symbol}|{zona['direccion']}|{zona['creada_en']}"
        if zona_id in _zonas_emitidas:
            continue

        senal = _construir_senal(symbol, zona)
        if senal is None:
            continue

        _zonas_emitidas.add(zona_id)
        senal.metadata["zona_id"] = zona_id
        logger.info(
            "%s: nueva Golden Zone %s [%.5f - %.5f], entrada límite %.5f, ancla %.5f",
            symbol, zona["direccion"], zona["bot"], zona["top"],
            senal.precio_entrada, zona["anchor"],
        )
        senales.append(senal)

    # higiene: que el set de emitidas no crezca sin límite
    if len(_zonas_emitidas) > 500:
        _zonas_emitidas.clear()

    return senales


def zona_viva(symbol: str) -> Optional[dict]:
    """Zona vigente del símbolo tras la última evaluación (o None)."""
    return _zonas_vivas.get(symbol)
