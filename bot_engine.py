"""
bot_engine.py — Loop principal del bot.

- Corre la estrategia sobre los 5 símbolos en cada ciclo.
- Respeta el límite de 3 pérdidas TOTALES por día (compartido entre
  los 5 símbolos), consultando idx_operaciones en Supabase.
- Sin restricción de killzone (config.RESTRINGIR_A_KILLZONE = False).
- Al detectar una señal válida: la guarda en idx_senales, ejecuta la
  orden en MT5, guarda el resultado en idx_operaciones, y notifica
  por Telegram. Los errores de ejecución se registran en idx_bot_errors.
"""

import logging
import time
from datetime import datetime, date
from typing import Optional

import MetaTrader5 as mt5
import requests
from supabase import create_client

import config
import data_engine
import signal_engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("bot_engine")

supabase = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)

state = config.RuntimeState()


# ============================================================
# TELEGRAM
# ============================================================

def enviar_telegram(mensaje: str) -> None:
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        logger.warning("Telegram no configurado (falta token o chat_id) — se omite envío.")
        return
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, data={
            "chat_id": config.TELEGRAM_CHAT_ID,
            "text": mensaje,
            "parse_mode": "Markdown",
        }, timeout=10)
    except Exception:
        logger.exception("Error enviando mensaje a Telegram")


# ============================================================
# LÍMITE DE PÉRDIDAS COMPARTIDO (3 por día, entre los 5 símbolos)
# ============================================================

def _resetear_contador_si_cambio_dia() -> None:
    hoy = date.today().isoformat()
    if state.last_reset_date != hoy:
        state.losses_today = 0
        state.last_reset_date = hoy
        state.signals_sent_ids.clear()
        logger.info("Nuevo día (%s) — contador de pérdidas reseteado.", hoy)


def contar_perdidas_hoy() -> int:
    """
    Cuenta operaciones CERRADAS con resultado negativo hoy, para TODOS
    los símbolos, usando magic_number para filtrar solo las de este bot.
    Esto hace el contador resistente a reinicios del bot (no depende
    solo de memoria).
    """
    hoy_inicio = datetime.combine(date.today(), datetime.min.time()).isoformat()
    try:
        resp = (
            supabase.table("idx_operaciones")
            .select("id, resultado")
            .eq("magic_number", config.MAGIC_NUMBER)
            .eq("estado", "CERRADA")
            .gte("cerrado_en", hoy_inicio)
            .lt("resultado", 0)
            .execute()
        )
        return len(resp.data or [])
    except Exception:
        logger.exception("Error consultando pérdidas de hoy en Supabase — se usa contador en memoria como respaldo.")
        return state.losses_today


def limite_de_perdidas_alcanzado() -> bool:
    _resetear_contador_si_cambio_dia()
    perdidas = contar_perdidas_hoy()
    state.losses_today = perdidas
    if perdidas >= config.MAX_LOSSES_PER_DAY_TOTAL:
        logger.warning(
            "Límite de %d pérdidas diarias alcanzado (%d) — no se abren nuevas operaciones hasta mañana.",
            config.MAX_LOSSES_PER_DAY_TOTAL, perdidas,
        )
        return True
    return False


# ============================================================
# SUPABASE — registrar señal / operación / error
# ============================================================

def guardar_senal(senal: signal_engine.Senal) -> Optional[int]:
    try:
        resp = supabase.table("idx_senales").insert({
            "symbol": senal.symbol,
            "estrategia": senal.estrategia,
            "direccion": senal.direccion,
            "precio_entrada": senal.precio_entrada,
            "stop_loss": senal.stop_loss,
            "take_profit": senal.take_profit,
            "estado": "PENDING",
            "magic_number": config.MAGIC_NUMBER,
            "metadata": senal.metadata,
        }).execute()
        return resp.data[0]["id"] if resp.data else None
    except Exception:
        logger.exception("Error guardando señal en Supabase")
        return None


def actualizar_estado_senal(senal_id: int, estado: str) -> None:
    try:
        supabase.table("idx_senales").update({"estado": estado}).eq("id", senal_id).execute()
    except Exception:
        logger.exception("Error actualizando estado de señal %s", senal_id)


def guardar_operacion(senal_id: int, senal: signal_engine.Senal, ticket: int, lote: float) -> None:
    try:
        supabase.table("idx_operaciones").insert({
            "senal_id": senal_id,
            "symbol": senal.symbol,
            "ticket": ticket,
            "direccion": senal.direccion,
            "lote": lote,
            "precio_entrada": senal.precio_entrada,
            "stop_loss": senal.stop_loss,
            "take_profit": senal.take_profit,
            "estado": "ABIERTA",
            "magic_number": config.MAGIC_NUMBER,
        }).execute()
    except Exception:
        logger.exception("Error guardando operación en Supabase")


def guardar_error(symbol: str, retcode: int, mensaje: str, contexto: dict) -> None:
    try:
        supabase.table("idx_bot_errors").insert({
            "symbol": symbol,
            "retcode": retcode,
            "mensaje": mensaje,
            "contexto": contexto,
        }).execute()
    except Exception:
        logger.exception("Error guardando error en Supabase (meta-error)")


# ============================================================
# CÁLCULO DE LOTE (por % de riesgo)
# ============================================================

def calcular_lote(symbol: str, precio_entrada: float, stop_loss: float) -> float:
    info = data_engine.info_simbolo(symbol)
    cuenta = mt5.account_info()
    if info is None or cuenta is None:
        return 0.01  # fallback mínimo de seguridad

    riesgo_dinero = cuenta.balance * (config.RISK_PERCENT_PER_TRADE / 100)
    distancia_precio = abs(precio_entrada - stop_loss)
    if distancia_precio <= 0:
        return 0.01

    valor_tick = info.trade_tick_value
    tick_size = info.trade_tick_size or info.point
    valor_por_punto = valor_tick / tick_size if tick_size else 0

    if valor_por_punto <= 0:
        return 0.01

    lote_calculado = riesgo_dinero / (distancia_precio * valor_por_punto)
    lote_calculado = max(info.volume_min, min(info.volume_max, lote_calculado))
    # redondear al step de volumen del símbolo
    step = info.volume_step or 0.01
    lote_calculado = round(lote_calculado / step) * step
    return round(lote_calculado, 2)


# ============================================================
# EJECUCIÓN DE ÓRDENES
# ============================================================

def ejecutar_orden(senal: signal_engine.Senal, lote: float):
    tipo_orden = mt5.ORDER_TYPE_BUY if senal.direccion == "BUY" else mt5.ORDER_TYPE_SELL
    precio = data_engine.precio_actual(senal.symbol)
    if precio is None:
        return None

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": senal.symbol,
        "volume": lote,
        "type": tipo_orden,
        "price": precio,
        "sl": senal.stop_loss,
        "tp": senal.take_profit,
        "deviation": 20,
        "magic": config.MAGIC_NUMBER,
        "comment": senal.estrategia[:31],  # MT5 limita el comentario
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(request)
    return result


# ============================================================
# LOOP PRINCIPAL
# ============================================================

def ciclo() -> None:
    if limite_de_perdidas_alcanzado():
        return

    simbolos_activos = data_engine.verificar_simbolos()
    if not simbolos_activos:
        logger.error("Ningún símbolo disponible — revisa nombres en config.SYMBOLS vs. tu broker.")
        return

    senales = signal_engine.evaluar_todos_los_simbolos(simbolos_activos)

    for senal in senales:
        senal_id = guardar_senal(senal)

        lote = calcular_lote(senal.symbol, senal.precio_entrada, senal.stop_loss)
        resultado = ejecutar_orden(senal, lote)

        if resultado is None or resultado.retcode != mt5.TRADE_RETCODE_DONE:
            retcode = resultado.retcode if resultado else -1
            mensaje = resultado.comment if resultado else "Sin respuesta de MT5 (precio no disponible)"
            logger.error("Fallo al ejecutar %s %s: [%s] %s", senal.symbol, senal.direccion, retcode, mensaje)
            guardar_error(senal.symbol, retcode, mensaje, {"senal_id": senal_id, "lote": lote})
            if senal_id:
                actualizar_estado_senal(senal_id, "RECHAZADA")
            enviar_telegram(
                f"⚠️ *Error ejecutando señal*\n{senal.symbol} {senal.direccion}\n"
                f"Retcode {retcode}: {mensaje}"
            )
            continue

        if senal_id:
            actualizar_estado_senal(senal_id, "EJECUTADA")
        guardar_operacion(senal_id, senal, resultado.order, lote)

        enviar_telegram(
            f"✅ *Nueva operación*\n"
            f"*{senal.symbol}* — {senal.direccion}\n"
            f"Entrada: {senal.precio_entrada}\n"
            f"SL: {senal.stop_loss}\n"
            f"TP1: {senal.take_profit} | TP2: {senal.take_profit_2}\n"
            f"Lote: {lote}\n"
            f"Estrategia: {senal.estrategia}"
        )


def main() -> None:
    if not data_engine.conectar():
        logger.error("No se pudo conectar a MT5. Verifica que el terminal esté abierto y logueado.")
        return

    logger.info("Bot SMC 5-activos iniciado. Símbolos: %s", config.SYMBOLS)
    logger.info("Límite de pérdidas diarias (compartido): %d", config.MAX_LOSSES_PER_DAY_TOTAL)

    try:
        while True:
            ciclo()
            time.sleep(60)  # corre cada minuto (timeframe base de confirmación es M1)
    except KeyboardInterrupt:
        logger.info("Detenido manualmente.")
    finally:
        data_engine.desconectar()


if __name__ == "__main__":
    main()
