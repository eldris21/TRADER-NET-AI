-- ============================================
-- Tablas para TradingPro-Nasdaq (Nasdaq + US30)
-- Proyecto Supabase: kakvbirmgcnojxtqjlwm
-- Prefijo idx_ (indices) — reemplaza el prefijo sp500_ usado
-- antes cuando el plan era operar SP500. Un solo bot maneja
-- ambos símbolos (US100Cash / US30Cash), diferenciados por
-- la columna "symbol" y por magic_number si se desea separar.
-- ============================================

-- Si ya corriste el SQL anterior de sp500_*, estas tablas nuevas
-- no chocan con esas — puedes eliminar las sp500_* manualmente
-- desde el SQL Editor si ya no las vas a usar:
--   DROP TABLE IF EXISTS sp500_senales, sp500_operaciones, sp500_bot_errors;

CREATE TABLE IF NOT EXISTS idx_senales (
    id BIGSERIAL PRIMARY KEY,
    creado_en TIMESTAMPTZ DEFAULT now(),
    symbol TEXT NOT NULL,               -- 'US100Cash' (Nasdaq) o 'US30Cash'
    estrategia TEXT NOT NULL,
    direccion TEXT NOT NULL,            -- BUY / SELL
    precio_entrada NUMERIC NOT NULL,
    stop_loss NUMERIC NOT NULL,
    take_profit NUMERIC NOT NULL,
    estado TEXT DEFAULT 'PENDING',      -- PENDING / EJECUTADA / EXPIRADA / RECHAZADA
    vigente_hasta TIMESTAMPTZ,
    magic_number BIGINT DEFAULT 20260801,
    metadata JSONB
);

CREATE TABLE IF NOT EXISTS idx_operaciones (
    id BIGSERIAL PRIMARY KEY,
    senal_id BIGINT REFERENCES idx_senales(id),
    creado_en TIMESTAMPTZ DEFAULT now(),
    symbol TEXT NOT NULL,
    ticket BIGINT,
    direccion TEXT NOT NULL,
    lote NUMERIC NOT NULL,
    precio_entrada NUMERIC NOT NULL,
    stop_loss NUMERIC,
    take_profit NUMERIC,
    precio_cierre NUMERIC,
    resultado NUMERIC,
    estado TEXT DEFAULT 'ABIERTA',      -- ABIERTA / CERRADA
    magic_number BIGINT DEFAULT 20260801,
    cerrado_en TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS idx_bot_errors (
    id BIGSERIAL PRIMARY KEY,
    creado_en TIMESTAMPTZ DEFAULT now(),
    symbol TEXT,
    retcode INTEGER,
    mensaje TEXT,
    contexto JSONB
);

CREATE INDEX IF NOT EXISTS idx_senales_estado ON idx_senales(estado);
CREATE INDEX IF NOT EXISTS idx_senales_symbol ON idx_senales(symbol);
CREATE INDEX IF NOT EXISTS idx_operaciones_estado ON idx_operaciones(estado);
CREATE INDEX IF NOT EXISTS idx_operaciones_symbol ON idx_operaciones(symbol);

ALTER TABLE idx_senales ENABLE ROW LEVEL SECURITY;
ALTER TABLE idx_operaciones ENABLE ROW LEVEL SECURITY;
ALTER TABLE idx_bot_errors ENABLE ROW LEVEL SECURITY;

-- Lectura pública para el dashboard (solo SELECT); el bot Python usa
-- la service_role key (no la anon key) para poder escribir.
CREATE POLICY "idx_senales_read" ON idx_senales FOR SELECT USING (true);
CREATE POLICY "idx_operaciones_read" ON idx_operaciones FOR SELECT USING (true);
CREATE POLICY "idx_bot_errors_read" ON idx_bot_errors FOR SELECT USING (true);

CREATE POLICY "idx_senales_write" ON idx_senales FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "idx_operaciones_write" ON idx_operaciones FOR ALL USING (true) WITH CHECK (true);
CREATE POLICY "idx_bot_errors_write" ON idx_bot_errors FOR ALL USING (true) WITH CHECK (true);
