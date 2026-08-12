# TradingPro-Nasdaq

Panel de señales en vivo para el bot de Nasdaq/US30 (React + Vite + Supabase).
Independiente del sistema de gold (TradingProEA-main) — no comparte carpeta,
credenciales de MT5, ni magic number con ese proyecto.

- **Supabase**: `kakvbirmgcnojxtqjlwm` (mismo proyecto de TraderNetAI, tablas `idx_*` propias)
- **Símbolos**: `US100Cash` (Nasdaq) y `US30Cash`, diferenciados por columna `symbol`
- **Magic number**: `20260801`
- **Telegram**: `@ea500drbot`, canal "Nasdaq & US30 Signals"

## 1. Crear las tablas en Supabase

Antes de desplegar, corre `sql/idx_tablas.sql` en el SQL Editor de tu proyecto Supabase
(`kakvbirmgcnojxtqjlwm`). Crea las tablas `idx_senales`, `idx_operaciones`, `idx_bot_errors`.

## 2. Subir a GitHub (vía editor web, como ya haces)

1. Ve a [github.com/new](https://github.com/new)
2. Nombre del repo: `TradingPro-Nasdaq`
3. Público o privado, como prefieras → **Create repository**
4. En el repo vacío, usa **"uploading an existing file"** (o el editor web) y sube
   todo el contenido de esta carpeta manteniendo la estructura (`src/`, `sql/`, etc.)
5. **IMPORTANTE**: no subas ningún archivo `.env` real (solo `.env.example`), el
   `.gitignore` ya lo excluye si usas `git` normal — si subes por el editor web,
   simplemente no arrastres el `.env`.

## 3. Desplegar en Vercel

1. Ve a [vercel.com/new](https://vercel.com/new)
2. Importa el repo `TradingPro-Nasdaq` desde GitHub
3. Framework preset: **Vite** (Vercel lo detecta solo)
4. En **Environment Variables**, agrega:
   - `VITE_SUPABASE_URL` = `https://kakvbirmgcnojxtqjlwm.supabase.co`
   - `VITE_SUPABASE_ANON_KEY` = `sb_publishable_jB8a4JektgnkWvAv6ljVbg_bmt7BHlr`
5. **Deploy**

Cada vez que subas cambios al repo vía el editor web de GitHub, Vercel
redespliega automáticamente — mismo flujo que usas en AGV-SISTEMA.

## 4. Desarrollo local (opcional)

```bash
npm install
cp .env.example .env   # y confirma los valores
npm run dev
```

## Notas

- El dashboard es **solo lectura visual** de lo que el bot Python (aún por
  construir) escribe en Supabase — no ejecuta órdenes ni se conecta a MT5.
- Usa Supabase Realtime, así que las señales/operaciones nuevas aparecen
  solas sin recargar la página.
- Si en algún momento ya no usas las tablas `sp500_*` que se crearon en un
  borrador anterior (cuando el plan era operar SP500 en vez de Nasdaq/US30),
  puedes borrarlas desde el SQL Editor — el comentario en `sql/idx_tablas.sql`
  trae el comando exacto.
