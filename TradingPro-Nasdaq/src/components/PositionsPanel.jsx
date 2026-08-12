import SymbolBadge from './SymbolBadge.jsx'

export default function PositionsPanel({ operaciones, loading }) {
  const abiertas = operaciones.filter((o) => o.estado === 'ABIERTA')

  return (
    <div className="border border-ink-700 bg-ink-900/60 rounded-lg overflow-hidden">
      <div className="px-4 py-3 border-b border-ink-700 flex items-center justify-between">
        <h2 className="font-display text-sm font-semibold text-slate-200 tracking-wide">
          Operaciones abiertas
        </h2>
        <span className="text-[11px] font-mono text-slate-500">{abiertas.length} activas</span>
      </div>

      <div className="p-4 space-y-3">
        {loading && (
          <p className="text-center text-slate-500 font-mono text-xs py-6">Cargando...</p>
        )}
        {!loading && abiertas.length === 0 && (
          <p className="text-center text-slate-500 text-xs py-6">
            Sin posiciones abiertas en este momento.
          </p>
        )}
        {abiertas.map((op) => (
          <div
            key={op.id}
            className="flex items-center justify-between border border-ink-700 rounded-md px-3 py-2.5 bg-ink-850/40"
          >
            <div className="flex items-center gap-2">
              <SymbolBadge symbol={op.symbol} />
              <span
                className={`font-mono text-xs font-semibold ${
                  op.direccion === 'BUY' ? 'text-signal-green' : 'text-signal-red'
                }`}
              >
                {op.direccion}
              </span>
            </div>
            <div className="text-right">
              <div className="font-mono text-sm tabular text-slate-200">
                {op.lote} lotes @ {op.precio_entrada}
              </div>
              <div className="font-mono text-[11px] text-slate-500">
                Ticket #{op.ticket}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
