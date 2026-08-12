import { createClient } from '@supabase/supabase-js'

// Mismo proyecto Supabase que TraderNetAI (kakvbirmgcnojxtqjlwm),
// tablas propias con prefijo idx_ para no chocar con las existentes
// (traders, operaciones, senales, consejos_ai, logros).
const SUPABASE_URL = import.meta.env.VITE_SUPABASE_URL
const SUPABASE_ANON_KEY = import.meta.env.VITE_SUPABASE_ANON_KEY

export const supabase = createClient(SUPABASE_URL, SUPABASE_ANON_KEY, {
  realtime: { params: { eventsPerSecond: 5 } },
})
