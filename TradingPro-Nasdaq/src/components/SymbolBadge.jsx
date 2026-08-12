const STYLES = {
  NASDAQ: 'border-signal-violet/40 text-signal-violet bg-signal-violet/10',
  US30: 'border-signal-amber/40 text-signal-amber bg-signal-amber/10',
}

export default function SymbolBadge({ symbol }) {
  const key = symbol?.toUpperCase().includes('30') ? 'US30' : 'NASDAQ'
  return (
    <span
      className={`inline-flex items-center rounded-sm border px-1.5 py-0.5 text-[11px] font-mono font-medium tracking-wide ${STYLES[key]}`}
    >
      {symbol}
    </span>
  )
}
