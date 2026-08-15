export default function StatCard({ label, value, sub, tone = 'default' }) {
  const toneClass =
    tone === 'up' ? 'text-up' : tone === 'down' ? 'text-down' : 'text-ink-900'

  return (
    <div className="px-4 py-1 md:py-0 first:pl-0 last:pr-0">
      <div className="text-[11px] uppercase tracking-widest text-ink-500 font-mono">
        {label}
      </div>
      <div className={`mt-1 text-[22px] font-display font-semibold tabular leading-none ${toneClass}`}>
        {value}
      </div>
      {sub && <div className="mt-1 text-[11px] text-ink-500 font-mono">{sub}</div>}
    </div>
  )
}
