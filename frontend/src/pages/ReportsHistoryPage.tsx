import React, { useEffect, useState } from 'react'
import {
  Search, RefreshCw, Pencil, Trash2, AlertTriangle, FilePlus, Send, ChevronLeft, ChevronRight, X, Save, History,
} from 'lucide-react'
import { api } from '../lib/api'
import { daysAgo, formatCategory, khDate, localISODate, monthStart } from '../lib/format'
import { Category, DailyReport, GradeEntry, PaginatedResponse } from '../types'
import { useAuth } from '../context/AuthContext'

interface ReportsHistoryPageProps {
  onNavigate: (tab: string, dateParam?: string) => void
}

type Preset = 'all' | '7d' | '30d' | 'month' | 'custom'
type Letter = GradeEntry['grade']
const LETTERS: Letter[] = ['A', 'B', 'C', 'D', 'E']

const todayOf = (r: DailyReport) => ({
  total: r.today?.total ?? r.today_total ?? 0,
  female: r.today?.female ?? r.today_female ?? 0,
  pp: r.today?.pp ?? r.today_pp ?? 0,
  kp: r.today?.kp ?? r.today_kp ?? 0,
})

/** Grade counts as coloured pills: "● A 2". Letter + number, never colour alone. */
const GradePills: React.FC<{ grades: GradeEntry[] }> = ({ grades }) => {
  const shown = [...grades].filter((g) => g.total > 0).sort((a, b) => a.grade.localeCompare(b.grade))
  if (shown.length === 0) return <span style={{ color: 'var(--text-dim)' }}>–</span>
  return (
    <span className="grade-pills">
      {shown.map((g) => (
        <span key={g.grade} className="grade-pill">
          <span className="grade-pill-dot" style={{ background: `var(--grade-${g.grade})` }} />
          {g.grade} <strong>{g.total}</strong>
        </span>
      ))}
    </span>
  )
}

export const ReportsHistoryPage: React.FC<ReportsHistoryPageProps> = ({ onNavigate }) => {
  const { user } = useAuth()
  const canEdit = ['superadmin', 'admin', 'manager', 'staff'].includes(user?.role || '')
  const canDelete = ['superadmin', 'admin'].includes(user?.role || '')

  const [page, setPage] = useState(1)
  const [size, setSize] = useState(15)
  const [preset, setPreset] = useState<Preset>('all')
  const [startDate, setStartDate] = useState('')
  const [endDate, setEndDate] = useState('')
  const [categoryCode, setCategoryCode] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')

  const [categories, setCategories] = useState<Category[]>([])
  const [data, setData] = useState<PaginatedResponse<DailyReport> | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [detail, setDetail] = useState<DailyReport | null>(null)
  const [editing, setEditing] = useState<DailyReport | null>(null)
  const [editRows, setEditRows] = useState<Array<{ grade: Letter; total: number; female: number; pp: number }>>([])
  const [editNote, setEditNote] = useState('')
  const [editSaving, setEditSaving] = useState(false)
  const [editError, setEditError] = useState<string | null>(null)
  const [toDelete, setToDelete] = useState<DailyReport | null>(null)
  const [deleting, setDeleting] = useState(false)
  const [notice, setNotice] = useState<string | null>(null)

  useEffect(() => {
    api.getCategories().then((r) => setCategories(r.items)).catch(() => undefined)
  }, [])

  useEffect(() => {
    const t = setTimeout(() => { setSearch(searchInput.trim()); setPage(1) }, 350)
    return () => clearTimeout(t)
  }, [searchInput])

  const fetchReports = async () => {
    setLoading(true)
    setError(null)
    try {
      setData(await api.getReportsHistory({
        page, size,
        start: startDate || undefined,
        end: endDate || undefined,
        category_code: categoryCode || undefined,
        q: search || undefined,
      }))
    } catch (err: any) {
      setError(err.message || 'បរាជ័យក្នុងការទាញទិន្នន័យ')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchReports()
  }, [page, size, categoryCode, startDate, endDate, search])

  // Esc closes whichever dialog is open.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== 'Escape') return
      setDetail(null); setEditing(null); setToDelete(null)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  const applyPreset = (p: Preset) => {
    setPreset(p)
    setPage(1)
    if (p === 'all') { setStartDate(''); setEndDate('') }
    if (p === '7d') { setStartDate(daysAgo(6)); setEndDate(localISODate()) }
    if (p === '30d') { setStartDate(daysAgo(29)); setEndDate(localISODate()) }
    if (p === 'month') { setStartDate(monthStart()); setEndDate(localISODate()) }
  }

  const hasFilters = !!(startDate || endDate || categoryCode || searchInput)
  const clearFilters = () => { applyPreset('all'); setCategoryCode(''); setSearchInput('') }

  const categoryName = (r: DailyReport) => {
    const c = categories.find((x) => x.code === r.category_code || x.id === r.category_id)
    return formatCategory(r.roman_numeral || c?.roman_numeral, r.category_title || c?.title || r.category_code)
  }

  // ── Edit: same rule as Daily Entry — total is always ភ្នំពេញ + ខេត្ត.
  const openEdit = (r: DailyReport) => {
    setDetail(null)
    setEditing(r)
    setEditNote(r.note || '')
    setEditError(null)
    setEditRows(LETTERS.map((g) => {
      const e = r.grades?.find((x) => x.grade === g)
      return { grade: g, total: e?.total ?? 0, female: e?.female ?? 0, pp: e?.pp ?? 0 }
    }))
  }

  const setEditCell = (idx: number, field: 'total' | 'female' | 'pp', raw: string) => {
    const digits = raw.replace(/[^\d]/g, '')
    const value = digits === '' ? 0 : Math.min(99999, parseInt(digits, 10))
    setEditRows((rows) => rows.map((r, i) => (i === idx ? { ...r, [field]: value } : r)))
  }

  // Same model as Daily Entry: type ចំនួន, ស្រី, ភ្នំពេញ; KP = ចំនួន − ភ្នំពេញ.
  const editKp = (r: { total: number; pp: number }) => Math.max(0, r.total - r.pp)
  const editInvalid = editRows.find((r) => r.female > r.total || r.pp > r.total)

  const saveEdit = async () => {
    if (!editing || editInvalid) return
    setEditSaving(true)
    setEditError(null)
    try {
      await api.updateReport(editing.id, {
        note: editNote || null,
        grades: editRows
          .filter((r) => r.total > 0 || r.female > 0 || r.pp > 0)
          .map((r) => ({ grade: r.grade, total: r.total, female: r.female, pp: r.pp, kp: editKp(r) })),
      })
      setEditing(null)
      setNotice(`បានកែប្រែរបាយការណ៍ ${khDate(editing.report_date)} រួចរាល់`)
      fetchReports()
    } catch (err: any) {
      setEditError(err.message || 'បរាជ័យក្នុងការកែប្រែ')
    } finally {
      setEditSaving(false)
    }
  }

  const confirmDelete = async () => {
    if (!toDelete) return
    setDeleting(true)
    try {
      await api.deleteReport(toDelete.id)
      setNotice(`បានលុបរបាយការណ៍ ${khDate(toDelete.report_date)}`)
      setToDelete(null)
      fetchReports()
    } catch (err: any) {
      setNotice(`បរាជ័យក្នុងការលុប: ${err.message}`)
      setToDelete(null)
    } finally {
      setDeleting(false)
    }
  }

  const editTotals = editRows.reduce((a, r) => ({ total: a.total + r.total, female: a.female + r.female, pp: a.pp + r.pp, kp: a.kp + editKp(r) }), { total: 0, female: 0, pp: 0, kp: 0 })

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div className="page-header">
        <div>
          <h1 className="page-title">ប្រវត្តិរបាយការណ៍</h1>
          <p className="page-subtitle">របាយការណ៍ប្រចាំថ្ងៃទាំងអស់ — ចុចលើជួរដើម្បីមើលលម្អិត</p>
        </div>
        <div className="page-actions">
          <button onClick={fetchReports} className="btn btn-ghost" aria-label="ផ្ទុកឡើងវិញ" title="ផ្ទុកឡើងវិញ">
            <RefreshCw size={16} className={loading ? 'spin' : ''} />
          </button>
          <button onClick={() => onNavigate('daily-entry')} className="btn btn-primary">
            <FilePlus size={16} /> បញ្ចូលទិន្នន័យថ្មី
          </button>
        </div>
      </div>

      {/* Filters — one plain row */}
      <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', alignItems: 'center' }}>
        <div className="preset-group" role="group" aria-label="ចន្លោះពេល">
          {([['all', 'ទាំងអស់'], ['7d', '៧ ថ្ងៃ'], ['30d', '៣០ ថ្ងៃ'], ['month', 'ខែនេះ']] as Array<[Preset, string]>).map(([p, label]) => (
            <button key={p} className={preset === p ? 'active' : ''} aria-pressed={preset === p} onClick={() => applyPreset(p)}>{label}</button>
          ))}
        </div>
        <input type="date" className="input-field" style={{ width: 'auto' }} value={startDate} max={endDate || undefined}
          aria-label="ចាប់ពីថ្ងៃ" onChange={(e) => { setStartDate(e.target.value); setPreset('custom'); setPage(1) }} />
        <span style={{ color: 'var(--text-dim)' }}>–</span>
        <input type="date" className="input-field" style={{ width: 'auto' }} value={endDate} min={startDate || undefined}
          aria-label="ដល់ថ្ងៃ" onChange={(e) => { setEndDate(e.target.value); setPreset('custom'); setPage(1) }} />
        <select className="input-field" style={{ width: 'auto', maxWidth: '280px' }} value={categoryCode}
          aria-label="ផ្នែក" onChange={(e) => { setCategoryCode(e.target.value); setPage(1) }}>
          <option value="">គ្រប់ផ្នែក</option>
          {categories.map((c) => <option key={c.id} value={c.code}>{formatCategory(c.roman_numeral, c.title)}</option>)}
        </select>
        <div style={{ position: 'relative', flex: '1 1 200px', maxWidth: '300px' }}>
          <Search size={15} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-dim)' }} />
          <input type="search" className="input-field" placeholder="ស្វែងរកកំណត់សម្គាល់…" value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)} style={{ paddingLeft: '36px' }} aria-label="ស្វែងរក" />
        </div>
        {hasFilters && <button onClick={clearFilters} className="link-button">សម្អាតតម្រង</button>}
      </div>

      {notice && (
        <div role="status" className="notice notice-emerald">
          <span style={{ flex: 1 }}>{notice}</span>
          <button className="btn btn-ghost" style={{ padding: 2 }} onClick={() => setNotice(null)} aria-label="បិទ"><X size={14} /></button>
        </div>
      )}

      <section className="glass-panel" style={{ overflow: 'hidden' }}>
        {error ? (
          <div className="chart-empty" style={{ color: 'var(--rose-primary)' }}>{error}</div>
        ) : loading && !data ? (
          <div className="chart-empty"><RefreshCw size={18} className="spin" style={{ marginRight: 8 }} /> កំពុងផ្ទុក…</div>
        ) : !data || data.items.length === 0 ? (
          <div className="chart-empty" style={{ flexDirection: 'column', gap: '12px' }}>
            <History size={32} />
            <span>ពុំមានរបាយការណ៍ត្រូវនឹងតម្រងនេះទេ</span>
            <button onClick={() => onNavigate('daily-entry')} className="btn btn-primary btn-sm"><FilePlus size={15} /> បញ្ចូលទិន្នន័យ</button>
          </div>
        ) : (
          <div style={{ overflowX: 'auto', opacity: loading ? 0.6 : 1 }}>
            <table className="audit-table history-table">
              <thead>
                <tr>
                  <th style={{ width: '120px' }}>កាលបរិច្ឆេទ</th>
                  <th>ផ្នែក</th>
                  <th style={{ textAlign: 'right', width: '150px' }}>សិស្សថ្មី</th>
                  <th style={{ textAlign: 'right', width: '130px' }}>សរុបទាំងអស់</th>
                  <th style={{ width: '240px' }}>និទ្ទេស</th>
                  <th style={{ width: '90px' }} aria-label="សកម្មភាព" />
                </tr>
              </thead>
              <tbody>
                {data.items.map((r) => {
                  const t = todayOf(r)
                  const inconsistent = t.total !== t.pp + t.kp || t.female > t.total
                  return (
                    <tr key={r.id} tabIndex={0} onClick={() => setDetail(r)}
                      onKeyDown={(e) => e.key === 'Enter' && setDetail(r)}>
                      <td style={{ fontWeight: 600, whiteSpace: 'nowrap' }}>{khDate(r.report_date)}</td>
                      <td>
                        <div style={{ fontWeight: 500 }}>{categoryName(r)}</div>
                        {r.note && <div className="audit-entity" style={{ maxWidth: '360px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{r.note}</div>}
                        {inconsistent && (
                          <span className="badge badge-rose" style={{ marginTop: 4 }} title="សរុប ≠ ភ្នំពេញ + ខេត្ត">
                            <AlertTriangle size={11} /> តួលេខមិនស៊ីគ្នា
                          </span>
                        )}
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        <div style={{ fontWeight: 700, fontSize: '1rem', color: 'var(--accent-text)' }}>+{t.total}</div>
                        <div className="audit-entity">ស្រី {t.female} · ភ្នំពេញ {t.pp} · ខេត្ត {t.kp}</div>
                      </td>
                      <td style={{ textAlign: 'right', fontWeight: 600 }}>{(r.cumulative?.total ?? 0).toLocaleString()}</td>
                      <td><GradePills grades={r.grades || []} /></td>
                      <td onClick={(e) => e.stopPropagation()} style={{ textAlign: 'right', whiteSpace: 'nowrap' }}>
                        {canEdit && (
                          <button onClick={() => openEdit(r)} className="btn btn-ghost" aria-label="កែប្រែ" title="កែប្រែ"><Pencil size={15} /></button>
                        )}
                        {canDelete && (
                          <button onClick={() => setToDelete(r)} className="btn btn-ghost" aria-label="លុប" title="លុប" style={{ color: 'var(--rose-primary)' }}><Trash2 size={15} /></button>
                        )}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}

        {data && data.items.length > 0 && (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 18px', borderTop: '1px solid var(--border-subtle)', flexWrap: 'wrap', gap: '10px' }}>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              ទំព័រ {data.meta.page} នៃ {data.meta.total_pages || 1} · សរុប {data.meta.total} របាយការណ៍
            </span>
            <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
              <select className="input-field" style={{ width: 'auto', padding: '5px 8px', fontSize: '0.8rem' }} value={size}
                onChange={(e) => { setSize(Number(e.target.value)); setPage(1) }} aria-label="ចំនួនក្នុងមួយទំព័រ">
                {[15, 30, 50].map((n) => <option key={n} value={n}>{n} / ទំព័រ</option>)}
              </select>
              <button disabled={!data.meta.has_prev} onClick={() => setPage((p) => Math.max(1, p - 1))} className="btn btn-secondary btn-sm"><ChevronLeft size={15} /> ថយក្រោយ</button>
              <button disabled={!data.meta.has_next} onClick={() => setPage((p) => p + 1)} className="btn btn-secondary btn-sm">ទៅមុខ <ChevronRight size={15} /></button>
            </div>
          </div>
        )}
      </section>

      {/* ── Detail ── */}
      {detail && (() => {
        const t = todayOf(detail)
        const c = detail.cumulative || { total: 0, female: 0, pp: 0, kp: 0 }
        return (
          <div className="modal-backdrop" onClick={() => setDetail(null)}>
            <div className="glass-panel modal-card" role="dialog" aria-modal="true" aria-labelledby="rd-title" onClick={(e) => e.stopPropagation()}>
              <div className="modal-head">
                <div>
                  <div className="audit-entity">{khDate(detail.report_date)}</div>
                  <h2 id="rd-title" style={{ fontSize: '1.1rem' }}>{categoryName(detail)}</h2>
                </div>
                <button onClick={() => setDetail(null)} className="btn btn-ghost" aria-label="បិទ"><X size={18} /></button>
              </div>

              <div className="detail-stats">
                {([['សិស្សថ្មី', `+${t.total}`, c.total], ['ស្រី', t.female, c.female], ['ភ្នំពេញ', t.pp, c.pp], ['ខេត្ត', t.kp, c.kp]] as Array<[string, string | number, number]>).map(([label, v, cum]) => (
                  <div key={label}>
                    <div className="stat-label">{label}</div>
                    <div className="stat-value" style={{ fontSize: '1.4rem' }}>{v}</div>
                    <div className="stat-note">កើនសន្សំ {cum}</div>
                  </div>
                ))}
              </div>

              <h3 style={{ fontSize: '0.875rem', margin: '18px 0 8px' }}>តាមនិទ្ទេស</h3>
              {(detail.grades || []).length === 0 ? (
                <div className="audit-entity">គ្មានការបែងចែកតាមនិទ្ទេស</div>
              ) : (
                <div style={{ border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-md)', overflow: 'auto' }}>
                  <table className="result-table">
                    <thead><tr><th style={{ textAlign: 'left' }}>និទ្ទេស</th><th>សរុប</th><th>ស្រី</th><th>ភ្នំពេញ</th><th>ខេត្ត</th></tr></thead>
                    <tbody>
                      {[...detail.grades].sort((a, b) => a.grade.localeCompare(b.grade)).map((g) => (
                        <tr key={g.grade}>
                          <td style={{ textAlign: 'left' }}>
                            <span className="grade-pill-dot" style={{ background: `var(--grade-${g.grade})`, marginRight: 8 }} />និទ្ទេស {g.grade}
                          </td>
                          <td style={{ fontWeight: 700 }}>{g.total}</td><td>{g.female}</td><td>{g.pp}</td><td>{g.kp}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {detail.note && (
                <p style={{ marginTop: '14px', fontSize: '0.875rem' }}><span style={{ color: 'var(--text-dim)' }}>កំណត់សម្គាល់: </span>{detail.note}</p>
              )}

              <div className="modal-foot">
                <span className="audit-entity">
                  បញ្ចូលដោយ {detail.created_by_username || 'ប្រព័ន្ធ'}
                </span>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button onClick={() => { setDetail(null); onNavigate('telegram', detail.report_date) }} className="btn btn-secondary btn-sm"><Send size={14} /> សារ Telegram</button>
                  {canEdit && <button onClick={() => openEdit(detail)} className="btn btn-primary btn-sm"><Pencil size={14} /> កែប្រែ</button>}
                </div>
              </div>
            </div>
          </div>
        )
      })()}

      {/* ── Edit (same grid rules as Daily Entry) ── */}
      {editing && (
        <div className="modal-backdrop" onClick={() => setEditing(null)}>
          <div className="glass-panel modal-card" role="dialog" aria-modal="true" aria-labelledby="re-title" onClick={(e) => e.stopPropagation()}>
            <div className="modal-head">
              <div>
                <div className="audit-entity">{khDate(editing.report_date)}</div>
                <h2 id="re-title" style={{ fontSize: '1.1rem' }}>កែប្រែ · {categoryName(editing)}</h2>
              </div>
              <button onClick={() => setEditing(null)} className="btn btn-ghost" aria-label="បិទ"><X size={18} /></button>
            </div>

            <div style={{ border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-md)', overflow: 'auto' }}>
              <table className="entry-grid" style={{ width: '100%' }}>
                <thead>
                  <tr><th style={{ textAlign: 'left' }}>និទ្ទេស</th><th>ចំនួន</th><th>ស្រី</th><th>ភ្នំពេញ (PP)</th><th className="entry-total-col">ខេត្ត (KP)</th></tr>
                </thead>
                <tbody>
                  {editRows.map((r, i) => (
                    <tr key={r.grade} className={r.total > 0 ? 'has-value' : ''}>
                      <th scope="row" className="entry-grade" style={{ width: 'auto' }}>
                        <span className="entry-grade-letter" data-grade={r.grade}>{r.grade}</span>និទ្ទេស {r.grade}
                      </th>
                      {(['total', 'female', 'pp'] as const).map((f) => (
                        <td key={f}>
                          <input type="text" inputMode="numeric"
                            className={`cell-input ${f !== 'total' && r[f] > r.total ? 'invalid' : ''}`}
                            style={{ height: 36 }} value={r[f] === 0 ? '' : String(r[f])} placeholder="–"
                            aria-label={`និទ្ទេស ${r.grade} ${f === 'total' ? 'ចំនួន' : f === 'female' ? 'ស្រី' : 'ភ្នំពេញ'}`}
                            onFocus={(e) => e.currentTarget.select()} onChange={(e) => setEditCell(i, f, e.target.value)} />
                        </td>
                      ))}
                      <td className="entry-total-col">{r.total > 0 && r.pp <= r.total ? editKp(r) : '–'}</td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr><th scope="row" style={{ textAlign: 'left' }}>សរុប</th><td>{editTotals.total}</td><td>{editTotals.female}</td><td>{editTotals.pp}</td><td className="entry-total-col">{editTotals.kp}</td></tr>
                </tfoot>
              </table>
            </div>

            <label className="input-group" style={{ marginTop: '14px' }}>
              <span className="input-label">កំណត់សម្គាល់ / មូលហេតុនៃការកែប្រែ</span>
              <input className="input-field" value={editNote} onChange={(e) => setEditNote(e.target.value)} placeholder="ឧ. កែតួលេខខុស…" />
            </label>

            {(editInvalid || editError) && (
              <div role="alert" className="notice notice-rose" style={{ marginTop: '12px' }}>
                <AlertTriangle size={15} />
                {editInvalid
                  ? `និទ្ទេស ${editInvalid.grade}: ${editInvalid.female > editInvalid.total ? 'ស្រី' : 'ភ្នំពេញ'}មិនអាចលើសចំនួន`
                  : editError}
              </div>
            )}

            <div className="modal-foot">
              <span className="audit-entity">KP = ចំនួន − ភ្នំពេញ · កើនសន្សំនឹងគណនាឡើងវិញ</span>
              <div style={{ display: 'flex', gap: '8px' }}>
                <button onClick={() => setEditing(null)} className="btn btn-secondary">បោះបង់</button>
                <button onClick={saveEdit} disabled={editSaving || !!editInvalid} className="btn btn-primary">
                  {editSaving ? <RefreshCw size={15} className="spin" /> : <Save size={15} />} រក្សាទុក
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ── Delete confirm ── */}
      {toDelete && (
        <div className="modal-backdrop" onClick={() => !deleting && setToDelete(null)}>
          <div className="glass-panel modal-card" style={{ maxWidth: '420px' }} role="alertdialog" aria-modal="true" aria-labelledby="rdel-title" onClick={(e) => e.stopPropagation()}>
            <h2 id="rdel-title" style={{ fontSize: '1.05rem' }}>លុបរបាយការណ៍នេះ?</h2>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginTop: '8px', lineHeight: 1.6 }}>
              {khDate(toDelete.report_date)} · {categoryName(toDelete)} (+{todayOf(toDelete).total} នាក់)។
              ចំនួនកើនសន្សំនៃថ្ងៃបន្ទាប់ៗនឹងត្រូវគណនាឡើងវិញ។ សកម្មភាពនេះមិនអាចត្រឡប់វិញបានទេ។
            </p>
            <div className="modal-foot" style={{ justifyContent: 'flex-end' }}>
              <button onClick={() => setToDelete(null)} className="btn btn-secondary" disabled={deleting}>បោះបង់</button>
              <button onClick={confirmDelete} className="btn btn-danger" disabled={deleting}>
                {deleting ? <RefreshCw size={15} className="spin" /> : <Trash2 size={15} />} លុប
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
