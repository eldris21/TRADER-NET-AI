import { useEffect, useState } from 'react'
import { supabase } from './lib/supabase.js'
import StatCard from './components/StatCard.jsx'
import SignalsTable from './components/SignalsTable.jsx'
import PositionsPanel from './components/PositionsPanel.jsx'
import PerformanceStrip from './components/PerformanceStrip.jsx'

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
    <div className="min-h-screen bg-paper">
      <header className="border-b border-hairline bg-panel">
        <div className="max-w-6xl mx-auto px-5 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div>
              <div className="flex items-baseline gap-2">
                <h1 className="font-display text-lg font-semibold tracking-tight text-ink-900">
                  TradingPro
                </h1>
                <span className="font-mono text-[11px] text-brand tracking-widest uppercase">
                  Nasdaq · US30
                </span>
              </div>
              <p className="text-xs text-ink-500 font-mono mt-0.5">
                Panel de señales en vivo · magic 20260801
              </p>
            </div>
            <span className="inline-flex items-center gap-1.5 rounded-sm border border-up/30 bg-up-soft px-2 py-1 text-[10px] font-mono font-medium text-up uppercase tracking-widest">
              <span className="h-1.5 w-1.5 rounded-full bg-up" />
              En vivo
            </span>
          </div>
          <div className="text-right">
            <div className="font-mono text-sm tabular text-ink-700">
              {now.toLocaleTimeString('es-DO', { hour12: false })}
            </div>
            <div className="text-[11px] text-ink-500 font-mono">Hora RD</div>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-5 py-6 space-y-5">
        <section className="border border-hairline bg-panel rounded-md px-2 py-2 grid grid-cols-2 md:grid-cols-4 divide-x divide-hairline">
          <StatCard label="Posiciones abiertas" value={abiertas} />
          <StatCard label="Señales pendientes" value={pendientes} />
          <StatCard
            label="P&L hoy"
            value={`${pnlHoy >= 0 ? '+' : ''}$${pnlHoy.toFixed(2)}`}
            sub={`${cerradasHoy.length} cerradas`}
            tone={pnlHoy > 0 ? 'up' : pnlHoy < 0 ? 'down' : 'default'}
          />
          <StatCard label="Símbolos activos" value="5" sub="Gold · Silver · US100 · US30 · EURUSD" />
        </section>

        <section className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2">
            <SignalsTable signals={signals} loading={loading} />
          </div>
          <div>
            <PositionsPanel operaciones={operaciones} loading={loading} />
          </div>
        </section>

        <section>
          <PerformanceStrip operaciones={operaciones} loading={loading} />
        </section>
      </main>

      <footer className="max-w-6xl mx-auto px-5 py-8 text-center">
        <p className="text-[11px] font-mono text-ink-400">
          TradingPro-Nasdaq · Supabase kakvbirmgcnojxtqjlwm · datos en vivo
        </p>
      </footer>
    </div>
  )
}
