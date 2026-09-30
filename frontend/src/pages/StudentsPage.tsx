import React, { useEffect, useRef, useState } from 'react'
import {
  Search, RefreshCw, Pencil, Trash2, UserPlus, ChevronLeft, ChevronRight, X, Save, AlertTriangle, GraduationCap,
  ScanText, FileText, Check, Loader, Download, FileSpreadsheet,
} from 'lucide-react'
import { api } from '../lib/api'
import { PaginatedResponse, Student, StudentExtraction, StudentImportResult, StudentInput } from '../types'
import { useAuth } from '../context/AuthContext'
import { StudentPhoto } from '../components/StudentPhoto'
import { Segmented } from '../components/ui/Segmented'
import { SelectMenu } from '../components/ui/SelectMenu'

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

// Phones: don't open the keyboard the moment a form appears.
const IS_TOUCH = typeof window !== 'undefined' && window.matchMedia?.('(pointer: coarse)').matches

const dash = (v?: string | number | null) => (v === null || v === undefined || v === '' ? '–' : v)

const FIELD_LABEL: Record<string, string> = {
  full_name: 'គោត្តនាម-នាម', gender: 'ភេទ', grade: 'និទ្ទេស', score_rank: 'លំដាប់ពិន្ទុ',
  high_school: 'វិទ្យាល័យ', stream: 'ថ្នាក់', university: 'សាកលវិទ្យាល័យ/វិទ្យាស្ថាន',
  major: 'ជំនាញ/មុខវិជ្ជា', phone: 'លេខទូរស័ព្ទ',
}

const fromExtraction = (x: StudentExtraction): FormState => {
  const v = x.values
  const str = (k: keyof typeof v) => (v[k] === undefined ? '' : String(v[k]))
  return {
    ...EMPTY_FORM,
    full_name: str('full_name'),
    gender: (str('gender') as FormState['gender']) || '',
    grade: str('grade'),
    score_rank: str('score_rank'),
    high_school: str('high_school'),
    stream: str('stream'),
    university: str('university'),
    major: str('major'),
    phone: str('phone'),
  }
}

type Scan = { name: string; previewUrl: string | null; result: StudentExtraction }

// The server reads the form in one request, so there is no progress to read back.
// These are the stages the work really goes through, revealed by elapsed time, so
// the wait shows movement instead of a frozen screen. A slow machine simply
// spends longer on an early stage.
const SCAN_STAGES = [
  { at: 0, label: 'កំពុងផ្ទុកឯកសារឡើងម៉ាស៊ីន…' },
  { at: 900, label: 'កំពុងបើកទំព័រពីឯកសារ…' },
  { at: 2200, label: 'កំពុងវាស់អក្សរក្នុងឯកសារ…' },
  { at: 7000, label: 'កំពុងស្វែងរករូបថតសិស្ស…' },
  { at: 13000, label: 'កំពុងបញ្ចប់ការវាស់…' },
]
// Creeps towards 90% and stops there: the bar must never claim to be finished
// while the server is still working.
const scanPercent = (ms: number) => Math.min(90, 100 * (1 - Math.exp(-ms / 5200)))
const fileSize = (bytes: number) =>
  bytes >= 1024 * 1024 ? `${(bytes / 1024 / 1024).toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`

type PhotoChange =
  | { kind: 'keep' }
  | { kind: 'new'; blob: Blob; url: string; fromScan: boolean }
  | { kind: 'remove' }

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
  const fileRef = useRef<HTMLInputElement>(null)
  const [scan, setScan] = useState<Scan | null>(null)
  const [scanning, setScanning] = useState(false)
  const [scanError, setScanError] = useState<string | null>(null)
  const [scanPending, setScanPending] = useState<{ name: string; size: number } | null>(null)
  const [scanMs, setScanMs] = useState(0)
  const scanAbort = useRef<AbortController | null>(null)

  // What saving should do with the photo: leave it, replace it, or remove it.
  const [photo, setPhoto] = useState<PhotoChange>({ kind: 'keep' })
  const photoRef = useRef<HTMLInputElement>(null)
  const resetPhoto = () => setPhoto((p) => { if (p.kind === 'new') URL.revokeObjectURL(p.url); return { kind: 'keep' } })
  const choosePhoto = (blob: Blob, fromScan = false) =>
    setPhoto((p) => {
      if (p.kind === 'new') URL.revokeObjectURL(p.url)
      return { kind: 'new', blob, url: URL.createObjectURL(blob), fromScan }
    })
  const onPhotoFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return
    if (!file.type.startsWith('image/')) { setFormError('រូបថតត្រូវតែជា JPG, PNG ឬ WebP'); return }
    choosePhoto(file)
  }

  const clearScan = () => {
    setScan((s) => { if (s?.previewUrl) URL.revokeObjectURL(s.previewUrl); return null })
  }
  const closeForm = () => { setFormFor(null); clearScan(); resetPhoto() }
  // Highlight what OCR filled in, so the reviewer knows which values to double-check.
  const fieldClass = (key: string) => (scan?.result.found.includes(key) ? 'input-field prefilled' : 'input-field')

  const ACCEPTED = ['image/jpeg', 'image/png', 'image/webp', 'application/pdf']
  const isList = (f: File) => /\.(docx|xlsx)$/i.test(f.name)

  // A .docx/.xlsx is a whole list to import; anything else is one application form to scan.
  const handleFile = (file: File) => (isList(file) ? importList(file) : scanFile(file))

  const onFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    e.target.value = '' // allow picking the same file again
    if (file) handleFile(file)
  }

  const [importing, setImporting] = useState(false)
  const [importResult, setImportResult] = useState<(StudentImportResult & { name: string }) | null>(null)

  const importList = async (file: File) => {
    setImporting(true)
    setScanError(null)
    setImportResult(null)
    try {
      const result = await api.importStudents(file, year ?? undefined)
      setImportResult({ ...result, name: file.name })
      if (result.created) fetchStudents()
    } catch (err: any) {
      setScanError(`នាំចូលមិនបាន: ${err.message}`)
    } finally {
      setImporting(false)
    }
  }

  // Drag & drop anywhere on the page. The counter survives dragenter/leave
  // firing for every child element the pointer crosses.
  const [dragging, setDragging] = useState(false)
  const dragDepth = useRef(0)
  const hasFiles = (e: React.DragEvent) => Array.from(e.dataTransfer.types).includes('Files')
  const dropEnabled = canEdit && !scanning && !importing && !(formFor && formFor !== 'new')

  const onDragEnter = (e: React.DragEvent) => {
    if (!dropEnabled || !hasFiles(e)) return
    e.preventDefault()
    dragDepth.current += 1
    setDragging(true)
  }
  const onDragOver = (e: React.DragEvent) => {
    if (!dropEnabled || !hasFiles(e)) return
    e.preventDefault() // required, or the browser opens the file itself
    e.dataTransfer.dropEffect = 'copy'
  }
  const onDragLeave = (e: React.DragEvent) => {
    if (!dropEnabled || !hasFiles(e)) return
    dragDepth.current = Math.max(0, dragDepth.current - 1)
    if (dragDepth.current === 0) setDragging(false)
  }
  const onDrop = (e: React.DragEvent) => {
    if (!dropEnabled || !hasFiles(e)) return
    e.preventDefault()
    dragDepth.current = 0
    setDragging(false)
    const files = Array.from(e.dataTransfer.files)
    if (files.length > 1) setScanError('សូមទម្លាក់ឯកសារម្តងមួយ')
    if (files[0]) handleFile(files[0])
  }

  const scanFile = async (file: File) => {
    if (file.type && !ACCEPTED.includes(file.type)) {
      setScanError('សូមប្រើឯកសារ JPG, PNG, WebP ឬ PDF')
      return
    }
    const controller = new AbortController()
    scanAbort.current = controller
    setScanning(true)
    setScanMs(0)
    setScanPending({ name: file.name, size: file.size })
    setScanError(null)
    try {
      const result = await api.extractStudent(file, controller.signal)
      clearScan()
      setScan({
        name: file.name,
        previewUrl: file.type.startsWith('image/') ? URL.createObjectURL(file) : null,
        result,
      })
      setForm(fromExtraction(result))
      resetPhoto()
      if (result.photo) choosePhoto(await (await fetch(result.photo)).blob(), true)
      setFormError(null)
      setFormFor('new')
    } catch (err: any) {
      // Cancelling is a choice, not a failure — the server aborts on disconnect.
      if (err?.name !== 'AbortError') setScanError(`អានឯកសារមិនបាន: ${err.message}`)
    } finally {
      scanAbort.current = null
      setScanning(false)
      setScanPending(null)
    }
  }

  const cancelScan = () => scanAbort.current?.abort()

  // Drives the progress overlay: ticks a tenth of a second while the request runs.
  useEffect(() => {
    if (!scanning) { setScanMs(0); return }
    const started = Date.now()
    const id = window.setInterval(() => setScanMs(Date.now() - started), 100)
    return () => window.clearInterval(id)
  }, [scanning])

  // Success messages fade on their own; errors stay until closed.
  useEffect(() => {
    if (!notice) return
    const t = setTimeout(() => setNotice(null), 5000)
    return () => clearTimeout(t)
  }, [notice])

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
      closeForm(); setToDelete(null)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  const [exporting, setExporting] = useState<'word' | 'excel' | 'pdf' | null>(null)
  const [exportMenuOpen, setExportMenuOpen] = useState(false)
  const exportMenuRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (exportMenuRef.current && !exportMenuRef.current.contains(e.target as Node)) {
        setExportMenuOpen(false)
      }
    }
    if (exportMenuOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [exportMenuOpen])

  const handleExport = async (fmt: 'word' | 'excel' | 'pdf') => {
    setExportMenuOpen(false)
    setExporting(fmt)
    try {
      const { blob, filename } = await api.exportStudents({
        format: fmt,
        academic_year: year ?? undefined,
        q: search || undefined,
        gender: gender || undefined,
        grade: grade || undefined,
        stream: stream || undefined,
      })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
      setNotice(`បានទាញយកឯកសារ «${filename}» ដោយជោគជ័យ`)
    } catch (err: any) {
      setScanError(err.message || 'ការនាំចេញមិនបានសម្រេច')
    } finally {
      setExporting(null)
    }
  }

  const openAdd = () => { clearScan(); resetPhoto(); setForm(EMPTY_FORM); setFormError(null); setFormFor('new') }
  const openEdit = (s: Student) => { clearScan(); resetPhoto(); setForm(toForm(s)); setFormError(null); setFormFor(s) }
  const setValue = (key: keyof FormState) => (v: string) => setForm((f) => ({ ...f, [key]: v }))
  const segClass = (key: string) => (scan?.result.found.includes(key) ? 'prefilled' : '')
  const set = (key: keyof FormState) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
    setForm((f) => ({ ...f, [key]: e.target.value }))

  const save = async (addAnother: boolean) => {
    if (!form.full_name.trim()) { setFormError('សូមបញ្ចូលគោត្តនាម-នាម'); return }
    if (!form.gender) { setFormError('សូមជ្រើសរើសភេទ'); return }
    if (form.score_rank && !(Number(form.score_rank) > 0)) { setFormError('លំដាប់ពិន្ទុត្រូវតែជាលេខធំជាង 0'); return }
    setSaving(true)
    setFormError(null)
    try {
      let saved: Student | null = null
      if (formFor === 'new') {
        saved = await api.createStudent({ ...toPayload(form), academic_year: year ?? undefined })
        setNotice(`បានបន្ថែម ${saved.full_name}`)
      } else if (formFor) {
        saved = await api.updateStudent(formFor.id, toPayload(form))
        setNotice(`បានកែប្រែ ${saved.full_name}`)
      }
      // The student is saved at this point; a photo failure must not make the
      // user retry the whole form (that would add the student twice).
      if (saved) {
        try {
          if (photo.kind === 'new') await api.setStudentPhoto(saved.id, photo.blob)
          else if (photo.kind === 'remove' && saved.has_photo) await api.deleteStudentPhoto(saved.id)
        } catch (err: any) {
          setNotice(`បានរក្សាទុក ${saved.full_name} ប៉ុន្តែរូបថតមិនបានរក្សាទុក: ${err.message}`)
        }
      }
      if (addAnother) {
        // Keep school/stream/university: consecutive entries usually share them.
        clearScan()
        resetPhoto()
        setForm((f) => ({ ...EMPTY_FORM, high_school: f.high_school, stream: f.stream, university: f.university }))
        nameRef.current?.focus()
      } else {
        closeForm()
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
  const scanStep = SCAN_STAGES.filter((s) => scanMs >= s.at).length - 1

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '20px', minHeight: '70vh' }}
      onDragEnter={onDragEnter} onDragOver={onDragOver} onDragLeave={onDragLeave} onDrop={onDrop}>
      {dragging && (
        <div className="drop-overlay" aria-hidden="true">
          <div className="drop-overlay-card">
            <ScanText size={36} />
            <strong>ទម្លាក់ពាក្យស្នើសុំនៅទីនេះ</strong>
            <span>JPG, PNG, WebP, PDF (សិស្សម្នាក់) · Word/Excel (បញ្ជីទាំងមូល)</span>
          </div>
        </div>
      )}
      {scanning && scanPending && (
        <div className="scan-overlay" role="dialog" aria-modal="true" aria-label="កំពុងអានឯកសារ">
          <div className="scan-overlay-card">
            <div className="scan-spinner"><RefreshCw size={22} className="spin" /></div>
            <strong aria-live="polite">{SCAN_STAGES[scanStep].label}</strong>
            <span>{scanPending.name} · {fileSize(scanPending.size)}</span>
            <div className="scan-bar">
              <i style={{ width: `${scanPercent(scanMs)}%` }} />
            </div>
            <ol className="scan-steps">
              {SCAN_STAGES.map((s, i) => (
                <li key={s.at} className={`scan-step ${i < scanStep ? 'done' : i === scanStep ? 'active' : ''}`}>
                  {i < scanStep ? <Check size={13} /> : i === scanStep ? <Loader size={13} className="spin" /> : <span className="scan-dot" />}
                  <span>{s.label.replace('…', '')}</span>
                </li>
              ))}
            </ol>
            <span className="scan-hint">
              ប្រព័ន្ធកំពុងអានឯកសារ — ឯកសារច្រើនទំព័រត្រូវការពេលបន្តិច · {Math.floor(scanMs / 1000)} វិនាទី
            </span>
            <button className="btn btn-ghost" onClick={cancelScan}>បោះបង់</button>
          </div>
        </div>
      )}
      <div className="toast-stack">
        {notice && (
          <div role="status" className="notice notice-emerald">
            <span style={{ flex: 1 }}>{notice}</span>
            <button className="btn btn-ghost" style={{ padding: 2 }} onClick={() => setNotice(null)} aria-label="បិទ"><X size={14} /></button>
          </div>
        )}
        {scanError && (
          <div role="alert" className="notice notice-rose">
            <AlertTriangle size={15} />
            <span style={{ flex: 1 }}>{scanError}</span>
            <button className="btn btn-ghost" style={{ padding: 2 }} onClick={() => setScanError(null)} aria-label="បិទ"><X size={14} /></button>
          </div>
        )}
        {importResult && (
          <div role="status" className={`notice ${importResult.created ? 'notice-emerald' : 'notice-amber'}`} style={{ alignItems: 'flex-start' }}>
            <FileSpreadsheet size={15} style={{ marginTop: 3, flexShrink: 0 }} />
            <div style={{ flex: 1, lineHeight: 1.6 }}>
              <strong>{importResult.name}</strong>: បានបន្ថែម {importResult.created} នាក់
              {importResult.duplicates > 0 && ` · រំលងស្ទួន ${importResult.duplicates}`}
              {importResult.errors.length > 0 && ` · មានបញ្ហា ${importResult.errors.length} ជួរ`}
              {importResult.errors.length > 0 && (
                <details>
                  <summary style={{ cursor: 'pointer' }}>មើលជួរដែលមានបញ្ហា</summary>
                  <ul style={{ margin: '4px 0 0 18px', maxHeight: '40vh', overflowY: 'auto' }}>
                    {importResult.errors.slice(0, 50).map((e) => <li key={`${e.row}-${e.message}`}>ជួរទី {e.row}: {e.message}</li>)}
                    {importResult.errors.length > 50 && <li>… និង {importResult.errors.length - 50} ទៀត</li>}
                  </ul>
                </details>
              )}
            </div>
            <button className="btn btn-ghost" style={{ padding: 2 }} onClick={() => setImportResult(null)} aria-label="បិទ"><X size={14} /></button>
          </div>
        )}
      </div>

      <div className="page-header">
        <div>
          <h1 className="page-title">បញ្ជីឈ្មោះសិស្ស</h1>
          <p className="page-subtitle hide-phone">បញ្ជីសិស្សដែលបានដាក់ពាក្យ ព្រមទាំងសាកលវិទ្យាល័យ និងជំនាញដែលស្នើសុំ</p>
        </div>
        <div className="page-actions students-actions">
          <button onClick={fetchStudents} className="btn btn-ghost" aria-label="ផ្ទុកឡើងវិញ" title="ផ្ទុកឡើងវិញ">
            <RefreshCw size={16} className={loading ? 'spin' : ''} />
          </button>

          <div ref={exportMenuRef} className="students-export" style={{ position: 'relative' }}>
            <button
              type="button"
              onClick={() => setExportMenuOpen((v) => !v)}
              className="btn btn-secondary"
              disabled={exporting !== null}
              title="នាំចេញបញ្ជីឈ្មោះសិស្ស"
            >
              {exporting ? <RefreshCw size={16} className="spin" /> : <Download size={16} />}
              {exporting ? 'កំពុងនាំចេញ…' : 'នាំចេញ'}
            </button>
            {exportMenuOpen && (
              <div
                className="glass-panel"
                style={{
                  position: 'absolute',
                  right: 0,
                  top: 'calc(100% + 6px)',
                  zIndex: 50,
                  minWidth: 195,
                  padding: '6px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '4px',
                  boxShadow: '0 12px 28px rgba(0, 0, 0, 0.25)',
                }}
              >
                <button
                  type="button"
                  onClick={() => handleExport('word')}
                  className="btn btn-ghost"
                  style={{ justifyContent: 'flex-start', gap: 8, padding: '8px 12px', fontSize: '0.85rem' }}
                >
                  <FileText size={16} style={{ color: '#2563eb' }} />
                  <span>ឯកសារ Word (.docx)</span>
                </button>
                <button
                  type="button"
                  onClick={() => handleExport('excel')}
                  className="btn btn-ghost"
                  style={{ justifyContent: 'flex-start', gap: 8, padding: '8px 12px', fontSize: '0.85rem' }}
                >
                  <FileSpreadsheet size={16} style={{ color: '#16a34a' }} />
                  <span>ឯកសារ Excel (.xlsx)</span>
                </button>
                <button
                  type="button"
                  onClick={() => handleExport('pdf')}
                  className="btn btn-ghost"
                  style={{ justifyContent: 'flex-start', gap: 8, padding: '8px 12px', fontSize: '0.85rem' }}
                >
                  <FileText size={16} style={{ color: '#dc2626' }} />
                  <span>ឯកសារ PDF (.pdf)</span>
                </button>
              </div>
            )}
          </div>
          {canEdit && (
            <>
              <input ref={fileRef} type="file" accept="image/jpeg,image/png,image/webp,application/pdf,.docx,.xlsx"
                onChange={onFile} hidden aria-hidden="true" />
              <button onClick={() => fileRef.current?.click()} className="btn btn-secondary" disabled={scanning || importing}
                title="ជ្រើស ឬអូសទម្លាក់ពាក្យស្នើសុំ (JPG, PNG, PDF) ឬបញ្ជីសិស្ស Word (.docx) / Excel (.xlsx)">
                {scanning || importing ? <RefreshCw size={16} className="spin" /> : <ScanText size={16} />}
                {scanning ? 'កំពុងអានឯកសារ…' : importing ? 'កំពុងនាំចូល…' : 'បញ្ចូលពីឯកសារ'}
              </button>
              <button onClick={openAdd} className="btn btn-primary">
                <UserPlus size={16} /> បន្ថែមសិស្ស
              </button>
            </>
          )}
        </div>
      </div>

      {/* Filters */}
      <div className="filter-bar" style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', alignItems: 'center' }}>
        <SelectMenu ariaLabel="ឆ្នាំសិក្សា" value={year ? String(year) : ''}
          onChange={(v) => { setYear(Number(v)); setPage(1) }}
          options={yearOptions.map((y) => ({ value: String(y), label: `ឆ្នាំ ${y}` }))} />
        <div className="filter-search" style={{ position: 'relative', flex: '1 1 220px', maxWidth: '320px' }}>
          <Search size={15} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-dim)' }} />
          <input type="search" className="input-field" placeholder="ស្វែងរកឈ្មោះ លេខទូរស័ព្ទ សាលា…" value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)} style={{ paddingLeft: '36px' }} aria-label="ស្វែងរក" />
        </div>
        <SelectMenu ariaLabel="ភេទ" value={gender} onChange={(v) => { setGender(v); setPage(1) }}
          options={[{ value: '', label: 'គ្រប់ភេទ' }, { value: 'M', label: 'ប្រុស' }, { value: 'F', label: 'ស្រី' }]} />
        <SelectMenu ariaLabel="និទ្ទេស" value={grade} onChange={(v) => { setGrade(v); setPage(1) }}
          options={[{ value: '', label: 'គ្រប់និទ្ទេស' }, ...GRADES.map((g) => ({ value: g, label: `និទ្ទេស ${g}`, dot: `var(--grade-${g})` }))]} />
        <SelectMenu ariaLabel="ថ្នាក់" value={stream} onChange={(v) => { setStream(v); setPage(1) }}
          options={[{ value: '', label: 'គ្រប់ថ្នាក់' }, { value: 'science', label: 'វិទ្យាសាស្ត្រ' }, { value: 'social_science', label: 'វិទ្យាសាស្ត្រសង្គម' }]} />
        {hasFilters && <button onClick={clearFilters} className="link-button">សម្អាតតម្រង</button>}
      </div>

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
              <>
                <button onClick={openAdd} className="btn btn-primary btn-sm"><UserPlus size={15} /> បន្ថែមសិស្សដំបូង</button>
                <span style={{ fontSize: '0.8rem' }}>ឬអូសទម្លាក់ពាក្យស្នើសុំ (JPG, PNG, PDF) មកទីនេះ</span>
              </>
            )}
          </div>
        ) : (
          <div style={{ overflowX: 'auto', opacity: loading ? 0.6 : 1 }}>
            <table className="students-table">
              <thead>
                <tr>
                  <th className="num">ល.រ</th>
                  <th className="center">រូបថត</th>
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
                    <td className="num cell-index">{rowOffset + i + 1}</td>
                    <td className="center cell-photo" style={{ paddingTop: 6, paddingBottom: 6 }}>
                      <StudentPhoto id={s.id} name={s.full_name} version={s.has_photo ? s.photo_version : null} />
                    </td>
                    <td className="cell-name" style={{ fontWeight: 600, whiteSpace: 'nowrap' }}>{s.full_name}</td>
                    <td className="center" data-label="ភេទ">{GENDER_LABEL[s.gender] || s.gender}</td>
                    <td className="center" data-label="និទ្ទេស">
                      {s.grade ? (
                        <span className="grade-pill">
                          <span className="grade-pill-dot" style={{ background: `var(--grade-${s.grade})` }} />{s.grade}
                        </span>
                      ) : '–'}
                    </td>
                    <td className="num" data-label="លំដាប់ពិន្ទុ">{dash(s.score_rank)}</td>
                    <td data-label="វិទ្យាល័យ">{dash(s.high_school)}</td>
                    <td data-label="ថ្នាក់">{s.stream ? STREAM_LABEL[s.stream] : '–'}</td>
                    <td data-label="សាកលវិទ្យាល័យ">{dash(s.university)}</td>
                    <td data-label="ជំនាញ">{dash(s.major)}</td>
                    <td data-label="ទូរស័ព្ទ" style={{ whiteSpace: 'nowrap', fontVariantNumeric: 'tabular-nums' }}>{dash(s.phone)}</td>
                    <td className="note-cell" data-label="ផ្សេងៗ" title={s.note || undefined}>{dash(s.note)}</td>
                    {(canEdit || canDelete) && (
                      <td className="cell-actions" style={{ textAlign: 'right', whiteSpace: 'nowrap' }}>
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
          <div className="pager" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 18px', borderTop: '1px solid var(--border-subtle)', flexWrap: 'wrap', gap: '10px' }}>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              ទំព័រ {data.meta.page} នៃ {data.meta.total_pages || 1} · សរុប {data.meta.total} នាក់
            </span>
            <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
              <SelectMenu ariaLabel="ចំនួនក្នុងមួយទំព័រ" className="select-menu-sm" placement="up" value={String(size)}
                onChange={(v) => { setSize(Number(v)); setPage(1) }}
                options={[25, 50, 100, 200].map((n) => ({ value: String(n), label: `${n} / ទំព័រ` }))} />
              <button disabled={!data.meta.has_prev} onClick={() => setPage((p) => Math.max(1, p - 1))} className="btn btn-secondary btn-sm"><ChevronLeft size={15} /> ថយក្រោយ</button>
              <button disabled={!data.meta.has_next} onClick={() => setPage((p) => p + 1)} className="btn btn-secondary btn-sm">ទៅមុខ <ChevronRight size={15} /></button>
            </div>
          </div>
        )}
      </section>

      {/* ── Add / edit ── */}
      {formFor && (
        <div className="modal-backdrop" onClick={() => !saving && closeForm()}>
          <div className="glass-panel modal-card" style={{ maxWidth: scan ? '1180px' : '720px' }} role="dialog" aria-modal="true" aria-labelledby="st-title" onClick={(e) => e.stopPropagation()}>
            <div className="modal-head">
              <div>
                <div className="audit-entity">ឆ្នាំ {formFor === 'new' ? year : formFor.academic_year}</div>
                <h2 id="st-title" style={{ fontSize: '1.1rem' }}>
                  {formFor !== 'new' ? `កែប្រែ · ${formFor.full_name}` : scan ? 'ពិនិត្យព័ត៌មានពីឯកសារ' : 'បន្ថែមសិស្ស'}
                </h2>
              </div>
              <button onClick={closeForm} className="btn btn-ghost" aria-label="បិទ"><X size={18} /></button>
            </div>

            <div className={scan ? 'scan-review' : undefined}>
            {scan && (
              <aside className="scan-pane">
                {scan.previewUrl ? (
                  <a href={scan.previewUrl} target="_blank" rel="noreferrer" title="បើកទំហំពេញ">
                    <img src={scan.previewUrl} alt={`ឯកសារ ${scan.name}`} className="scan-preview" />
                  </a>
                ) : (
                  <div className="scan-file"><FileText size={22} /> {scan.name} · {scan.result.pages} ទំព័រ</div>
                )}
                <details className="scan-ocr">
                  <summary>អត្ថបទដែលអានបាន (OCR)</summary>
                  <pre>{scan.result.ocr_text || '—'}</pre>
                </details>
              </aside>
            )}

            <form onSubmit={(e) => { e.preventDefault(); save(false) }} className="student-form">
              {scan && (
                <div className={`notice ${scan.result.found.length ? 'notice-amber' : 'notice-rose'} span-4`} style={{ alignItems: 'flex-start' }}>
                  <ScanText size={15} style={{ marginTop: 3, flexShrink: 0 }} />
                  <div style={{ lineHeight: 1.6 }}>
                    <strong>អានបាន {scan.result.found.length}/{scan.result.found.length + scan.result.missing.length} ចន្លោះ</strong>
                    {' '}— សូមពិនិត្យ និងកែតម្រូវមុនរក្សាទុក។ ចន្លោះដែលបំពេញដោយប្រព័ន្ធមានពណ៌លឿង។
                    {scan.result.missing.length > 0 && (
                      <div>មិនទាន់មាន: {scan.result.missing.map((f) => FIELD_LABEL[f] || f).join(', ')}</div>
                    )}
                    {scan.result.warnings.map((w) => <div key={w}>{w}</div>)}
                  </div>
                </div>
              )}
              {(() => {
                const editing = formFor !== 'new' ? formFor : null
                const src = photo.kind === 'new' ? photo.url : null
                const hasSaved = photo.kind === 'keep' && !!editing?.has_photo
                const hasAny = !!src || hasSaved
                return (
                  <div className={`photo-field ${photo.kind === 'new' && photo.fromScan ? 'prefilled' : ''}`}>
                    <span className="input-label">រូបថត</span>
                    <StudentPhoto size="lg" name={form.full_name || '?'} src={src}
                      id={hasSaved ? editing!.id : undefined} version={hasSaved ? editing!.photo_version : null} />
                    <input ref={photoRef} type="file" accept="image/jpeg,image/png,image/webp" hidden onChange={onPhotoFile} />
                    <div className="photo-actions" style={{ display: 'flex', gap: 4, flexWrap: 'wrap', justifyContent: 'center' }}>
                      <button type="button" className="link-button" onClick={() => photoRef.current?.click()}>
                        {hasAny ? 'ប្តូររូប' : 'ជ្រើសរូប'}
                      </button>
                      {hasAny && (
                        <>
                          <span style={{ color: 'var(--text-dim)' }}>·</span>
                          <button type="button" className="link-button" style={{ color: 'var(--rose-primary)' }}
                            onClick={() => { resetPhoto(); if (hasSaved || editing?.has_photo) setPhoto({ kind: 'remove' }) }}>
                            លុបរូប
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                )
              })()}
              <label className="input-group span-2">
                <span className="input-label">គោត្តនាម-នាម <span className="req">*</span></span>
                <input ref={nameRef} autoFocus={!IS_TOUCH} required className={fieldClass('full_name')} value={form.full_name} onChange={set('full_name')} placeholder="ឧ. សុខ ដារ៉ា" maxLength={255} />
              </label>
              <div className="input-group">
                <span className="input-label">ភេទ <span className="req">*</span></span>
                <Segmented ariaLabel="ភេទ" className={segClass('gender')} value={form.gender} onChange={setValue('gender')}
                  options={[{ value: 'M', label: 'ប្រុស' }, { value: 'F', label: 'ស្រី' }]} />
              </div>
              <div className="input-group span-2 grade-field">
                <span className="input-label">និទ្ទេស</span>
                <Segmented ariaLabel="និទ្ទេស" allowClear className={`segmented-grade ${segClass('grade')}`} value={form.grade} onChange={setValue('grade')}
                  options={GRADES.map((g) => ({ value: g, label: <><span className="grade-pill-dot" style={{ background: `var(--grade-${g})` }} />{g}</>, title: `និទ្ទេស ${g}` }))} />
              </div>
              <label className="input-group">
                <span className="input-label">លំដាប់ពិន្ទុ</span>
                <input type="number" min={1} inputMode="numeric" className={fieldClass('score_rank')} value={form.score_rank} onChange={set('score_rank')} placeholder="ឧទាហរណ៍៖ 152" />
              </label>
              <div className="input-group span-2">
                <span className="input-label">ថ្នាក់</span>
                <Segmented ariaLabel="ថ្នាក់" allowClear className={segClass('stream')} value={form.stream} onChange={setValue('stream')}
                  options={[{ value: 'science', label: 'វិទ្យាសាស្ត្រ' }, { value: 'social_science', label: 'វិទ្យាសាស្ត្រសង្គម' }]} />
              </div>
              <label className="input-group span-2">
                <span className="input-label">វិទ្យាល័យ</span>
                <input className={fieldClass('high_school')} value={form.high_school} onChange={set('high_school')} maxLength={255} />
              </label>
              <label className="input-group span-2">
                <span className="input-label">ស្នើសុំនៅសាកលវិទ្យាល័យ/វិទ្យាស្ថាន</span>
                <input className={fieldClass('university')} value={form.university} onChange={set('university')} maxLength={255} />
              </label>
              <label className="input-group span-2">
                <span className="input-label">ជំនាញ/មុខវិជ្ជា</span>
                <input className={fieldClass('major')} value={form.major} onChange={set('major')} maxLength={255} />
              </label>
              <label className="input-group span-2">
                <span className="input-label">លេខទូរស័ព្ទ</span>
                <input type="tel" className={fieldClass('phone')} value={form.phone} onChange={set('phone')} placeholder="ឧទាហរណ៍៖ 012 345 678" maxLength={32} />
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
                  <button type="button" onClick={closeForm} className="btn btn-secondary" disabled={saving}>បោះបង់</button>
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
