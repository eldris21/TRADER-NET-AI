export default function StatCard({ label, value, sub, tone = 'default' }) {
  const toneClass =
    tone === 'up'
      ? 'text-signal-green'
      : tone === 'down'
      ? 'text-signal-red'
      : 'text-slate-100'

  return (
    <div className="border border-ink-700 bg-ink-900/60 rounded-lg px-4 py-3">
      <div className="text-[11px] uppercase tracking-widest text-slate-500 font-mono">
        {label}
      </div>
      <div className={`mt-1 text-2xl font-display font-semibold tabular ${toneClass}`}>
        {value}
      </div>
      {sub && <div className="mt-0.5 text-xs text-slate-500 font-mono">{sub}</div>}
    </div>
  )
}
