function InfoRow({ label, value, tone = 'default' }) {
  const toneClass = tone === 'up' ? 'text-up' : tone === 'down' ? 'text-down' : 'text-ink-900'
  return (
    <div className="flex items-center justify-between py-1.5">
      <span className="text-ink-500 text-xs">{label}</span>
      <span className={`font-mono text-xs font-medium tabular ${toneClass}`}>{value}</span>
    </div>
  )
}

export default function ManagementPanel({ operaciones, lastSignal }) {
  const abiertas = operaciones.filter((o) => o.estado === 'ABIERTA')
  const hoy = operaciones.filter(
    (o) => new Date(o.creado_en).toDateString() === new Date().toDateString()
  )

  return (
    <div className="border border-hairline bg-panel rounded-md overflow-hidden">
      <div className="px-4 py-2.5 border-b border-hairline">
        <h3 className="font-display text-[13px] font-semibold text-ink-900 tracking-wide">Gestión</h3>
      </div>
      <div className="px-4 py-2 divide-y divide-hairline">
        <InfoRow label="Posiciones abiertas" value={abiertas.length} />
        <InfoRow label="Trades hoy" value={hoy.length} />
        <InfoRow label="Lotaje última señal" value={lastSignal ? (lastSignal.lote ?? '—') : '—'} />
        <InfoRow
          label="SL última señal"
          value={lastSignal ? lastSignal.stop_loss : '—'}
          tone="down"
        />
      </div>
    </div>
  )
}
