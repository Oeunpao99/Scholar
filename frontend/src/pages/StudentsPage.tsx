import React, { useEffect, useRef, useState } from 'react'
import {
  Search, RefreshCw, Pencil, Trash2, UserPlus, ChevronLeft, ChevronRight, X, Save, AlertTriangle, GraduationCap,
} from 'lucide-react'
import { api } from '../lib/api'
import { PaginatedResponse, Student, StudentInput } from '../types'
import { useAuth } from '../context/AuthContext'

const GRADES = ['A', 'B', 'C', 'D', 'E'] as const
const GENDER_LABEL: Record<string, string> = { M: 'ប្រុស', F: 'ស្រី' }
const STREAM_LABEL: Record<string, string> = { science: 'វិទ្យាសាស្ត្រ', social_science: 'វិទ្យាសាស្ត្រសង្គម' }

type FormState = {
  full_name: string
  gender: '' | 'M' | 'F'
  grade: string
  score_rank: string
  high_school: string
  stream: string
  university: string
  major: string
  phone: string
  note: string
}

const EMPTY_FORM: FormState = {
  full_name: '', gender: '', grade: '', score_rank: '', high_school: '',
  stream: '', university: '', major: '', phone: '', note: '',
}

const toForm = (s: Student): FormState => ({
  full_name: s.full_name,
  gender: s.gender,
  grade: s.grade || '',
  score_rank: s.score_rank ? String(s.score_rank) : '',
  high_school: s.high_school || '',
  stream: s.stream || '',
  university: s.university || '',
  major: s.major || '',
  phone: s.phone || '',
  note: s.note || '',
})

// Blank inputs go as null so edits can clear a field; the API stores "" as NULL anyway.
const toPayload = (f: FormState): StudentInput => ({
  full_name: f.full_name.trim(),
  gender: f.gender as 'M' | 'F',
  grade: (f.grade || null) as StudentInput['grade'],
  score_rank: f.score_rank ? Number(f.score_rank) : null,
  high_school: f.high_school || null,
  stream: (f.stream || null) as StudentInput['stream'],
  university: f.university || null,
  major: f.major || null,
  phone: f.phone || null,
  note: f.note || null,
})

const dash = (v?: string | number | null) => (v === null || v === undefined || v === '' ? '–' : v)

export const StudentsPage: React.FC = () => {
  const { user } = useAuth()
  const canEdit = ['superadmin', 'admin', 'manager', 'staff'].includes(user?.role || '')
  const canDelete = ['superadmin', 'admin', 'manager'].includes(user?.role || '')

  const [year, setYear] = useState<number | null>(null)
  const [currentYear, setCurrentYear] = useState<number | null>(null)
  const [page, setPage] = useState(1)
  const [size, setSize] = useState(50)
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [gender, setGender] = useState('')
  const [grade, setGrade] = useState('')
  const [stream, setStream] = useState('')

  const [data, setData] = useState<PaginatedResponse<Student> | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  // null = closed, 'new' = adding, Student = editing
  const [formFor, setFormFor] = useState<Student | 'new' | null>(null)
  const [form, setForm] = useState<FormState>(EMPTY_FORM)
  const [saving, setSaving] = useState(false)
  const [formError, setFormError] = useState<string | null>(null)
  const [toDelete, setToDelete] = useState<Student | null>(null)
  const [deleting, setDeleting] = useState(false)
  const nameRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    api.getCurrentYear()
      .then((r) => { setCurrentYear(r.current_year); setYear(r.current_year) })
      .catch(() => { const y = new Date().getFullYear(); setCurrentYear(y); setYear(y) })
  }, [])

  useEffect(() => {
    const t = setTimeout(() => { setSearch(searchInput.trim()); setPage(1) }, 350)
    return () => clearTimeout(t)
  }, [searchInput])

  const fetchStudents = async () => {
    if (year === null) return
    setLoading(true)
    setError(null)
    try {
      setData(await api.getStudents({
        page, size, academic_year: year,
        q: search || undefined, gender: gender || undefined, grade: grade || undefined, stream: stream || undefined,
      }))
    } catch (err: any) {
      setError(err.message || 'បរាជ័យក្នុងការទាញបញ្ជីសិស្ស')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchStudents()
  }, [year, page, size, search, gender, grade, stream])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== 'Escape') return
      setFormFor(null); setToDelete(null)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  const openAdd = () => { setForm(EMPTY_FORM); setFormError(null); setFormFor('new') }
  const openEdit = (s: Student) => { setForm(toForm(s)); setFormError(null); setFormFor(s) }
  const set = (key: keyof FormState) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
    setForm((f) => ({ ...f, [key]: e.target.value }))

  const save = async (addAnother: boolean) => {
    if (!form.full_name.trim()) { setFormError('សូមបញ្ចូលគោត្តនាម-នាម'); return }
    if (!form.gender) { setFormError('សូមជ្រើសរើសភេទ'); return }
    if (form.score_rank && !(Number(form.score_rank) > 0)) { setFormError('លំដាប់ពិន្ទុត្រូវតែជាលេខធំជាង 0'); return }
    setSaving(true)
    setFormError(null)
    try {
      if (formFor === 'new') {
        const created = await api.createStudent({ ...toPayload(form), academic_year: year ?? undefined })
        setNotice(`បានបន្ថែម ${created.full_name}`)
      } else if (formFor) {
        const updated = await api.updateStudent(formFor.id, toPayload(form))
        setNotice(`បានកែប្រែ ${updated.full_name}`)
      }
      if (addAnother) {
        // Keep school/stream/university: consecutive entries usually share them.
        setForm((f) => ({ ...EMPTY_FORM, high_school: f.high_school, stream: f.stream, university: f.university }))
        nameRef.current?.focus()
      } else {
        setFormFor(null)
      }
      fetchStudents()
    } catch (err: any) {
      setFormError(err.message || 'បរាជ័យក្នុងការរក្សាទុក')
    } finally {
      setSaving(false)
    }
  }

  const confirmDelete = async () => {
    if (!toDelete) return
    setDeleting(true)
    try {
      await api.deleteStudent(toDelete.id)
      setNotice(`បានលុប ${toDelete.full_name}`)
      setToDelete(null)
      fetchStudents()
    } catch (err: any) {
      setError(err.message || 'បរាជ័យក្នុងការលុប')
    } finally {
      setDeleting(false)
    }
  }

  const hasFilters = !!(searchInput || gender || grade || stream)
  const clearFilters = () => { setSearchInput(''); setGender(''); setGrade(''); setStream(''); setPage(1) }
  const yearOptions = currentYear ? [currentYear + 1, currentYear, currentYear - 1, currentYear - 2] : []
  const rowOffset = data ? (data.meta.page - 1) * data.meta.size : 0

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div className="page-header">
        <div>
          <h1 className="page-title">បញ្ជីឈ្មោះសិស្ស</h1>
          <p className="page-subtitle">បញ្ជីសិស្សដែលបានដាក់ពាក្យ ព្រមទាំងសាកលវិទ្យាល័យ និងជំនាញដែលស្នើសុំ</p>
        </div>
        <div className="page-actions">
          <button onClick={fetchStudents} className="btn btn-ghost" aria-label="ផ្ទុកឡើងវិញ" title="ផ្ទុកឡើងវិញ">
            <RefreshCw size={16} className={loading ? 'spin' : ''} />
          </button>
          {canEdit && (
            <button onClick={openAdd} className="btn btn-primary">
              <UserPlus size={16} /> បន្ថែមសិស្ស
            </button>
          )}
        </div>
      </div>

      {/* Filters */}
      <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', alignItems: 'center' }}>
        <select className="input-field" style={{ width: 'auto' }} value={year ?? ''} aria-label="ឆ្នាំសិក្សា"
          onChange={(e) => { setYear(Number(e.target.value)); setPage(1) }}>
          {yearOptions.map((y) => <option key={y} value={y}>ឆ្នាំ {y}</option>)}
        </select>
        <div style={{ position: 'relative', flex: '1 1 220px', maxWidth: '320px' }}>
          <Search size={15} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-dim)' }} />
          <input type="search" className="input-field" placeholder="ស្វែងរកឈ្មោះ លេខទូរស័ព្ទ សាលា…" value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)} style={{ paddingLeft: '36px' }} aria-label="ស្វែងរក" />
        </div>
        <select className="input-field" style={{ width: 'auto' }} value={gender} aria-label="ភេទ"
          onChange={(e) => { setGender(e.target.value); setPage(1) }}>
          <option value="">គ្រប់ភេទ</option>
          <option value="M">ប្រុស</option>
          <option value="F">ស្រី</option>
        </select>
        <select className="input-field" style={{ width: 'auto' }} value={grade} aria-label="និទ្ទេស"
          onChange={(e) => { setGrade(e.target.value); setPage(1) }}>
          <option value="">គ្រប់និទ្ទេស</option>
          {GRADES.map((g) => <option key={g} value={g}>និទ្ទេស {g}</option>)}
        </select>
        <select className="input-field" style={{ width: 'auto' }} value={stream} aria-label="ថ្នាក់"
          onChange={(e) => { setStream(e.target.value); setPage(1) }}>
          <option value="">គ្រប់ថ្នាក់</option>
          <option value="science">វិទ្យាសាស្ត្រ</option>
          <option value="social_science">វិទ្យាសាស្ត្រសង្គម</option>
        </select>
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
            <GraduationCap size={32} />
            <span>{hasFilters ? 'ពុំមានសិស្សត្រូវនឹងតម្រងនេះទេ' : `មិនទាន់មានសិស្សក្នុងឆ្នាំ ${year ?? ''} នៅឡើយ`}</span>
            {canEdit && !hasFilters && (
              <button onClick={openAdd} className="btn btn-primary btn-sm"><UserPlus size={15} /> បន្ថែមសិស្សដំបូង</button>
            )}
          </div>
        ) : (
          <div style={{ overflowX: 'auto', opacity: loading ? 0.6 : 1 }}>
            <table className="students-table">
              <thead>
                <tr>
                  <th className="num">ល.រ</th>
                  <th>គោត្តនាម-នាម</th>
                  <th className="center">ភេទ</th>
                  <th className="center">និ.</th>
                  <th className="num">លំដាប់ពិន្ទុ</th>
                  <th>វិទ្យាល័យ</th>
                  <th>ថ្នាក់<span className="th-sub">(វិទ្យាសាស្ត្រ/វិទ្យាសាស្ត្រសង្គម)</span></th>
                  <th>ស្នើសុំនៅសាកលវិទ្យាល័យ/វិទ្យាស្ថាន</th>
                  <th>ជំនាញ/មុខវិជ្ជា</th>
                  <th>លេខទូរស័ព្ទ</th>
                  <th>ផ្សេងៗ</th>
                  {(canEdit || canDelete) && <th aria-label="សកម្មភាព" />}
                </tr>
              </thead>
              <tbody>
                {data.items.map((s, i) => (
                  <tr key={s.id}>
                    <td className="num">{rowOffset + i + 1}</td>
                    <td style={{ fontWeight: 600, whiteSpace: 'nowrap' }}>{s.full_name}</td>
                    <td className="center">{GENDER_LABEL[s.gender] || s.gender}</td>
                    <td className="center">
                      {s.grade ? (
                        <span className="grade-pill">
                          <span className="grade-pill-dot" style={{ background: `var(--grade-${s.grade})` }} />{s.grade}
                        </span>
                      ) : '–'}
                    </td>
                    <td className="num">{dash(s.score_rank)}</td>
                    <td>{dash(s.high_school)}</td>
                    <td>{s.stream ? STREAM_LABEL[s.stream] : '–'}</td>
                    <td>{dash(s.university)}</td>
                    <td>{dash(s.major)}</td>
                    <td style={{ whiteSpace: 'nowrap', fontVariantNumeric: 'tabular-nums' }}>{dash(s.phone)}</td>
                    <td className="note-cell" title={s.note || undefined}>{dash(s.note)}</td>
                    {(canEdit || canDelete) && (
                      <td style={{ textAlign: 'right', whiteSpace: 'nowrap' }}>
                        {canEdit && (
                          <button onClick={() => openEdit(s)} className="btn btn-ghost" aria-label={`កែប្រែ ${s.full_name}`} title="កែប្រែ"><Pencil size={15} /></button>
                        )}
                        {canDelete && (
                          <button onClick={() => setToDelete(s)} className="btn btn-ghost" aria-label={`លុប ${s.full_name}`} title="លុប" style={{ color: 'var(--rose-primary)' }}><Trash2 size={15} /></button>
                        )}
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {data && data.items.length > 0 && (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 18px', borderTop: '1px solid var(--border-subtle)', flexWrap: 'wrap', gap: '10px' }}>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              ទំព័រ {data.meta.page} នៃ {data.meta.total_pages || 1} · សរុប {data.meta.total} នាក់
            </span>
            <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
              <select className="input-field" style={{ width: 'auto', padding: '5px 8px', fontSize: '0.8rem' }} value={size}
                onChange={(e) => { setSize(Number(e.target.value)); setPage(1) }} aria-label="ចំនួនក្នុងមួយទំព័រ">
                {[25, 50, 100, 200].map((n) => <option key={n} value={n}>{n} / ទំព័រ</option>)}
              </select>
              <button disabled={!data.meta.has_prev} onClick={() => setPage((p) => Math.max(1, p - 1))} className="btn btn-secondary btn-sm"><ChevronLeft size={15} /> ថយក្រោយ</button>
              <button disabled={!data.meta.has_next} onClick={() => setPage((p) => p + 1)} className="btn btn-secondary btn-sm">ទៅមុខ <ChevronRight size={15} /></button>
            </div>
          </div>
        )}
      </section>

      {/* ── Add / edit ── */}
      {formFor && (
        <div className="modal-backdrop" onClick={() => !saving && setFormFor(null)}>
          <div className="glass-panel modal-card" style={{ maxWidth: '720px' }} role="dialog" aria-modal="true" aria-labelledby="st-title" onClick={(e) => e.stopPropagation()}>
            <div className="modal-head">
              <div>
                <div className="audit-entity">ឆ្នាំ {formFor === 'new' ? year : formFor.academic_year}</div>
                <h2 id="st-title" style={{ fontSize: '1.1rem' }}>{formFor === 'new' ? 'បន្ថែមសិស្ស' : `កែប្រែ · ${formFor.full_name}`}</h2>
              </div>
              <button onClick={() => setFormFor(null)} className="btn btn-ghost" aria-label="បិទ"><X size={18} /></button>
            </div>

            <form onSubmit={(e) => { e.preventDefault(); save(false) }} className="student-form">
              <label className="input-group span-2">
                <span className="input-label">គោត្តនាម-នាម <span className="req">*</span></span>
                <input ref={nameRef} autoFocus required className="input-field" value={form.full_name} onChange={set('full_name')} placeholder="ឧ. សុខ ដារ៉ា" maxLength={255} />
              </label>
              <label className="input-group">
                <span className="input-label">ភេទ <span className="req">*</span></span>
                <select required className="input-field" value={form.gender} onChange={set('gender')}>
                  <option value="">— ជ្រើសរើស —</option>
                  <option value="M">ប្រុស</option>
                  <option value="F">ស្រី</option>
                </select>
              </label>
              <label className="input-group">
                <span className="input-label">និទ្ទេស</span>
                <select className="input-field" value={form.grade} onChange={set('grade')}>
                  <option value="">–</option>
                  {GRADES.map((g) => <option key={g} value={g}>{g}</option>)}
                </select>
              </label>
              <label className="input-group">
                <span className="input-label">លំដាប់ពិន្ទុ</span>
                <input type="number" min={1} inputMode="numeric" className="input-field" value={form.score_rank} onChange={set('score_rank')} placeholder="ឧ. 152" />
              </label>
              <label className="input-group">
                <span className="input-label">ថ្នាក់</span>
                <select className="input-field" value={form.stream} onChange={set('stream')}>
                  <option value="">–</option>
                  <option value="science">វិទ្យាសាស្ត្រ</option>
                  <option value="social_science">វិទ្យាសាស្ត្រសង្គម</option>
                </select>
              </label>
              <label className="input-group span-2">
                <span className="input-label">វិទ្យាល័យ</span>
                <input className="input-field" value={form.high_school} onChange={set('high_school')} maxLength={255} />
              </label>
              <label className="input-group span-2">
                <span className="input-label">ស្នើសុំនៅសាកលវិទ្យាល័យ/វិទ្យាស្ថាន</span>
                <input className="input-field" value={form.university} onChange={set('university')} maxLength={255} />
              </label>
              <label className="input-group span-2">
                <span className="input-label">ជំនាញ/មុខវិជ្ជា</span>
                <input className="input-field" value={form.major} onChange={set('major')} maxLength={255} />
              </label>
              <label className="input-group span-2">
                <span className="input-label">លេខទូរស័ព្ទ</span>
                <input type="tel" className="input-field" value={form.phone} onChange={set('phone')} placeholder="ឧ. 012 345 678" maxLength={32} />
              </label>
              <label className="input-group span-4">
                <span className="input-label">ផ្សេងៗ</span>
                <textarea className="input-field" rows={2} value={form.note} onChange={set('note')} maxLength={2000} />
              </label>

              {formError && (
                <div role="alert" className="notice notice-rose span-4"><AlertTriangle size={15} /> {formError}</div>
              )}

              <div className="modal-foot span-4">
                <span className="audit-entity"><span className="req">*</span> ត្រូវតែបំពេញ</span>
                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                  <button type="button" onClick={() => setFormFor(null)} className="btn btn-secondary" disabled={saving}>បោះបង់</button>
                  {formFor === 'new' && (
                    <button type="button" onClick={() => save(true)} className="btn btn-secondary" disabled={saving}>
                      <UserPlus size={15} /> រក្សាទុក និងបន្ថែមថ្មី
                    </button>
                  )}
                  <button type="submit" className="btn btn-primary" disabled={saving}>
                    {saving ? <RefreshCw size={15} className="spin" /> : <Save size={15} />} រក្សាទុក
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ── Delete confirm ── */}
      {toDelete && (
        <div className="modal-backdrop" onClick={() => !deleting && setToDelete(null)}>
          <div className="glass-panel modal-card" style={{ maxWidth: '420px' }} role="alertdialog" aria-modal="true" aria-labelledby="sdel-title" onClick={(e) => e.stopPropagation()}>
            <h2 id="sdel-title" style={{ fontSize: '1.05rem' }}>លុបសិស្សនេះ?</h2>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginTop: '8px', lineHeight: 1.6 }}>
              {toDelete.full_name} ({GENDER_LABEL[toDelete.gender]}{toDelete.grade ? ` · និទ្ទេស ${toDelete.grade}` : ''})។ សកម្មភាពនេះមិនអាចត្រឡប់វិញបានទេ។
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
