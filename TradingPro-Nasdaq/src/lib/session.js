// Calcula la sesión de trading activa según hora RD (America/Santo_Domingo, UTC-4 fijo, sin DST)
export function getSessionInfo(date = new Date()) {
  const rdHour = (date.getUTCHours() - 4 + 24) % 24
  if (rdHour >= 3 && rdHour < 6) return { label: 'Londres', tone: 'up' }
  if (rdHour >= 9 && rdHour < 12) return { label: 'Nueva York', tone: 'up' }
  return { label: 'Zona muerta', tone: 'muted' }
}
