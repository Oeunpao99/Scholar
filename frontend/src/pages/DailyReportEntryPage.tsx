import React, { useEffect, useMemo, useState } from 'react'
import { Save, AlertCircle, CheckCircle2, Layers, RefreshCw, Keyboard } from 'lucide-react'
import confetti from 'canvas-confetti'
import { api } from '../lib/api'
import { formatRoman, shortCategory } from '../lib/format'
import { Category } from '../types'
import { DatePicker } from '../components/ui/DatePicker'

interface DailyReportEntryPageProps {
  initialDate?: string
}

type GradeLetter = 'A' | 'B' | 'C' | 'D' | 'E'
type Field = 'total' | 'female' | 'pp' | 'kp'

// Staff type what the report line gives:
//   "-និទ្ទេស D ចំនួន : 03 នាក់ ស្រី 02 នាក់ (PP: 01 នាក់, KP: 02 នាក់)"
// PP and KP can be typed in either order. ចំនួន = PP + KP must hold:
//  - with ចំនួន typed, the PP/KP not typed last is filled as ចំនួន − the other;
//  - with ចំនួន empty, it is filled as PP + KP.
interface GradeRow {
  grade: GradeLetter
  total: number
  female: number
  pp: number
  kp: number
}

// Per-cell typing state, kept apart from the values so "dirty" compares numbers only.
interface RowMeta {
  lock: 'pp' | 'kp' // which of the two the user typed last
  totalTyped: boolean // ចំនួន came from the user, not from PP + KP
}

type CategoryRows = Record<string, GradeRow[]>

const GRADES: GradeLetter[] = ['A', 'B', 'C', 'D', 'E']

const COLUMNS: Array<{ field: Field; label: string; hint: string }> = [
  { field: 'total', label: 'ចំនួន', hint: 'ចំនួនសិស្សសរុបនៃនិទ្ទេសនេះ' },
  { field: 'female', label: 'ស្រី', hint: 'ក្នុងនោះជាសិស្សស្រី' },
  { field: 'pp', label: 'ភ្នំពេញ (PP)', hint: 'ចំនួនដែលដាក់ពាក្យនៅភ្នំពេញ' },
  { field: 'kp', label: 'ខេត្ត (KP)', hint: 'ចំនួនដែលដាក់ពាក្យនៅខេត្ត' },
]

const emptyRows = (): GradeRow[] => GRADES.map((grade) => ({ grade, total: 0, female: 0, pp: 0, kp: 0 }))
const rowTotal = (r: GradeRow) => r.total
const splitMismatch = (r: GradeRow) => r.total > 0 && (r.pp > 0 || r.kp > 0) && r.pp + r.kp !== r.total
const today = () => new Date().toISOString().split('T')[0]

const sumRows = (rows: GradeRow[]) =>
  rows.reduce(
    (acc, r) => ({
      total: acc.total + r.total,
      female: acc.female + r.female,
      pp: acc.pp + r.pp,
      kp: acc.kp + r.kp,
    }),
    { total: 0, female: 0, pp: 0, kp: 0 }
  )

export const DailyReportEntryPage: React.FC<DailyReportEntryPageProps> = ({ initialDate }) => {
  const [reportDate, setReportDate] = useState<string>(initialDate || today())
  const [categories, setCategories] = useState<Category[]>([])
  const [selectedCode, setSelectedCode] = useState<string>('current_year')
  const [isBulkMode, setIsBulkMode] = useState<boolean>(false)

  const [rows, setRows] = useState<CategoryRows>({})
  const [meta, setMeta] = useState<Record<string, RowMeta[]>>({})
  const [notes, setNotes] = useState<Record<string, string>>({})
  // What is saved on the server, to detect unsaved edits and to update vs create.
  const [savedSnapshot, setSavedSnapshot] = useState<string>('{}')
  const [existingIds, setExistingIds] = useState<Record<string, string>>({})

  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [status, setStatus] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  useEffect(() => {
    api.getCategories()
      .then((res) => setCategories(res.items))
      .catch((err) => console.error('Failed to load categories', err))
  }, [])

  // Load the chosen day from scratch — never carry values over from another date.
  const loadDay = async (date: string) => {
    setLoading(true)
    setStatus(null)
    const nextRows: CategoryRows = {}
    const nextNotes: Record<string, string> = {}
    const ids: Record<string, string> = {}
    try {
      const reports = await api.getTodayReports(date)
      reports.forEach((rep) => {
        if (!rep.category_code) return
        nextRows[rep.category_code] = GRADES.map((grade) => {
          const g = rep.grades?.find((x) => x.grade === grade)
          const total = g?.total ?? 0
          const pp = g?.pp ?? 0
          return { grade, total, female: g?.female ?? 0, pp, kp: g?.kp ?? Math.max(0, total - pp) }
        })
        nextNotes[rep.category_code] = rep.note || ''
        if (rep.source !== 'missing') ids[rep.category_code] = rep.id
      })
    } catch (err) {
      console.error('Failed to fetch existing day report', err)
    } finally {
      setRows(nextRows)
      setMeta({})
      setNotes(nextNotes)
      setExistingIds(ids)
      setSavedSnapshot(JSON.stringify({ rows: nextRows, notes: nextNotes }))
      setLoading(false)
    }
  }

  useEffect(() => {
    if (reportDate) loadDay(reportDate)
  }, [reportDate])

  const rowsFor = (code: string) => rows[code] || emptyRows()

  const isDirty = (code: string) => {
    const saved = JSON.parse(savedSnapshot)
    const savedRows = JSON.stringify(saved.rows?.[code] || emptyRows())
    const savedNote = saved.notes?.[code] || ''
    return JSON.stringify(rowsFor(code)) !== savedRows || (notes[code] || '') !== savedNote
  }

  const metaFor = (code: string, rowIdx: number): RowMeta =>
    meta[code]?.[rowIdx] ?? { lock: 'pp', totalTyped: rowsFor(code)[rowIdx].total > 0 }

  const setCell = (code: string, rowIdx: number, field: Field, raw: string) => {
    const digits = raw.replace(/[^\d]/g, '')
    const value = digits === '' ? 0 : Math.min(99999, parseInt(digits, 10))
    const m = { ...metaFor(code, rowIdx) }
    const r = { ...rowsFor(code)[rowIdx], [field]: value }

    if (field === 'total') {
      m.totalTyped = value > 0
      // Keep the side typed last; refill the other from the new total.
      if (value > 0 && (r.pp > 0 || r.kp > 0)) {
        if (m.lock === 'pp') r.kp = Math.max(0, value - r.pp)
        else r.pp = Math.max(0, value - r.kp)
      }
    } else if (field === 'pp' || field === 'kp') {
      m.lock = field
      const other = field === 'pp' ? 'kp' : 'pp'
      if (m.totalTyped && r.total > 0) r[other] = Math.max(0, r.total - value)
      else r.total = r.pp + r.kp
    }

    setRows((prev) => {
      const next = [...(prev[code] || emptyRows())]
      next[rowIdx] = r
      return { ...prev, [code]: next }
    })
    setMeta((prev) => {
      const list = [...(prev[code] || GRADES.map((_, i) => metaFor(code, i)))]
      list[rowIdx] = m
      return { ...prev, [code]: list }
    })
    setStatus(null)
  }

  const errorsFor = (code: string) =>
    rowsFor(code).flatMap((r) => [
      ...(r.female > r.total ? [`និទ្ទេស ${r.grade}: ស្រី (${r.female}) មិនអាចលើសចំនួន (${r.total}) បានឡើយ`] : []),
      ...(r.pp > r.total ? [`និទ្ទេស ${r.grade}: ភ្នំពេញ (${r.pp}) មិនអាចលើសចំនួន (${r.total}) បានឡើយ`] : []),
      ...(r.kp > r.total ? [`និទ្ទេស ${r.grade}: ខេត្ត (${r.kp}) មិនអាចលើសចំនួន (${r.total}) បានឡើយ`] : []),
      ...(splitMismatch(r) && r.pp <= r.total && r.kp <= r.total
        ? [`និទ្ទេស ${r.grade}: ភ្នំពេញ (${r.pp}) + ខេត្ត (${r.kp}) ត្រូវតែស្មើចំនួន (${r.total})`]
        : []),
    ])

  const targets = isBulkMode ? categories.map((c) => c.code) : [selectedCode]
  const dirtyTargets = targets.filter(isDirty)
  const barTotals = useMemo(
    () => sumRows(targets.flatMap((code) => rowsFor(code))),
    [rows, isBulkMode, selectedCode, categories]
  )

  const handleSave = async () => {
    const invalid = dirtyTargets.find((code) => errorsFor(code).length > 0)
    if (invalid) {
      setStatus({ type: 'error', text: errorsFor(invalid)[0] })
      return
    }
    setSaving(true)
    setStatus(null)
    try {
      const creates = []
      for (const code of dirtyTargets) {
        const list = rowsFor(code)
        const grades = list
          .filter((r) => r.total > 0 || r.female > 0 || r.pp > 0 || r.kp > 0)
          .map((r) => ({ grade: r.grade, total: r.total, female: r.female, pp: r.pp, kp: r.kp }))
        const note = notes[code] || null

        if (existingIds[code]) {
          // Report already exists for this day → edit it instead of a duplicate create.
          await api.updateReport(existingIds[code], { grades, note })
        } else {
          const cat = categories.find((c) => c.code === code)
          const sums = sumRows(list)
          creates.push({
            report_date: reportDate,
            category_id: cat?.id || code,
            category_code: code,
            ...sums,
            note,
            grades,
          })
        }
      }
      if (creates.length > 1) await api.bulkCreateReports(creates)
      else if (creates.length === 1) await api.createReport(creates[0])

      confetti({ particleCount: 60, spread: 60, origin: { y: 0.8 } })
      await loadDay(reportDate) // refresh ids + saved snapshot (also clears status)
      setStatus({ type: 'success', text: `បានរក្សាទុកទិន្នន័យថ្ងៃ ${reportDate} រួចរាល់ — ទិន្នន័យកើនសន្សំត្រូវបានធ្វើបច្ចុប្បន្នភាព។` })
    } catch (err: any) {
      setStatus({ type: 'error', text: err.message || 'មានបញ្ហាក្នុងការរក្សាទុកទិន្នន័យ' })
    } finally {
      setSaving(false)
    }
  }

  // Spreadsheet-style keyboard movement between cells.
  const focusCell = (code: string, row: number, col: number) => {
    const el = document.querySelector<HTMLInputElement>(`[data-cell="${code}-${row}-${col}"]`)
    if (el) el.focus()
  }

  const onCellKeyDown = (e: React.KeyboardEvent<HTMLInputElement>, code: string, row: number, col: number) => {
    const last = GRADES.length - 1
    if (e.key === 'Enter' || e.key === 'ArrowDown') {
      e.preventDefault()
      if (row < last) focusCell(code, row + 1, col)
      else if (col < COLUMNS.length - 1) focusCell(code, 0, col + 1)
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      if (row > 0) focusCell(code, row - 1, col)
    } else if (e.key === 'ArrowRight' && e.currentTarget.selectionStart === e.currentTarget.value.length) {
      if (col < COLUMNS.length - 1) { e.preventDefault(); focusCell(code, row, col + 1) }
    } else if (e.key === 'ArrowLeft' && e.currentTarget.selectionStart === 0) {
      if (col > 0) { e.preventDefault(); focusCell(code, row, col - 1) }
    }
  }

  const renderGrid = (code: string) => {
    const cat = categories.find((c) => c.code === code)
    const list = rowsFor(code)
    const sums = sumRows(list)
    const errs = errorsFor(code)

    return (
      <section key={code} className="glass-panel" style={{ overflow: 'hidden' }}>
        <div className="entry-card-head" style={{ padding: '18px 22px', display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: '12px', flexWrap: 'wrap' }}>
          <div>
            <h2 style={{ fontSize: '1.05rem' }}>
              {formatRoman(cat?.roman_numeral)} {cat?.title || code}
            </h2>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-dim)', marginTop: '2px' }}>
              បញ្ចូល ភ្នំពេញ ឬ ខេត្ត មុនក៏បាន — ប្រអប់ម្ខាងទៀតបំពេញដោយស្វ័យប្រវត្តិ (ភ្នំពេញ + ខេត្ត = ចំនួន)
            </p>
          </div>
          {existingIds[code] && !isDirty(code) && (
            <span className="badge badge-emerald"><CheckCircle2 size={12} /> បានរក្សាទុក</span>
          )}
          {isDirty(code) && <span className="badge badge-amber">មិនទាន់រក្សាទុក</span>}
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table className="entry-grid">
            <thead>
              <tr>
                <th style={{ textAlign: 'left' }}>និទ្ទេស</th>
                {COLUMNS.map((c) => (
                  <th key={c.field} title={c.hint}>{c.label}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {list.map((row, rIdx) => {
                const total = rowTotal(row)
                return (
                  <tr key={row.grade} className={total > 0 ? 'has-value' : ''}>
                    <th scope="row" className="entry-grade">
                      <span className="entry-grade-letter" data-grade={row.grade}>{row.grade}</span>
                      <span className="entry-grade-name">និទ្ទេស {row.grade}</span>
                    </th>
                    {COLUMNS.map((c, cIdx) => {
                      const value = row[c.field]
                      const invalid =
                        (c.field !== 'total' && value > total) ||
                        ((c.field === 'pp' || c.field === 'kp') && splitMismatch(row))
                      return (
                        <td key={c.field}>
                          <input
                            type="text"
                            inputMode="numeric"
                            autoComplete="off"
                            data-cell={`${code}-${rIdx}-${cIdx}`}
                            aria-label={`និទ្ទេស ${row.grade} — ${c.label}`}
                            aria-invalid={invalid || undefined}
                            className={`cell-input ${invalid ? 'invalid' : ''}`}
                            value={value === 0 ? '' : String(value)}
                            placeholder="–"
                            onFocus={(e) => e.currentTarget.select()}
                            onChange={(e) => setCell(code, rIdx, c.field, e.target.value)}
                            onKeyDown={(e) => onCellKeyDown(e, code, rIdx, cIdx)}
                            disabled={loading}
                          />
                        </td>
                      )
                    })}
                  </tr>
                )
              })}
            </tbody>
            <tfoot>
              <tr>
                <th scope="row" style={{ textAlign: 'left' }}>សរុប</th>
                <td>{sums.total}</td>
                <td>{sums.female}</td>
                <td>{sums.pp}</td>
                <td>{sums.kp}</td>
              </tr>
            </tfoot>
          </table>
        </div>

        {errs.length > 0 && (
          <div role="alert" style={{ margin: '0 22px 16px', padding: '10px 14px', background: 'var(--rose-soft)', border: '1px solid var(--rose-border)', borderRadius: 'var(--radius-md)', display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--rose-primary)', fontSize: '0.85rem' }}>
            <AlertCircle size={16} />
            <span>{errs[0]}</span>
          </div>
        )}

        {/* The note field was removed from entry; notes already on a report are still sent back unchanged on save. */}
        <div style={{ height: 16 }} />
      </section>
    )
  }

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div className="page-header">
        <div>
          <h1 className="page-title">បញ្ចូលទិន្នន័យចុះឈ្មោះប្រចាំថ្ងៃ</h1>
          <p className="page-subtitle">បញ្ចូលចំនួនសិស្សថ្មីថ្ងៃនេះ — ប្រព័ន្ធនឹងបូកសរុប និងគណនាកើនសន្សំដោយស្វ័យប្រវត្តិ</p>
        </div>
        <div className="page-actions">
          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
            កាលបរិច្ឆេទ
            <DatePicker ariaLabel="កាលបរិច្ឆេទ" value={reportDate} max={today()} onChange={setReportDate} />
          </label>
          <button
            onClick={() => setIsBulkMode(!isBulkMode)}
            className={`btn ${isBulkMode ? 'btn-outline-cyan' : 'btn-secondary'}`}
            aria-pressed={isBulkMode}
          >
            <Layers size={16} />
            បង្ហាញទាំង ៣ ប្រភេទ
          </button>
        </div>
      </div>

      {!isBulkMode && (
        <div className="tab-strip" role="tablist">
          {categories.map((cat) => {
            const count = sumRows(rowsFor(cat.code)).total
            const active = selectedCode === cat.code
            return (
              <button
                key={cat.code}
                role="tab"
                aria-selected={active}
                onClick={() => setSelectedCode(cat.code)}
                className={`tab ${active ? 'active' : ''}`}
                title={cat.title}
              >
                <span>{formatRoman(cat.roman_numeral)} {shortCategory(cat.title)}</span>
                <span className={`tab-count ${count > 0 ? 'filled' : ''}`}>{count}</span>
                {isDirty(cat.code) && <span className="tab-dirty" title="មិនទាន់រក្សាទុក" />}
              </button>
            )
          })}
        </div>
      )}

      {isBulkMode ? categories.map((cat) => renderGrid(cat.code)) : renderGrid(selectedCode)}

      <div className="entry-keyhint" style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.78rem', color: 'var(--text-dim)' }}>
        <Keyboard size={14} />
        ចុច Enter ឬ ↓ ដើម្បីទៅប្រអប់បន្ទាប់ · ← → ដើម្បីប្តូរជួរឈរ
      </div>

      {/* Save row — status on the left; totals sit right beside the save button. */}
      <div className="save-bar">
        <div className={status ? 'save-bar-status' : 'save-bar-status hide-phone'} style={{ flex: 1, minWidth: 0 }}>
          {status ? (
            <span role="status" style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.85rem', color: status.type === 'success' ? 'var(--emerald-primary)' : 'var(--rose-primary)' }}>
              {status.type === 'success' ? <CheckCircle2 size={16} /> : <AlertCircle size={16} />}
              {status.text}
            </span>
          ) : dirtyTargets.length > 0 ? (
            <span className="hide-phone" style={{ fontSize: '0.85rem', color: 'var(--amber-primary)' }}>មានការកែប្រែមិនទាន់រក្សាទុក</span>
          ) : null}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '18px', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px', flexWrap: 'wrap', fontSize: '0.875rem', color: 'var(--text-muted)' }}>
            <span>ស្រី <strong className="save-bar-num">{barTotals.female}</strong></span>
            <span>ភ្នំពេញ <strong className="save-bar-num">{barTotals.pp}</strong></span>
            <span>ខេត្ត <strong className="save-bar-num">{barTotals.kp}</strong></span>
            <span>សរុបថ្ងៃនេះ <strong className="save-bar-num save-bar-total">{barTotals.total}</strong> នាក់</span>
          </div>
          <button
            onClick={handleSave}
            disabled={saving || loading || dirtyTargets.length === 0}
            className="btn btn-primary"
            style={{ minWidth: '150px' }}
          >
            {saving ? <RefreshCw size={16} className="spin" /> : <Save size={16} />}
            {saving ? 'កំពុងរក្សាទុក...' : 'រក្សាទុក'}
          </button>
        </div>
      </div>
    </div>
  )
}
