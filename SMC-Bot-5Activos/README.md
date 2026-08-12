# SMC-Bot-5Activos

Bot de trading algorítmico para **Nasdaq (US100Cash), US30 (US30Cash), Oro
(XAUUSD), EURUSD y Plata (XAGUSD)**, con una sola estrategia aplicada a los 5:

**Impulso (M5) + retroceso válido ≥50% Fibonacci + CHoCH → BOS en M1 +
entrada al 50% de la pierna del BOS.**

Sin restricción de killzone (opera 24/5 según horario de cada símbolo).
Límite de **3 pérdidas totales por día**, compartido entre los 5 activos.

Corre 100% local (necesita el terminal MT5 abierto y logueado) — no se
despliega en la nube, a diferencia del dashboard `TradingPro-Nasdaq`.

## 1. Instalación

```bash
pip install -r requirements.txt
cp .env.example .env
```

Edita `.env` y agrega:
- `SUPABASE_SERVICE_KEY`: la **service_role key** de tu proyecto Supabase
  (`cgvidgcgtuzgcuaszqsg`) — Project Settings → API → service_role.
  **Nunca la anon key del dashboard** (esa es solo lectura).
- `TELEGRAM_BOT_TOKEN` y `TELEGRAM_CHAT_ID` del bot `@ea500drbot`.

## 2. Antes de correr en real: verifica los símbolos

Abre MT5 → Market Watch y confirma el nombre EXACTO que tu broker (XMGlobal)
usa para cada instrumento. Ajusta `config.py` → `SYMBOLS` si difiere:

```python
SYMBOLS = [
    "US100Cash",
    "US30Cash",
    "XAUUSD",   # revisa si tu broker usa "GOLD"
    "EURUSD",
    "XAGUSD",   # revisa si tu broker usa "SILVER"
]
```

## 3. Arrancar

```bash
START_ALL.bat
```

Esto abre 3 ventanas independientes:
- `bot_engine.py` — genera señales y ejecuta órdenes
- `result_tracker.py` — breakeven al 70% hacia TP1 + trailing ATR x1.2
- `sync_trades_supabase.py` — sincroniza cierres hacia el dashboard

## 4. Pendientes / riesgos conocidos

- **Sin filtro de noticias.** `config.NEWS_FILTER_ENABLED = False`. Oro,
  plata y EURUSD son muy sensibles a NFP/CPI/FOMC — considera portar
  `news_engine.py` del bot de oro antes de dejarlo corriendo desatendido
  cerca de estos eventos.
- **Correlación entre activos.** Oro/Plata y a veces EURUSD se mueven
  correlacionados. Un solo evento macro puede disparar señales en varios
  símbolos a la vez en la misma dirección, consumiendo el límite diario
  de 3 pérdidas de un solo golpe si el mercado revierte.
- **Sin backtesting todavía.** Esta lógica no tiene muestra histórica real
  ni backtested — no hay evidencia de win rate. Recomendado: correr en
  cuenta demo un tiempo antes de fondos reales, y acumular ≥10-15 trades
  por símbolo antes de sacar conclusiones (mismo criterio que se usa con
  EMA Pullback M5 en el bot de oro).
- **Cálculo de lote por % de riesgo** (`RISK_PERCENT_PER_TRADE` en
  `config.py`, default 0.5%) — ajusta según tu apetito de riesgo real
  antes de ir en vivo.

## 5. Estructura del proyecto

```
config.py                  Parámetros centrales (símbolos, riesgo, fibo)
structure.py                Pivotes, impulso, fibonacci, CHoCH/BOS
data_engine.py               Conexión MT5 y obtención de velas
signal_engine.py             Orquesta la estrategia por símbolo
bot_engine.py                 Loop principal, ejecución de órdenes
result_tracker.py            Breakeven + trailing de posiciones abiertas
sync_trades_supabase.py       Sincroniza cierres hacia Supabase/dashboard
```

## 6. Base de datos

Reutiliza las tablas ya creadas en Supabase (`idx_senales`,
`idx_operaciones`, `idx_bot_errors`) del proyecto `cgvidgcgtuzgcuaszqsg` —
mismo esquema que usa el dashboard `TradingPro-Nasdaq`, ya que la columna
`symbol` acepta cualquier texto y no está limitada a 2 símbolos.
