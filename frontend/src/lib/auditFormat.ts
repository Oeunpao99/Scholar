// Turns raw audit-log data (English field names, JSON diffs) into Khmer text.

export const FIELD_LABELS: Record<string, string> = {
  today_total: 'សិស្សថ្មី',
  today_female: 'ស្រី',
  today_pp: 'ភ្នំពេញ',
  today_kp: 'ខេត្ត',
  total: 'សរុប',
  female: 'ស្រី',
  pp: 'ភ្នំពេញ',
  kp: 'ខេត្ត',
  grades: 'និទ្ទេស',
  note: 'កំណត់សម្គាល់',
  report_date: 'កាលបរិច្ឆេទ',
  category_id: 'ផ្នែក',
  category_code: 'ផ្នែក',
  is_locked: 'ចាក់សោ',
  source: 'ប្រភព',
  full_name: 'ឈ្មោះពេញ',
  username: 'ឈ្មោះគណនី',
  email: 'អ៊ីមែល',
  role: 'តួនាទី',
  is_active: 'គណនីសកម្ម',
  current_year: 'ឆ្នាំសិក្សា',
  title_template: 'គំរូចំណងជើង',
  format: 'ទម្រង់ឯកសារ',
  rows: 'ចំនួនជួរ',
  provider: 'ម៉ាស៊ីនវិភាគ',
  date: 'កាលបរិច្ឆេទ',
}

export const ENTITY_LABELS: Record<string, string> = {
  daily_report: 'របាយការណ៍ប្រចាំថ្ងៃ',
  user: 'អ្នកប្រើប្រាស់',
  setting: 'ការកំណត់',
  category: 'ផ្នែក',
  auth: 'ការចូលប្រព័ន្ធ',
  ai_extraction: 'ការស្កេនទិន្នន័យ',
  export: 'ការនាំចេញ',
  telegram: 'Telegram',
  database: 'មូលដ្ឋានទិន្នន័យ',
}

/** Audit actions → Khmer label + a tone for the badge. */
export const ACTION_META: Record<string, { label: string; tone: 'emerald' | 'amber' | 'rose' | 'blue' | 'cyan' }> = {
  create: { label: 'បង្កើត', tone: 'emerald' },
  bulk_create: { label: 'បង្កើតច្រើន', tone: 'emerald' },
  update: { label: 'កែប្រែ', tone: 'amber' },
  delete: { label: 'លុប', tone: 'rose' },
  login: { label: 'ចូលប្រព័ន្ធ', tone: 'blue' },
  logout: { label: 'ចាកចេញ', tone: 'blue' },
  export: { label: 'នាំចេញ', tone: 'cyan' },
  import: { label: 'នាំចូល', tone: 'cyan' },
  ai_parse: { label: 'ស្កេនទិន្នន័យ', tone: 'cyan' },
  send: { label: 'ផ្ញើ Telegram', tone: 'cyan' },
  backup: { label: 'បម្រុងទុក', tone: 'blue' },
  restore: { label: 'ស្ដារទិន្នន័យ', tone: 'rose' },
  settings_change: { label: 'ប្តូរការកំណត់', tone: 'amber' },
}

const CATEGORY_LABELS: Record<string, string> = {
  current_year: 'ផ្នែក I',
  before_current_year: 'ផ្នែក II',
  other_province: 'ផ្នែក III',
}

const ROLE_LABELS: Record<string, string> = {
  superadmin: 'អ្នកគ្រប់គ្រងជាន់ខ្ពស់',
  admin: 'អ្នករៀបចំប្រព័ន្ធ',
  manager: 'អ្នកគ្រប់គ្រង',
  staff: 'បុគ្គលិក',
  viewer: 'អ្នកមើល',
}

export const fieldLabel = (key: string) => FIELD_LABELS[key] || key
export const entityLabel = (key: string) => ENTITY_LABELS[key] || key
export const actionMeta = (action: string) => ACTION_META[action.toLowerCase()] || { label: action, tone: 'blue' as const }
const cat = (code: string) => CATEGORY_LABELS[code] || code
const ymdToKh = (iso: string) => iso.replace(/^(\d{4})-(\d{2})-(\d{2})$/, '$3/$2/$1')

// Every summary sentence the backend writes (see backend app/services/*) → Khmer.
const SUMMARY_RULES: Array<[RegExp, (m: RegExpMatchArray) => string]> = [
  [/^Updated (\w+) fields: (.+)$/, (m) =>
    `បានកែប្រែ${entityLabel(m[1])}: ${[...new Set(m[2].split(',').map((f) => fieldLabel(f.trim())))].join(', ')}`],
  [/^(.+) signed in$/, (m) => `${m[1]} បានចូលប្រព័ន្ធ`],
  [/^Signed out$/, () => 'បានចាកចេញពីប្រព័ន្ធ'],
  [/^Failed login attempt$/, () => 'ការព្យាយាមចូលប្រព័ន្ធមិនបានសម្រេច'],
  [/^Password reset for (\S+) by (\S+)$/, (m) => `${m[2]} បានកំណត់ពាក្យសម្ងាត់ថ្មីឱ្យ ${m[1]}`],
  [/^AI extraction via ([\w+]+): (\d+) categor\(y\/ies\), confidence ([\d.]+)$/, (m) =>
    `បានស្កេនទិន្នន័យ: រកឃើញ ${m[2]} ផ្នែក · ភាពជឿជាក់ ${Math.round(parseFloat(m[3]) * 100)}%`],
  [/^Created report (\S+) \/ (\w+): total=(\d+) female=(\d+) pp=(\d+) kp=(\d+)$/, (m) =>
    `បានបញ្ចូលរបាយការណ៍ ${ymdToKh(m[1])} · ${cat(m[2])}: ${m[3]} នាក់ (ស្រី ${m[4]} · ភ្នំពេញ ${m[5]} · ខេត្ត ${m[6]})`],
  [/^Deleted report (\S+) \/ (\w+)$/, (m) => `បានលុបរបាយការណ៍ ${ymdToKh(m[1])} · ${cat(m[2])}`],
  [/^Created user (\S+) \((\w+)\)$/, (m) => `បានបង្កើតអ្នកប្រើប្រាស់ ${m[1]} (${ROLE_LABELS[m[2]] || m[2]})`],
  [/^Deleted user (\S+)$/, (m) => `បានលុបអ្នកប្រើប្រាស់ ${m[1]}`],
  [/^Activated (\S+)$/, (m) => `បានបើកគណនី ${m[1]}`],
  [/^Deactivated (\S+)$/, (m) => `បានផ្អាកគណនី ${m[1]}`],
  [/^Exported (\d+) row\(s\) as (\w+) \((.+) - (.+)\)$/, (m) =>
    `បាននាំចេញ ${m[1]} ជួរ ជា ${m[2]} (${ymdToKh(m[3])} – ${ymdToKh(m[4])})`],
  [/^Sent Telegram report for (\S+) to (.+)$/, (m) => `បានផ្ញើរបាយការណ៍ ${ymdToKh(m[1])} ទៅ Telegram ${m[2]}`],
]

/** Backend (English) audit summary → Khmer sentence; unknown text is shown as-is. */
export const khmerSummary = (summary?: string | null): string => {
  if (!summary) return 'សកម្មភាពក្នុងប្រព័ន្ធ'
  for (const [re, fmt] of SUMMARY_RULES) {
    const m = summary.match(re)
    if (m) return fmt(m)
  }
  return summary
}

/** ISO timestamp → "30/09/2026 · 09:45" (24h, local time). */
export const khDateTime = (iso?: string | null): string => {
  if (!iso) return '–'
  const d = new Date(iso)
  const p = (n: number) => String(n).padStart(2, '0')
  return `${p(d.getDate())}/${p(d.getMonth() + 1)}/${d.getFullYear()} · ${p(d.getHours())}:${p(d.getMinutes())}`
}

type Counts = { total?: number; female?: number; pp?: number; kp?: number }

/** Any value → short Khmer text. Grade maps become "D: 2 នាក់ (ស្រី 1 · ភ្នំពេញ 1 · ខេត្ត 1)". */
export const formatValue = (value: unknown): string => {
  if (value === null || value === undefined || value === '') return '–'
  if (typeof value === 'boolean') return value ? 'បាទ/ចាស' : 'ទេ'
  if (typeof value !== 'object') return String(value)

  const entries = Object.entries(value as Record<string, unknown>)
  const isGradeMap = entries.length > 0 && entries.every(([k, v]) => /^[A-E]$/.test(k) && typeof v === 'object')
  if (isGradeMap) {
    return entries
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([g, v]) => {
        const c = v as Counts
        return `${g}: ${c.total ?? 0} នាក់ (ស្រី ${c.female ?? 0} · ភ្នំពេញ ${c.pp ?? 0} · ខេត្ត ${c.kp ?? 0})`
      })
      .join('\n')
  }
  if (entries.length === 0) return '–'
  return entries.map(([k, v]) => `${fieldLabel(k)}: ${formatValue(v)}`).join('\n')
}

export interface ChangeRow {
  field: string
  before: string
  after: string
  changed: boolean
}

/**
 * Edits are stored as { field: { from, to } }; creates/other actions as a flat
 * { field: value } object. Returns rows for a before → after table, or
 * null when the change set is a flat snapshot (render as a simple list).
 */
export const changeRows = (changes: unknown): ChangeRow[] | null => {
  if (!changes || typeof changes !== 'object') return null
  const entries = Object.entries(changes as Record<string, unknown>)
  const isDiff = entries.length > 0 && entries.every(([, v]) => v && typeof v === 'object' && ('from' in (v as object) || 'to' in (v as object)))
  if (!isDiff) return null
  return entries
    .map(([key, v]) => {
      const { from, to } = v as { from: unknown; to: unknown }
      return {
        field: fieldLabel(key),
        before: formatValue(from),
        after: formatValue(to),
        changed: JSON.stringify(from) !== JSON.stringify(to),
      }
    })
    .sort((a, b) => Number(b.changed) - Number(a.changed))
}
