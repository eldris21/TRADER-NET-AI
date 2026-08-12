"""
sync_trades_supabase.py — Sincroniza operaciones cerradas en MT5
(filtradas por magic_number) hacia idx_operaciones en Supabase,
marcando estado='CERRADA', resultado, precio_cierre y cerrado_en.

Corre periódicamente (independiente del bot principal) para mantener
el dashboard al día incluso si una posición se cerró manualmente o
por SL/TP directo en el broker.
"""

import logging
import time
from datetime import datetime, timedelta

import MetaTrader5 as mt5
from supabase import create_client

import config
import data_engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("sync_trades")

supabase = create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)


def sincronizar_cierres(dias_atras: int = 2) -> None:
    desde = datetime.now() - timedelta(days=dias_atras)
    deals = mt5.history_deals_get(desde, datetime.now())
    if deals is None:
        logger.warning("Sin deals en el rango consultado.")
        return

    deals_de_este_bot = [d for d in deals if d.magic == config.MAGIC_NUMBER and d.entry == mt5.DEAL_ENTRY_OUT]

    for deal in deals_de_este_bot:
        try:
            resp = (
                supabase.table("idx_operaciones")
                .select("id, estado")
                .eq("ticket", deal.position_id)
                .eq("magic_number", config.MAGIC_NUMBER)
                .execute()
            )
            if not resp.data:
                logger.debug("Operación con ticket %s no encontrada en Supabase (¿se abrió fuera del bot?)", deal.position_id)
                continue

            registro = resp.data[0]
            if registro["estado"] == "CERRADA":
                continue  # ya sincronizada

            supabase.table("idx_operaciones").update({
                "estado": "CERRADA",
                "precio_cierre": deal.price,
                "resultado": deal.profit,
                "cerrado_en": datetime.fromtimestamp(deal.time).isoformat(),
            }).eq("id", registro["id"]).execute()

            logger.info("Sincronizado cierre: ticket %s, resultado %.2f", deal.position_id, deal.profit)

        except Exception:
            logger.exception("Error sincronizando deal %s", deal.ticket)


def main() -> None:
    if not data_engine.conectar():
        logger.error("No se pudo conectar a MT5.")
        return
    logger.info("sync_trades_supabase iniciado.")
    try:
        while True:
            sincronizar_cierres()
            time.sleep(30)
    except KeyboardInterrupt:
        logger.info("Detenido manualmente.")
    finally:
        data_engine.desconectar()


if __name__ == "__main__":
    main()
