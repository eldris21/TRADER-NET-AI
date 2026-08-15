import { useEffect, useRef } from 'react'

export default function TradingViewChart({ tvSymbol }) {
  const containerRef = useRef(null)

  useEffect(() => {
    if (!containerRef.current) return
    containerRef.current.innerHTML = ''

    const script = document.createElement('script')
    script.src = 'https://s3.tradingview.com/tv.js'
    script.async = true
    script.onload = () => {
      if (!window.TradingView || !containerRef.current) return
      new window.TradingView.widget({
        autosize: true,
        symbol: tvSymbol,
        interval: '5',
        timezone: 'America/Santo_Domingo',
        theme: 'light',
        style: '1',
        locale: 'es',
        toolbar_bg: '#ffffff',
        enable_publishing: false,
        allow_symbol_change: false,
        hide_top_toolbar: false,
        hide_legend: false,
        studies: ['STD;EMA'],
        container_id: containerRef.current.id,
      })
    }
    containerRef.current.appendChild(script)

    return () => {
      if (containerRef.current) containerRef.current.innerHTML = ''
    }
  }, [tvSymbol])

  return (
    <div className="border border-hairline bg-panel rounded-md overflow-hidden">
      <div
        id={`tv-chart-${tvSymbol.replace(/[^a-zA-Z0-9]/g, '')}`}
        ref={containerRef}
        style={{ height: 460 }}
      />
    </div>
  )
}
