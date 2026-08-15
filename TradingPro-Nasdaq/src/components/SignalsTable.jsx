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

export default function SignalsTable({ signals, loading }) {
  return (
    <div className="border border-hairline bg-panel rounded-md overflow-hidden">
      <div className="px-4 py-2.5 border-b border-hairline flex items-center justify-between">
        <h2 className="font-display text-[13px] font-semibold text-ink-900 tracking-wide">
          Señales recientes
        </h2>
        <span className="text-[11px] font-mono text-ink-500">
          {signals.length} en cola
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-[11px] uppercase tracking-widest text-ink-500 font-mono border-b border-hairline">
              <th className="px-4 py-2 font-medium">Activo</th>
              <th className="px-4 py-2 font-medium">Estrategia</th>
              <th className="px-4 py-2 font-medium">Dir.</th>
              <th className="px-4 py-2 font-medium text-right">Entrada</th>
              <th className="px-4 py-2 font-medium text-right">SL</th>
              <th className="px-4 py-2 font-medium text-right">TP</th>
              <th className="px-4 py-2 font-medium">Estado</th>
              <th className="px-4 py-2 font-medium text-right">Hace</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-hairline">
            {loading && (
              <tr>
                <td colSpan={8} className="px-4 py-8 text-center text-ink-500 font-mono text-xs">
                  Cargando señales...
                </td>
              </tr>
            )}
            {!loading && signals.length === 0 && (
              <tr>
                <td colSpan={8} className="px-4 py-10 text-center text-ink-500 text-xs">
                  Todavía no hay señales registradas.
                </td>
              </tr>
            )}
            {signals.map((s) => (
              <tr key={s.id} className="hover:bg-paper transition-colors">
                <td className="px-4 py-2.5">
                  <SymbolBadge symbol={s.symbol} />
                </td>
                <td className="px-4 py-2.5 text-ink-700">{s.estrategia}</td>
                <td className="px-4 py-2.5">
                  <span
                    className={`font-mono text-xs font-semibold ${
                      s.direccion === 'BUY' ? 'text-up' : 'text-down'
                    }`}
                  >
                    {s.direccion}
                  </span>
                </td>
                <td className="px-4 py-2.5 text-right font-mono tabular text-ink-900">
                  {s.precio_entrada}
                </td>
                <td className="px-4 py-2.5 text-right font-mono tabular text-ink-500">
                  {s.stop_loss}
                </td>
                <td className="px-4 py-2.5 text-right font-mono tabular text-ink-500">
                  {s.take_profit}
                </td>
                <td className="px-4 py-2.5">
                  <span
                    className={`inline-block rounded-sm px-1.5 py-0.5 font-mono text-[10px] font-medium ${ESTADO_STYLES[s.estado] || 'text-ink-500 bg-ink-300/20'}`}
                  >
                    {s.estado}
                  </span>
                </td>
                <td className="px-4 py-2.5 text-right font-mono text-xs text-ink-500">
                  {timeAgo(s.creado_en)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
