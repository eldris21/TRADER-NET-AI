import SymbolBadge from './SymbolBadge.jsx'

export default function PositionsPanel({ operaciones, loading }) {
  const abiertas = operaciones.filter((o) => o.estado === 'ABIERTA')

  return (
    <div className="border border-hairline bg-panel rounded-md overflow-hidden">
      <div className="px-4 py-2.5 border-b border-hairline flex items-center justify-between">
        <h2 className="font-display text-[13px] font-semibold text-ink-900 tracking-wide">
          Operaciones abiertas
        </h2>
        <span className="text-[11px] font-mono text-ink-500">{abiertas.length} activas</span>
      </div>

      <div className="p-3 space-y-2">
        {loading && (
          <p className="text-center text-ink-500 font-mono text-xs py-6">Cargando...</p>
        )}
        {!loading && abiertas.length === 0 && (
          <p className="text-center text-ink-500 text-xs py-6">
            Sin posiciones abiertas en este momento.
          </p>
        )}
        {abiertas.map((op) => (
          <div
            key={op.id}
            className="flex items-center justify-between border border-hairline rounded-sm px-3 py-2.5 bg-paper/70"
          >
            <div className="flex items-center gap-2">
              <SymbolBadge symbol={op.symbol} />
              <span
                className={`font-mono text-xs font-semibold ${
                  op.direccion === 'BUY' ? 'text-up' : 'text-down'
                }`}
              >
                {op.direccion}
              </span>
            </div>
            <div className="text-right">
              <div className="font-mono text-sm tabular text-ink-900">
                {op.lote} lotes @ {op.precio_entrada}
              </div>
              <div className="font-mono text-[11px] text-ink-500">
                Ticket #{op.ticket}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
