const PERIODS = [
  { key: 'hoy', label: 'Hoy', days: 1 },
  { key: 'semana', label: 'Esta semana', days: 7 },
  { key: 'mes', label: 'Este mes', days: 30 },
  { key: 'total', label: 'Total (30 reg.)', days: null },
]

function computeStats(operaciones, days) {
  const cerradas = operaciones.filter((o) => o.estado === 'CERRADA' && o.cerrado_en)
  const scoped =
    days === null
      ? cerradas
      : cerradas.filter(
          (o) => Date.now() - new Date(o.cerrado_en).getTime() <= days * 86400000
        )

  const trades = scoped.length
  const ganadas = scoped.filter((o) => (o.resultado || 0) > 0).length
  const pnl = scoped.reduce((acc, o) => acc + (o.resultado || 0), 0)
  const winRate = trades > 0 ? (ganadas / trades) * 100 : null

  return { trades, ganadas, pnl, winRate }
}

export default function PerformanceStrip({ operaciones, loading }) {
  return (
    <div className="border border-hairline bg-panel rounded-md overflow-hidden">
      <div className="px-4 py-2.5 border-b border-hairline">
        <h2 className="font-display text-[13px] font-semibold text-ink-900 tracking-wide">
          Rendimiento por periodo
        </h2>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-[11px] uppercase tracking-widest text-ink-500 font-mono border-b border-hairline">
              <th className="px-4 py-2 font-medium">Periodo</th>
              <th className="px-4 py-2 font-medium text-right">Operaciones</th>
              <th className="px-4 py-2 font-medium text-right">Ganadas</th>
              <th className="px-4 py-2 font-medium text-right">Win %</th>
              <th className="px-4 py-2 font-medium text-right">P&amp;L</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-hairline">
            {loading && (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-ink-500 font-mono text-xs">
                  Calculando...
                </td>
              </tr>
            )}
            {!loading &&
              PERIODS.map((p) => {
                const s = computeStats(operaciones, p.days)
                return (
                  <tr key={p.key} className="hover:bg-paper transition-colors">
                    <td className="px-4 py-2.5 text-ink-700">{p.label}</td>
                    <td className="px-4 py-2.5 text-right font-mono tabular text-ink-900">
                      {s.trades}
                    </td>
                    <td className="px-4 py-2.5 text-right font-mono tabular text-ink-500">
                      {s.trades > 0 ? s.ganadas : '—'}
                    </td>
                    <td className="px-4 py-2.5 text-right font-mono tabular text-ink-500">
                      {s.winRate === null ? '—' : `${s.winRate.toFixed(0)}%`}
                    </td>
                    <td
                      className={`px-4 py-2.5 text-right font-mono tabular font-medium ${
                        s.trades === 0
                          ? 'text-ink-500'
                          : s.pnl > 0
                          ? 'text-up'
                          : s.pnl < 0
                          ? 'text-down'
                          : 'text-ink-900'
                      }`}
                    >
                      {s.trades === 0 ? '—' : `${s.pnl >= 0 ? '+' : ''}$${s.pnl.toFixed(2)}`}
                    </td>
                  </tr>
                )
              })}
          </tbody>
        </table>
      </div>
      <div className="px-4 py-2 border-t border-hairline text-[11px] font-mono text-ink-500">
        Calculado sobre las últimas 30 operaciones sincronizadas — no es el histórico completo.
      </div>
    </div>
  )
}
