const STYLES = {
  GOLD: 'border-sym-gold/30 text-sym-gold bg-sym-gold/[0.08]',
  SILVER: 'border-sym-silver/30 text-sym-silver bg-sym-silver/[0.08]',
  US100CASH: 'border-sym-nasdaq/30 text-sym-nasdaq bg-sym-nasdaq/[0.08]',
  US30CASH: 'border-sym-us30/30 text-sym-us30 bg-sym-us30/[0.08]',
  EURUSD: 'border-sym-eur/30 text-sym-eur bg-sym-eur/[0.08]',
}

function resolveKey(symbol) {
  const s = symbol?.toUpperCase() || ''
  if (s.includes('GOLD') || s.includes('XAU')) return 'GOLD'
  if (s.includes('SILVER') || s.includes('XAG')) return 'SILVER'
  if (s.includes('US100')) return 'US100CASH'
  if (s.includes('US30')) return 'US30CASH'
  if (s.includes('EUR')) return 'EURUSD'
  return 'US100CASH'
}

export default function SymbolBadge({ symbol }) {
  const key = resolveKey(symbol)
  return (
    <span
      className={`inline-flex items-center rounded-sm border px-1.5 py-0.5 text-[11px] font-mono font-medium tracking-wide ${STYLES[key]}`}
    >
      {symbol}
    </span>
  )
}
