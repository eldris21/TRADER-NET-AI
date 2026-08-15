// Config de los 5 activos que opera SMC-Bot-5Activos.
// tvSymbol = símbolo equivalente en TradingView para el widget de gráfico.
export const SYMBOLS = [
  { key: 'GOLD', label: 'Gold', dbMatch: (s) => s?.toUpperCase().includes('GOLD') || s?.toUpperCase().includes('XAU'), tvSymbol: 'OANDA:XAUUSD', badge: 'gold' },
  { key: 'SILVER', label: 'Silver', dbMatch: (s) => s?.toUpperCase().includes('SILVER') || s?.toUpperCase().includes('XAG'), tvSymbol: 'OANDA:XAGUSD', badge: 'silver' },
  { key: 'US100CASH', label: 'US100Cash', dbMatch: (s) => s?.toUpperCase().includes('US100'), tvSymbol: 'CAPITALCOM:US100', badge: 'nasdaq' },
  { key: 'US30CASH', label: 'US30Cash', dbMatch: (s) => s?.toUpperCase().includes('US30'), tvSymbol: 'CAPITALCOM:US30', badge: 'us30' },
  { key: 'EURUSD', label: 'EURUSD', dbMatch: (s) => s?.toUpperCase().includes('EUR'), tvSymbol: 'OANDA:EURUSD', badge: 'eur' },
]

export function resolveSymbolKey(symbol) {
  const found = SYMBOLS.find((s) => s.dbMatch(symbol))
  return found ? found.key : 'US100CASH'
}

export function getSymbolConfig(key) {
  return SYMBOLS.find((s) => s.key === key) || SYMBOLS[2]
}
