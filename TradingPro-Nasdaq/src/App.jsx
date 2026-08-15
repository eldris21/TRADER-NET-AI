import { useEffect, useState } from 'react'
import { supabase } from './lib/supabase.js'
import { SYMBOLS, resolveSymbolKey, getSymbolConfig } from './lib/symbols.js'
import { getSessionInfo } from './lib/session.js'
import StatCard from './components/StatCard.jsx'
import PerformanceStrip from './components/PerformanceStrip.jsx'
import TradingViewChart from './components/TradingViewChart.jsx'
import SignalFeed from './components/SignalFeed.jsx'
import MarketPanel from './components/MarketPanel.jsx'
import ManagementPanel from './components/ManagementPanel.jsx'
import UnavailablePanel from './components/UnavailablePanel.jsx'

export default function App() {
  const [signals, setSignals] = useState([])
  const [operaciones, setOperaciones] = useState([])
  const [loading, setLoading] = useState(true)
  const [now, setNow] = useState(new Date())
  const [activeSymbol, setActiveSymbol] = useState('GOLD')

  useEffect(() => {
    const clock = setInterval(() => setNow(new Date()), 1000)
    return () => clearInterval(clock)
  }, [])

  useEffect(() => {
    let mounted = true

    async function load() {
      try {
        setLoading(true)
        const [{ data: sigData }, { data: opData }] = await Promise.all([
          supabase.from('idx_senales').select('*').order('creado_en', { ascending: false }).limit(30),
          supabase.from('idx_operaciones').select('*').order('creado_en', { ascending: false }).limit(30),
        ])
        if (!mounted) return
        setSignals(sigData || [])
        setOperaciones(opData || [])
      } catch (err) {
        console.error('Error cargando datos de Supabase:', err)
      } finally {
        if (mounted) setLoading(false)
      }
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
    (o) => o.estado === 'CERRADA' && new Date(o.cerrado_en).toDateString() === new Date().toDateString()
  )
  const pnlHoy = cerradasHoy.reduce((acc, o) => acc + (o.resultado || 0), 0)
  const pendientes = signals.filter((s) => s.estado === 'PENDING').length

  const symbolConfig = getSymbolConfig(activeSymbol)
  const signalsForSymbol = signals.filter((s) => resolveSymbolKey(s.symbol) === activeSymbol)
  const lastSignal = signalsForSymbol[0] || null
  const session = getSessionInfo(now)

  return (
    <div className="min-h-screen bg-paper">
      <header className="border-b border-hairline bg-panel">
        <div className="max-w-[1400px] mx-auto px-5 py-3 flex items-center justify-between flex-wrap gap-3">
          <div className="flex items-center gap-3">
            <span className="h-7 w-7 rounded-full bg-up flex items-center justify-center text-white text-sm shrink-0">
              <i className="ti ti-check" style={{ fontSize: 16 }} />
            </span>
            <div>
              <div className="flex items-baseline gap-2">
                <h1 className="font-display text-base font-semibold tracking-tight text-ink-900">
                  TradingPro Nasdaq
                </h1>
                <span className="font-mono text-[11px] text-brand tracking-widest uppercase">
                  {symbolConfig.label}
                </span>
              </div>
              <p className="text-[11px] text-ink-500 font-mono mt-0.5">
                {lastSignal ? `Última señal ${lastSignal.precio_entrada}` : 'Sin señales aún'}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            <span
              className={`inline-flex items-center rounded-sm border px-2 py-1 text-[10px] font-mono font-medium uppercase tracking-widest ${
                session.tone === 'up' ? 'border-up/30 bg-up-soft text-up' : 'border-hairline-strong bg-paper text-ink-500'
              }`}
            >
              {session.label}
            </span>
            <span className="font-mono text-sm tabular text-ink-700">
              {now.toLocaleTimeString('es-DO', { hour12: false })} RD
            </span>
          </div>
        </div>
        <div className="max-w-[1400px] mx-auto px-5 pb-3 flex items-center gap-2 overflow-x-auto">
          {SYMBOLS.map((s) => (
            <button
              key={s.key}
              onClick={() => setActiveSymbol(s.key)}
              className={`px-3 py-1.5 rounded-sm text-xs font-mono font-medium whitespace-nowrap border transition-colors ${
                activeSymbol === s.key
                  ? 'bg-brand text-white border-brand'
                  : 'bg-panel text-ink-500 border-hairline hover:border-hairline-strong'
              }`}
            >
              {s.label}
            </button>
          ))}
        </div>
      </header>

      <main className="max-w-[1400px] mx-auto px-5 py-5 space-y-4">
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

        <section className="grid grid-cols-1 xl:grid-cols-[1fr_320px] gap-4">
          <div className="space-y-4">
            <TradingViewChart tvSymbol={symbolConfig.tvSymbol} />
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <MarketPanel symbolLabel={symbolConfig.label} lastSignal={lastSignal} now={now} />
              <ManagementPanel operaciones={operaciones} lastSignal={lastSignal} />
              <UnavailablePanel
                title="Liquidez y confluencia"
                note="Requiere sincronizar el motor SMC (structure.py) hacia Supabase — hoy solo vive en el backend Python, no en idx_senales."
              />
            </div>
          </div>
          <SignalFeed
            signals={signals}
            loading={loading}
            symbolKeyFilter={activeSymbol}
            resolveSymbolKey={resolveSymbolKey}
          />
        </section>

        <section>
          <PerformanceStrip operaciones={operaciones} loading={loading} />
        </section>
      </main>

      <footer className="max-w-[1400px] mx-auto px-5 py-8 text-center">
        <p className="text-[11px] font-mono text-ink-400">
          TradingPro-Nasdaq · datos en vivo desde Supabase · gráfico TradingView
        </p>
      </footer>
    </div>
  )
}
