import { useEffect, useState } from 'react'
import { supabase } from './lib/supabase.js'
import StatCard from './components/StatCard.jsx'
import SignalsTable from './components/SignalsTable.jsx'
import PositionsPanel from './components/PositionsPanel.jsx'

export default function App() {
  const [signals, setSignals] = useState([])
  const [operaciones, setOperaciones] = useState([])
  const [loading, setLoading] = useState(true)
  const [now, setNow] = useState(new Date())

  useEffect(() => {
    const clock = setInterval(() => setNow(new Date()), 1000)
    return () => clearInterval(clock)
  }, [])

  useEffect(() => {
    let mounted = true

    async function load() {
      setLoading(true)
      const [{ data: sigData }, { data: opData }] = await Promise.all([
        supabase
          .from('idx_senales')
          .select('*')
          .order('creado_en', { ascending: false })
          .limit(30),
        supabase
          .from('idx_operaciones')
          .select('*')
          .order('creado_en', { ascending: false })
          .limit(30),
      ])
      if (!mounted) return
      setSignals(sigData || [])
      setOperaciones(opData || [])
      setLoading(false)
    }

    load()

    const channel = supabase
      .channel('idx-live')
      .on('postgres_changes', { event: '*', schema: 'public', table: 'idx_senales' }, load)
      .on('postgres_changes', { event: '*', schema: 'public', table: 'idx_operaciones' }, load)
      .subscribe()

    return () => {
      mounted = false
      supabase.removeChannel(channel)
    }
  }, [])

  const abiertas = operaciones.filter((o) => o.estado === 'ABIERTA').length
  const cerradasHoy = operaciones.filter(
    (o) =>
      o.estado === 'CERRADA' &&
      new Date(o.cerrado_en).toDateString() === new Date().toDateString()
  )
  const pnlHoy = cerradasHoy.reduce((acc, o) => acc + (o.resultado || 0), 0)
  const pendientes = signals.filter((s) => s.estado === 'PENDING').length

  return (
    <div className="min-h-screen bg-grid-fade">
      <header className="border-b border-ink-700/80 bg-ink-950/80 backdrop-blur">
        <div className="max-w-6xl mx-auto px-5 py-4 flex items-center justify-between">
          <div>
            <div className="flex items-baseline gap-2">
              <h1 className="font-display text-lg font-bold tracking-tight text-slate-50">
                TradingPro
              </h1>
              <span className="font-mono text-[11px] text-signal-violet tracking-widest uppercase">
                Nasdaq · US30
              </span>
            </div>
            <p className="text-xs text-slate-500 font-mono mt-0.5">
              Panel de señales en vivo · magic 20260801
            </p>
          </div>
          <div className="text-right">
            <div className="font-mono text-sm tabular text-slate-300">
              {now.toLocaleTimeString('es-DO', { hour12: false })}
            </div>
            <div className="text-[11px] text-slate-500 font-mono">Hora RD</div>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-5 py-6 space-y-6">
        <section className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <StatCard label="Posiciones abiertas" value={abiertas} />
          <StatCard label="Señales pendientes" value={pendientes} />
          <StatCard
            label="P&L hoy"
            value={`${pnlHoy >= 0 ? '+' : ''}$${pnlHoy.toFixed(2)}`}
            sub={`${cerradasHoy.length} cerradas`}
            tone={pnlHoy > 0 ? 'up' : pnlHoy < 0 ? 'down' : 'default'}
          />
          <StatCard label="Símbolos activos" value="2" sub="US100Cash · US30Cash" />
        </section>

        <section className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2">
            <SignalsTable signals={signals} loading={loading} />
          </div>
          <div>
            <PositionsPanel operaciones={operaciones} loading={loading} />
          </div>
        </section>
      </main>

      <footer className="max-w-6xl mx-auto px-5 py-8 text-center">
        <p className="text-[11px] font-mono text-slate-600">
          TradingPro-Nasdaq · Supabase kakvbirmgcnojxtqjlwm · datos en vivo
        </p>
      </footer>
    </div>
  )
}
