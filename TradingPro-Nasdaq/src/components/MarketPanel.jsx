import { getSessionInfo } from '../lib/session.js'

function InfoRow({ label, value, tone = 'default' }) {
  const toneClass = tone === 'up' ? 'text-up' : tone === 'muted' ? 'text-ink-400' : 'text-ink-900'
  return (
    <div className="flex items-center justify-between py-1.5">
      <span className="text-ink-500 text-xs">{label}</span>
      <span className={`font-mono text-xs font-medium tabular ${toneClass}`}>{value}</span>
    </div>
  )
}

export default function MarketPanel({ symbolLabel, lastSignal, now }) {
  const session = getSessionInfo(now)

  return (
    <div className="border border-hairline bg-panel rounded-md overflow-hidden">
      <div className="px-4 py-2.5 border-b border-hairline">
        <h3 className="font-display text-[13px] font-semibold text-ink-900 tracking-wide">Mercado</h3>
      </div>
      <div className="px-4 py-2 divide-y divide-hairline">
        <InfoRow label="Símbolo" value={symbolLabel} />
        <InfoRow
          label="Precio última señal"
          value={lastSignal ? lastSignal.precio_entrada : '— sin señales'}
        />
        <InfoRow label="Sesión" value={session.label} tone={session.tone} />
        <InfoRow label="Estrategia última señal" value={lastSignal ? lastSignal.estrategia : '—'} />
      </div>
    </div>
  )
}
