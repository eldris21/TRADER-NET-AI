export default function UnavailablePanel({ title, note }) {
  return (
    <div className="border border-hairline bg-panel rounded-md overflow-hidden">
      <div className="px-4 py-2.5 border-b border-hairline">
        <h3 className="font-display text-[13px] font-semibold text-ink-900 tracking-wide">{title}</h3>
      </div>
      <div className="px-4 py-6 text-center">
        <p className="text-xs text-ink-500">{note}</p>
      </div>
    </div>
  )
}
