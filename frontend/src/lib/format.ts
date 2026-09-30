/** "I", "I." or " I. " → "I." (the API is not consistent about the trailing dot). */
export const formatRoman = (roman?: string | null): string => {
  const r = (roman || '').trim()
  if (!r) return ''
  return r.endsWith('.') ? r : `${r}.`
}

/** Local calendar date as YYYY-MM-DD (toISOString would give the UTC date). */
export const localISODate = (d: Date = new Date()): string => {
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  return `${d.getFullYear()}-${mm}-${dd}`
}

export const daysAgo = (n: number): string => {
  const d = new Date()
  d.setDate(d.getDate() - n)
  return localISODate(d)
}

export const monthStart = (): string => {
  const d = new Date()
  return localISODate(new Date(d.getFullYear(), d.getMonth(), 1))
}

/** "2026-09-30" → "30/09" */
export const shortDate = (iso: string): string => {
  const [, m, d] = iso.split('-')
  return `${d}/${m}`
}

/** "2026-09-30" → "30/09/2026" */
export const khDate = (iso: string): string => {
  const [y, m, d] = iso.split('-')
  return `${d}/${m}/${y}`
}

/** "I." + title → "I. title" */
export const formatCategory = (roman?: string | null, title?: string | null): string =>
  [formatRoman(roman), title || ''].filter(Boolean).join(' ')
