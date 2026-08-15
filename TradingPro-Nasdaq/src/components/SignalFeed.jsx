import SymbolBadge from './SymbolBadge.jsx'

const ESTADO_STYLES = {
  PENDING: 'text-amber bg-amber-soft',
  EJECUTADA: 'text-up bg-up-soft',
  EXPIRADA: 'text-ink-500 bg-ink-300/20',
  RECHAZADA: 'text-down bg-down-soft',
}

function timeAgo(iso) {
  const diffMs = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diffMs / 60000)
  if (mins < 1) return 'ahora'
  if (mins < 60) return `hace ${mins}m`
  const hrs = Math.floor(mins / 60)
  return `hace ${hrs}h`
}

export default function SignalFeed({ signals, loading, symbolKeyFilter, resolveSymbolKey }) {
  const filtered = symbolKeyFilter
    ? signals.filter((s) => resolveSymbolKey(s.symbol) === symbolKeyFilter)
    : signals

  return (
    <div className="border border-hairline bg-panel rounded-md overflow-hidden h-full flex flex-col">
      <div className="px-4 py-2.5 border-b border-hairline flex items-center justify-between shrink-0">
        <h2 className="font-display text-[13px] font-semibold text-ink-900 tracking-wide">
          En vivo desde Supabase
        </h2>
        <span className="text-[11px] font-mono text-ink-500">{filtered.length}</span>
      </div>
      <div className="overflow-y-auto divide-y divide-hairline" style={{ maxHeight: 520 }}>
        {loading && (
          <p className="text-center text-ink-500 font-mono text-xs py-8">Cargando...</p>
        )}
        {!loading && filtered.length === 0 && (
          <p className="text-center text-ink-500 text-xs py-8 px-3">
            Sin señales para este símbolo todavía.
          </p>
        )}
        {filtered.map((s) => (
          <div key={s.id} className="px-3 py-2.5">
            <div className="flex items-center justify-between mb-1.5">
              <div className="flex items-center gap-1.5">
                <span
                  className={`font-mono text-[10px] font-bold px-1.5 py-0.5 rounded-sm ${
                    s.direccion === 'BUY' ? 'text-up bg-up-soft' : 'text-down bg-down-soft'
                  }`}
                >
                  {s.direccion}
                </span>
                <span className="text-[11px] text-ink-500 font-mono">{s.estrategia}</span>
              </div>
              <span className="text-[10px] font-mono text-ink-400">{timeAgo(s.creado_en)}</span>
            </div>
            <div className="flex items-center justify-between">
              <SymbolBadge symbol={s.symbol} />
              <span className="font-mono text-sm font-semibold tabular text-ink-900">
                {s.precio_entrada}
              </span>
            </div>
            <div className="flex items-center justify-between mt-1 text-[11px] font-mono">
              <span className="text-down">SL {s.stop_loss}</span>
              <span className="text-up">TP {s.take_profit}</span>
              <span className={`px-1.5 py-0.5 rounded-sm text-[10px] ${ESTADO_STYLES[s.estado] || 'text-ink-500 bg-ink-300/20'}`}>
                {s.estado}
              </span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
