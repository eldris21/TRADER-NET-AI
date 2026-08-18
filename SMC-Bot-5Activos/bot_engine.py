"""
bot_engine.py — Loop principal del bot.

- Corre la estrategia GOLDEN ZONE (IGZ) en cada TF de TFS_ESTRUCTURA
  (M1 y M5, de forma independiente) sobre los símbolos ACTIVOS
  en config.SYMBOLS (actualmente solo GOLD; el resto pausado).
- Entrada por ORDEN LÍMITE en el 50% del fibo de la zona. Si al momento
  de colocarla el precio ya alcanzó ese nivel, entra a mercado.
- Cancela automáticamente las órdenes límite cuya zona fue invalidada
  o reemplazada, y las de símbolos pausados.
- SINCRONIZACIÓN: detecta órdenes límite ejecutadas (PENDIENTE->ABIERTA)
  y posiciones cerradas (->CERRADA con resultado) en Supabase. De esto
  depende el límite de pérdidas.
- BREAKEVEN: mueve el SL al precio de entrada cuando la ganancia
  alcanza BREAKEVEN_AT_R veces el riesgo (1.0 = al llegar a 1:1).
- LÍMITES DIARIOS: 3 pérdidas O 6 señales ejecutadas — al llegar a
  cualquiera, el bot cancela sus pendientes y deja de operar hasta mañana.
"""

import logging
import time
from datetime import datetime, date, timedelta
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

# Memoria de sincronización (evita repetir updates/avisos ya hechos)
_tickets_marcados_abiertos: set[int] = set()
_posiciones_cerradas_procesadas: set[int] = set()


# ============================================================
# TELEGRAM
# ============================================================

def enviar_telegram(mensaje: str) -> None:
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        logger.warning("Telegram no configurado (falta token o chat_id) — se omite envío.")
        return
    url = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        resp = requests.post(url, data={
            "chat_id": config.TELEGRAM_CHAT_ID,
            "text": mensaje,
            "parse_mode": "Markdown",
        }, timeout=10)
        if resp.status_code != 200:
            logger.error("Telegram respondió %s: %s", resp.status_code, resp.text)
    except Exception:
        logger.exception("Error enviando mensaje a Telegram")


# ============================================================
# LÍMITES DIARIOS (pérdidas y señales) — compartidos entre símbolos
# ============================================================

def _resetear_contador_si_cambio_dia() -> None:
    hoy = date.today().isoformat()
    if state.last_reset_date != hoy:
        state.losses_today = 0
        state.signals_today = 0
        state.last_reset_date = hoy
        state.signals_sent_ids.clear()
        logger.info("Nuevo día (%s) — contadores de pérdidas y señales reseteados.", hoy)


def contar_perdidas_hoy() -> int:
    """Operaciones CERRADAS con resultado negativo hoy (todas las del bot,
    por magic_number). Resistente a reinicios: la fuente es Supabase."""
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


def contar_senales_hoy() -> int:
    """Señales EJECUTADAS hoy según Supabase; si la consulta falla
    (p.ej. la tabla no tiene created_at), usa el contador en memoria."""
    hoy_inicio = datetime.combine(date.today(), datetime.min.time()).isoformat()
    try:
        resp = (
            supabase.table("idx_senales")
            .select("id")
            .eq("magic_number", config.MAGIC_NUMBER)
            .eq("estado", "EJECUTADA")
            .gte("created_at", hoy_inicio)
            .execute()
        )
        return len(resp.data or [])
    except Exception:
        logger.warning("No se pudo contar señales en Supabase — usando contador en memoria (%d).",
                       state.signals_today)
        return state.signals_today


def limites_diarios_alcanzados() -> Optional[str]:
    """Devuelve el motivo si algún límite diario está alcanzado, o None."""
    _resetear_contador_si_cambio_dia()

    perdidas = contar_perdidas_hoy()
    state.losses_today = perdidas
    if perdidas >= config.MAX_LOSSES_PER_DAY_TOTAL:
        return f"{perdidas} pérdidas hoy (límite: {config.MAX_LOSSES_PER_DAY_TOTAL})"

    senales_hoy = max(contar_senales_hoy(), state.signals_today)
    state.signals_today = senales_hoy
    if senales_hoy >= config.MAX_SIGNALS_PER_DAY_TOTAL:
        return f"{senales_hoy} señales ejecutadas hoy (límite: {config.MAX_SIGNALS_PER_DAY_TOTAL})"

    return None


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


def guardar_operacion(senal_id: Optional[int], senal: signal_engine.Senal,
                      ticket: int, lote: float, estado: str) -> None:
    """estado: 'PENDIENTE' (orden límite colocada) o 'ABIERTA' (ejecutada a mercado)."""
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
            "estado": estado,
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
# SINCRONIZACIÓN MT5 -> SUPABASE (llenados y cierres)
# ============================================================

def sincronizar_operaciones() -> None:
    """
    1) Órdenes límite que se ejecutaron: la posición aparece en MT5 con
       nuestro magic -> marca la fila PENDIENTE como ABIERTA.
    2) Posiciones cerradas (SL/TP/manual): aparecen como deals de salida
       en el historial -> marca la fila como CERRADA con su resultado
       (profit + comisión + swap). De aquí se alimenta el límite de pérdidas.
    """
    # --- 1) pendientes que se llenaron ---
    for pos in (mt5.positions_get() or []):
        if pos.magic != config.MAGIC_NUMBER or pos.ticket in _tickets_marcados_abiertos:
            continue
        try:
            resp = (
                supabase.table("idx_operaciones")
                .update({"estado": "ABIERTA", "precio_entrada": float(pos.price_open)})
                .eq("ticket", pos.ticket)
                .eq("estado", "PENDIENTE")
                .execute()
            )
            _tickets_marcados_abiertos.add(pos.ticket)
            if resp.data:  # solo si realmente era una límite pendiente
                direccion = "BUY" if pos.type == mt5.POSITION_TYPE_BUY else "SELL"
                logger.info("Orden límite ejecutada: %s %s ticket %s @ %.5f",
                            pos.symbol, direccion, pos.ticket, pos.price_open)
                enviar_telegram(
                    f"▶️ *Orden límite ejecutada*\n"
                    f"*{pos.symbol}* — {direccion}\n"
                    f"Precio real: {pos.price_open}\n"
                    f"SL: {pos.sl} | TP: {pos.tp}\n"
                    f"Lote: {pos.volume}"
                )
        except Exception:
            logger.exception("Error marcando operación %s como ABIERTA", pos.ticket)
            _tickets_marcados_abiertos.discard(pos.ticket)  # reintentar el próximo ciclo

    # --- 2) posiciones cerradas ---
    ahora = datetime.now()
    desde = ahora - timedelta(days=3)          # ventana amplia (cubre desfase horario del broker)
    hasta = ahora + timedelta(days=1)
    for deal in (mt5.history_deals_get(desde, hasta) or []):
        if deal.magic != config.MAGIC_NUMBER:
            continue
        if deal.entry != mt5.DEAL_ENTRY_OUT:   # solo deals de salida (cierre)
            continue
        pid = deal.position_id
        if pid in _posiciones_cerradas_procesadas:
            continue
        resultado = float(deal.profit + deal.commission + deal.swap)
        try:
            resp = (
                supabase.table("idx_operaciones")
                .update({
                    "estado": "CERRADA",
                    "resultado": resultado,
                    "cerrado_en": datetime.now().isoformat(),
                })
                .eq("ticket", pid)
                .neq("estado", "CERRADA")
                .execute()
            )
            _posiciones_cerradas_procesadas.add(pid)
            if resp.data:
                if resultado < 0:
                    state.losses_today += 1
                emoji = "🔴" if resultado < 0 else "🟢"
                logger.info("Posición %s cerrada — resultado %.2f", pid, resultado)
                enviar_telegram(
                    f"{emoji} *Operación cerrada*\n"
                    f"*{deal.symbol}*\n"
                    f"Resultado: {resultado:+.2f} USD\n"
                    f"Pérdidas hoy: {state.losses_today}/{config.MAX_LOSSES_PER_DAY_TOTAL}"
                )
        except Exception:
            logger.exception("Error marcando posición %s como CERRADA", pid)
            _posiciones_cerradas_procesadas.discard(pid)


# ============================================================
# BREAKEVEN — SL a la entrada cuando la ganancia alcanza 1R
# (R = distancia entrada -> SL original). Con BREAKEVEN_AT_R = 1.0
# la protección entra exactamente al llegar a un 1:1.
# ============================================================

def aplicar_breakeven() -> None:
    for pos in (mt5.positions_get() or []):
        if pos.magic != config.MAGIC_NUMBER:
            continue
        if not pos.sl:
            continue  # sin SL no hay R medible (nuestras órdenes siempre llevan SL)
        info = data_engine.info_simbolo(pos.symbol)
        digits = info.digits if info else 5
        point = info.point if info else 0.0001
        tick = mt5.symbol_info_tick(pos.symbol)
        if tick is None:
            continue

        if pos.type == mt5.POSITION_TYPE_BUY:
            if pos.sl >= pos.price_open - point:
                continue  # ya está en breakeven (o mejor)
            riesgo = pos.price_open - pos.sl        # R original (el SL aún no se ha movido)
            ganancia = tick.bid - pos.price_open
        else:
            if pos.sl <= pos.price_open + point:
                continue
            riesgo = pos.sl - pos.price_open
            ganancia = pos.price_open - tick.ask

        if riesgo <= 0 or ganancia < config.BREAKEVEN_AT_R * riesgo:
            continue

        nuevo_sl = round(float(pos.price_open), digits)
        res = mt5.order_send({
            "action": mt5.TRADE_ACTION_SLTP,
            "position": pos.ticket,
            "symbol": pos.symbol,
            "sl": nuevo_sl,
            "tp": pos.tp,
        })
        if res is not None and res.retcode == mt5.TRADE_RETCODE_DONE:
            logger.info("%s ticket %s: SL movido a breakeven (%.5f) — ganancia alcanzó %.1fR.",
                        pos.symbol, pos.ticket, nuevo_sl, ganancia / riesgo)
            enviar_telegram(
                f"🛡 *SL a breakeven*\n"
                f"*{pos.symbol}* — la operación alcanzó "
                f"{config.BREAKEVEN_AT_R:g}:1 (ganancia = riesgo).\n"
                f"Nuevo SL: {nuevo_sl} (precio de entrada)"
            )
        else:
            retcode = res.retcode if res else -1
            logger.error("Fallo moviendo SL a BE en ticket %s: retcode %s", pos.ticket, retcode)
            guardar_error(pos.symbol, retcode, "Fallo aplicando breakeven", {"ticket": pos.ticket})


# ============================================================
# CÁLCULO DE LOTE
# ============================================================

def calcular_lote(symbol: str, precio_entrada: float, stop_loss: float) -> float:
    """Lote fijo por símbolo (config.FIXED_LOTS); 0.01 de seguridad si falta."""
    info = data_engine.info_simbolo(symbol)

    if symbol in config.FIXED_LOTS:
        lote = config.FIXED_LOTS[symbol]
    else:
        lote = config.LOTE_DEFAULT_SEGURO
        logger.warning(
            "%s no tiene lote fijo definido en FIXED_LOTS — usando %.2f por seguridad. "
            "Agrégalo a config.py cuando definas el tamaño real.",
            symbol, lote,
        )

    if info is None:
        return lote

    lote = max(info.volume_min, min(info.volume_max, lote))
    step = info.volume_step or 0.01
    lote = round(lote / step) * step
    return round(lote, 2)


# ============================================================
# ÓRDENES — límite en la zona, mercado si el precio ya llegó
# ============================================================

def _pendiente_existente(senal: signal_engine.Senal, lote: float) -> bool:
    """True si ya hay una orden límite nuestra equivalente (mismo símbolo,
    dirección, precio y lote). Si el precio coincide pero el LOTE cambió
    en config, cancela la vieja y devuelve False para recolocarla."""
    info = data_engine.info_simbolo(senal.symbol)
    point = info.point if info else 0.0001
    tipo_buscado = mt5.ORDER_TYPE_BUY_LIMIT if senal.direccion == "BUY" else mt5.ORDER_TYPE_SELL_LIMIT
    for o in (mt5.orders_get(symbol=senal.symbol) or []):
        if o.magic == config.MAGIC_NUMBER and o.type == tipo_buscado \
                and abs(o.price_open - senal.precio_entrada) <= 10 * point:
            if abs(o.volume_current - lote) > 0.001:
                mt5.order_send({"action": mt5.TRADE_ACTION_REMOVE, "order": o.ticket})
                logger.info("%s: orden límite %s cancelada para recolocarla con el lote nuevo (%.2f -> %.2f).",
                            senal.symbol, o.ticket, o.volume_current, lote)
                return False
            return True
    return False


def ejecutar_orden(senal: signal_engine.Senal, lote: float):
    """Orden límite en el 50% de la zona; a mercado si el precio ya llegó.
    Devuelve (result, fue_pendiente)."""
    tick = mt5.symbol_info_tick(senal.symbol)
    if tick is None:
        return None, False

    if senal.direccion == "BUY":
        precio_mercado = tick.ask
        ya_llego = precio_mercado <= senal.precio_entrada
        tipo = mt5.ORDER_TYPE_BUY if ya_llego else mt5.ORDER_TYPE_BUY_LIMIT
    else:
        precio_mercado = tick.bid
        ya_llego = precio_mercado >= senal.precio_entrada
        tipo = mt5.ORDER_TYPE_SELL if ya_llego else mt5.ORDER_TYPE_SELL_LIMIT

    request = {
        "action": mt5.TRADE_ACTION_DEAL if ya_llego else mt5.TRADE_ACTION_PENDING,
        "symbol": senal.symbol,
        "volume": lote,
        "type": tipo,
        "price": precio_mercado if ya_llego else senal.precio_entrada,
        "sl": senal.stop_loss,
        "tp": senal.take_profit,
        "deviation": 20,
        "magic": config.MAGIC_NUMBER,
        "comment": senal.estrategia[:31],
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    result = mt5.order_send(request)
    return result, (not ya_llego)


def cancelar_pendientes_invalidadas() -> None:
    """Elimina órdenes límite cuya zona fue invalidada/reemplazada, y las
    de símbolos pausados (que ya no se evalúan)."""
    for o in (mt5.orders_get() or []):
        if o.magic != config.MAGIC_NUMBER:
            continue
        if o.type == mt5.ORDER_TYPE_BUY_LIMIT:
            dir_orden = "BUY"
        elif o.type == mt5.ORDER_TYPE_SELL_LIMIT:
            dir_orden = "SELL"
        else:
            continue

        zonas = signal_engine.zonas_vivas(o.symbol)
        info = data_engine.info_simbolo(o.symbol)
        point = info.point if info else 0.0001
        vigente = any(
            z["direccion"] == dir_orden and abs(z["entrada"] - o.price_open) <= 10 * point
            for z in zonas
        )
        if vigente:
            continue

        res = mt5.order_send({"action": mt5.TRADE_ACTION_REMOVE, "order": o.ticket})
        if res is not None and res.retcode == mt5.TRADE_RETCODE_DONE:
            logger.info("Orden límite %s %s (ticket %s) cancelada — zona invalidada, reemplazada o símbolo pausado.",
                        o.symbol, dir_orden, o.ticket)
            enviar_telegram(
                f"🗑 *Orden límite cancelada*\n{o.symbol} {dir_orden} @ {o.price_open}\n"
                f"Motivo: zona invalidada/reemplazada o símbolo pausado."
            )
        else:
            retcode = res.retcode if res else -1
            logger.error("No se pudo cancelar la orden %s (%s): retcode %s", o.ticket, o.symbol, retcode)
            guardar_error(o.symbol, retcode, "Fallo cancelando orden límite huérfana", {"ticket": o.ticket})


def cancelar_todas_las_pendientes(motivo: str) -> None:
    """Al alcanzar un límite diario, retira TODAS nuestras órdenes límite:
    'dejar de operar' incluye no permitir que una pendiente se llene después."""
    canceladas = []
    for o in (mt5.orders_get() or []):
        if o.magic != config.MAGIC_NUMBER:
            continue
        if o.type not in (mt5.ORDER_TYPE_BUY_LIMIT, mt5.ORDER_TYPE_SELL_LIMIT):
            continue
        res = mt5.order_send({"action": mt5.TRADE_ACTION_REMOVE, "order": o.ticket})
        if res is not None and res.retcode == mt5.TRADE_RETCODE_DONE:
            canceladas.append(f"{o.symbol} @ {o.price_open}")
        else:
            logger.error("No se pudo cancelar la orden %s al aplicar límite diario.", o.ticket)
    if canceladas:
        enviar_telegram(
            "⛔ *Límite diario alcanzado* — órdenes pendientes retiradas:\n"
            + "\n".join(f"• {c}" for c in canceladas)
            + f"\nMotivo: {motivo}"
        )


# ============================================================
# LOOP PRINCIPAL
# ============================================================

def ciclo() -> None:
    # 1) Sincroniza con MT5 (llenados y cierres) y aplica breakeven.
    sincronizar_operaciones()
    aplicar_breakeven()

    # 2) Evalúa estructura de los símbolos ACTIVOS (necesario también para
    #    cancelar límites huérfanas, aunque los límites diarios apliquen).
    simbolos_activos = data_engine.verificar_simbolos()
    if not simbolos_activos:
        logger.error("Ningún símbolo disponible — revisa nombres en config.SYMBOLS vs. tu broker.")
        return

    senales = signal_engine.evaluar_todos_los_simbolos(simbolos_activos)
    cancelar_pendientes_invalidadas()

    # 3) Límites diarios: al alcanzarlos, retira pendientes y no opera más hoy.
    motivo = limites_diarios_alcanzados()
    if motivo:
        cancelar_todas_las_pendientes(motivo)
        hoy = date.today().isoformat()
        if state.limite_avisado != hoy:
            state.limite_avisado = hoy
            logger.warning("Límite diario alcanzado (%s) — el bot deja de operar hasta mañana.", motivo)
            enviar_telegram(f"⛔ *El bot deja de operar por hoy*\n{motivo}\nSe reanuda mañana automáticamente.")
        return

    # 4) Coloca las señales nuevas.
    for senal in senales:
        if state.signals_today >= config.MAX_SIGNALS_PER_DAY_TOTAL:
            logger.warning("Límite de señales del día alcanzado en pleno ciclo — no se colocan más.")
            break

        lote = calcular_lote(senal.symbol, senal.precio_entrada, senal.stop_loss)
        if _pendiente_existente(senal, lote):
            logger.info("%s %s: ya existe una orden límite en %.5f — se omite duplicado.",
                        senal.symbol, senal.direccion, senal.precio_entrada)
            continue

        senal_id = guardar_senal(senal)
        resultado, fue_pendiente = ejecutar_orden(senal, lote)

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

        state.signals_today += 1
        estado_op = "PENDIENTE" if fue_pendiente else "ABIERTA"
        if senal_id:
            actualizar_estado_senal(senal_id, "EJECUTADA")
        guardar_operacion(senal_id, senal, resultado.order, lote, estado_op)

        titulo = "🕐 *Orden límite colocada*" if fue_pendiente else "✅ *Entrada a mercado*"
        enviar_telegram(
            f"{titulo}\n"
            f"*{senal.symbol}* — {senal.direccion}\n"
            f"Entrada (50% zona): {senal.precio_entrada}\n"
            f"SL: {senal.stop_loss} (ancla {senal.metadata.get('ancla')})\n"
            f"TP1: {senal.take_profit} | TP2: {senal.take_profit_2}\n"
            f"Lote: {lote}\n"
            f"Señales hoy: {state.signals_today}/{config.MAX_SIGNALS_PER_DAY_TOTAL}\n"
            f"Estrategia: {senal.estrategia}"
        )


def main() -> None:
    if not data_engine.conectar():
        logger.error("No se pudo conectar a MT5. Verifica que el terminal esté abierto y logueado.")
        return

    logger.info("Bot Golden Zone (IGZ) iniciado. Símbolos activos: %s", config.SYMBOLS)
    logger.info("Límites diarios: %d pérdidas / %d señales (compartidos).",
                config.MAX_LOSSES_PER_DAY_TOTAL, config.MAX_SIGNALS_PER_DAY_TOTAL)

    cuenta = mt5.account_info()
    balance_txt = f"${cuenta.balance:.2f}" if cuenta else "N/D"
    enviar_telegram(
        f"🟢 *Bot iniciado*\n"
        f"Cuenta: {cuenta.login if cuenta else 'N/D'} — Balance: {balance_txt}\n"
        f"Símbolos activos: {', '.join(config.SYMBOLS)} (resto pausado)\n"
        f"Lote GOLD: {config.FIXED_LOTS.get('GOLD')}\n"
        f"Límites/día: {config.MAX_LOSSES_PER_DAY_TOTAL} pérdidas | {config.MAX_SIGNALS_PER_DAY_TOTAL} señales\n"
        f"Breakeven: al alcanzar {config.BREAKEVEN_AT_R:g}R (1:1)\n"
        f"Estrategia: Golden Zone IGZ ({'+'.join(config.TFS_ESTRUCTURA)}) — entrada límite 50%"
    )

    try:
        while True:
            ciclo()
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info("Detenido manualmente.")
    finally:
        data_engine.desconectar()


if __name__ == "__main__":
    main()
