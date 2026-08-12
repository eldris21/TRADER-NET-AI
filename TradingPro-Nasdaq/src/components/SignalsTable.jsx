import SymbolBadge from './SymbolBadge.jsx'

const ESTADO_STYLES = {
  PENDING: 'text-signal-amber',
  EJECUTADA: 'text-signal-green',
  EXPIRADA: 'text-slate-500',
  RECHAZADA: 'text-signal-red',
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
    <div className="border border-ink-700 bg-ink-900/60 rounded-lg overflow-hidden">
      <div className="px-4 py-3 border-b border-ink-700 flex items-center justify-between">
        <h2 className="font-display text-sm font-semibold text-slate-200 tracking-wide">
          Señales recientes
        </h2>
        <span className="text-[11px] font-mono text-slate-500">
          {signals.length} en cola
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-[11px] uppercase tracking-widest text-slate-500 font-mono border-b border-ink-700">
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
          <tbody className="divide-y divide-ink-800">
            {loading && (
              <tr>
                <td colSpan={8} className="px-4 py-8 text-center text-slate-500 font-mono text-xs">
                  Cargando señales...
                </td>
              </tr>
            )}
            {!loading && signals.length === 0 && (
              <tr>
                <td colSpan={8} className="px-4 py-10 text-center text-slate-500 text-xs">
                  Todavía no hay señales registradas para Nasdaq/US30.
                </td>
              </tr>
            )}
            {signals.map((s) => (
              <tr key={s.id} className="hover:bg-ink-850/60 transition-colors">
                <td className="px-4 py-2.5">
                  <SymbolBadge symbol={s.symbol} />
                </td>
                <td className="px-4 py-2.5 text-slate-300">{s.estrategia}</td>
                <td className="px-4 py-2.5">
                  <span
                    className={`font-mono text-xs font-semibold ${
                      s.direccion === 'BUY' ? 'text-signal-green' : 'text-signal-red'
                    }`}
                  >
                    {s.direccion}
                  </span>
                </td>
                <td className="px-4 py-2.5 text-right font-mono tabular text-slate-300">
                  {s.precio_entrada}
                </td>
                <td className="px-4 py-2.5 text-right font-mono tabular text-slate-500">
                  {s.stop_loss}
                </td>
                <td className="px-4 py-2.5 text-right font-mono tabular text-slate-500">
                  {s.take_profit}
                </td>
                <td className="px-4 py-2.5">
                  <span
                    className={`font-mono text-[11px] font-medium ${ESTADO_STYLES[s.estado] || 'text-slate-400'}`}
                  >
                    {s.estado}
                  </span>
                </td>
                <td className="px-4 py-2.5 text-right font-mono text-xs text-slate-500">
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
