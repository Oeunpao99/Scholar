import React, { useEffect, useState } from 'react'
import { Download, FileSpreadsheet, FileText, FileCode, Send, RefreshCw, CheckCircle2, AlertCircle } from 'lucide-react'
import { api } from '../lib/api'
import { daysAgo, formatCategory, khDate, localISODate, monthStart } from '../lib/format'
import { Category, Counters, SeriesPoint } from '../types'
import { DailyGainBars } from '../components/charts/DailyGainBars'
import { GradeDonut } from '../components/charts/GradeDonut'

type Preset = '7d' | '30d' | 'month' | 'custom'
type ExportFormat = 'excel' | 'pdf' | 'csv' | 'telegram'

const EXPORTS: Array<{ format: ExportFormat; label: string; ext: string; icon: typeof FileText }> = [
  { format: 'excel', label: 'Excel', ext: 'xlsx', icon: FileSpreadsheet },
  { format: 'pdf', label: 'PDF', ext: 'pdf', icon: FileText },
  { format: 'csv', label: 'CSV', ext: 'csv', icon: FileCode },
  { format: 'telegram', label: 'អត្ថបទ Telegram', ext: 'txt', icon: Send },
]

const pct = (part: number, whole: number) => (whole > 0 ? Math.round((part / whole) * 100) : 0)

export const AnalyticsExportPage: React.FC = () => {
  const [categories, setCategories] = useState<Category[]>([])
  const [academicYear, setAcademicYear] = useState<number>(2026)

  const [preset, setPreset] = useState<Preset>('month')
  const [startDate, setStartDate] = useState<string>(monthStart())
  const [endDate, setEndDate] = useState<string>(localISODate())
  const [categoryId, setCategoryId] = useState<string>('')

  const [points, setPoints] = useState<SeriesPoint[]>([])
  const [grades, setGrades] = useState<Record<string, Counters>>({})
  const [loading, setLoading] = useState<boolean>(false)
  const [loadError, setLoadError] = useState<string | null>(null)

  const [exporting, setExporting] = useState<ExportFormat | null>(null)
  const [exportMsg, setExportMsg] = useState<{ ok: boolean; text: string } | null>(null)

  useEffect(() => {
    Promise.all([api.getCategories(), api.getCurrentYear()])
      .then(([cats, year]) => {
        setCategories(cats.items)
        setAcademicYear(year.current_year)
      })
      .catch((err) => console.error('Failed to load initial export meta', err))
  }, [])

  const load = async () => {
    setLoading(true)
    setLoadError(null)
    try {
      const res = await api.getCumulativeSeries(startDate || undefined, endDate || undefined, categoryId || undefined)
      setPoints(res.points)
      setGrades(res.grades || {})
    } catch (err: any) {
      setLoadError(err.message || 'បរាជ័យក្នុងការផ្ទុកទិន្នន័យ')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [startDate, endDate, categoryId])

  const applyPreset = (p: Preset) => {
    setPreset(p)
    const today = localISODate()
    if (p === '7d') { setStartDate(daysAgo(6)); setEndDate(today) }
    if (p === '30d') { setStartDate(daysAgo(29)); setEndDate(today) }
    if (p === 'month') { setStartDate(monthStart()); setEndDate(today) }
  }

  const handleDownload = async (format: ExportFormat, ext: string) => {
    setExporting(format)
    setExportMsg(null)
    try {
      const blob = await api.exportData(format, {
        start: startDate || undefined,
        end: endDate || undefined,
        category_id: categoryId || undefined,
        academic_year: academicYear,
      })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `scholar_${format}_${startDate}_${endDate}.${ext}`
      document.body.appendChild(a)
      a.click()
      a.remove()
      window.URL.revokeObjectURL(url)
      setExportMsg({ ok: true, text: `បានទាញយកឯកសារ ${ext.toUpperCase()} រួចរាល់` })
    } catch (err: any) {
      setExportMsg({ ok: false, text: err.message || `បរាជ័យក្នុងការទាញយក ${ext.toUpperCase()}` })
    } finally {
      setExporting(null)
    }
  }

  // Range figures: students gained between the two dates (not all-time).
  const gained = points.reduce(
    (acc, p) => ({
      total: acc.total + (p.gain?.total || 0),
      female: acc.female + (p.gain?.female || 0),
      pp: acc.pp + (p.gain?.pp || 0),
      kp: acc.kp + (p.gain?.kp || 0),
    }),
    { total: 0, female: 0, pp: 0, kp: 0 }
  )
  const cumulativeEnd = points.length > 0 ? points[points.length - 1].total : 0
  const activeDays = points.filter((p) => (p.gain?.total || 0) > 0)
  const selectedCategory = categories.find((c) => c.id === categoryId)
  const scopeLabel = selectedCategory ? formatCategory(selectedCategory.roman_numeral, selectedCategory.title) : 'គ្រប់ផ្នែក'

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div className="page-header">
        <div>
          <h1 className="page-title">ការវិភាគ និងនាំចេញ</h1>
          <p className="page-subtitle">តាមដានចំនួនសិស្សចុះឈ្មោះប្រចាំថ្ងៃ និងការបែងចែកតាមនិទ្ទេស</p>
        </div>
        <button onClick={load} className="btn btn-secondary btn-sm" disabled={loading}>
          <RefreshCw size={14} className={loading ? 'spin' : ''} />
          ផ្ទុកឡើងវិញ
        </button>
      </div>

      {/* Filters — one row above the charts; they drive charts AND exports. */}
      <div style={{ display: 'flex', alignItems: 'flex-end', gap: '12px', flexWrap: 'wrap' }}>
        <div className="preset-group" role="group" aria-label="ចន្លោះពេល">
          {([['7d', '៧ ថ្ងៃ'], ['30d', '៣០ ថ្ងៃ'], ['month', 'ខែនេះ']] as Array<[Preset, string]>).map(([p, label]) => (
            <button key={p} className={preset === p ? 'active' : ''} aria-pressed={preset === p} onClick={() => applyPreset(p)}>
              {label}
            </button>
          ))}
        </div>
        <label className="input-group">
          <span className="input-label">ចាប់ពី</span>
          <input type="date" className="input-field" style={{ width: 'auto' }} value={startDate} max={endDate}
            onChange={(e) => { setStartDate(e.target.value); setPreset('custom') }} />
        </label>
        <label className="input-group">
          <span className="input-label">ដល់</span>
          <input type="date" className="input-field" style={{ width: 'auto' }} value={endDate} min={startDate}
            onChange={(e) => { setEndDate(e.target.value); setPreset('custom') }} />
        </label>
        <label className="input-group" style={{ minWidth: '240px' }}>
          <span className="input-label">ផ្នែកសិស្ស</span>
          <select className="input-field" value={categoryId} onChange={(e) => setCategoryId(e.target.value)}>
            <option value="">គ្រប់ផ្នែក</option>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>{formatCategory(c.roman_numeral, c.title)}</option>
            ))}
          </select>
        </label>
      </div>

      {loadError && (
        <div role="alert" className="badge badge-rose" style={{ borderRadius: 'var(--radius-md)', padding: '10px 14px', whiteSpace: 'normal' }}>
          <AlertCircle size={15} /> {loadError}
        </div>
      )}

      {/* Headline numbers for the range */}
      <div className="stat-strip">
        <div>
          <div className="stat-label">សិស្សចុះឈ្មោះថ្មី</div>
          <div className="stat-value">{gained.total}</div>
          <div className="stat-note">{khDate(startDate)} – {khDate(endDate)}</div>
        </div>
        <div>
          <div className="stat-label">សិស្សស្រី</div>
          <div className="stat-value">{gained.female}</div>
          <div className="stat-note">{pct(gained.female, gained.total)}% នៃសិស្សថ្មី</div>
        </div>
        <div>
          <div className="stat-label">ភ្នំពេញ / ខេត្ត</div>
          <div className="stat-value">{gained.pp} / {gained.kp}</div>
          <div className="stat-note">{pct(gained.pp, gained.total)}% / {pct(gained.kp, gained.total)}%</div>
        </div>
        <div>
          <div className="stat-label">សរុបទាំងអស់</div>
          <div className="stat-value">{cumulativeEnd}</div>
          <div className="stat-note">គិតត្រឹម {khDate(endDate)}</div>
        </div>
      </div>

      {/* Charts */}
      <div className="chart-grid" style={{ opacity: loading ? 0.6 : 1, transition: 'opacity 0.15s ease' }}>
        <section className="glass-panel chart-card">
          <div className="chart-card-head">
            <h2 className="chart-card-title">សិស្សចុះឈ្មោះថ្មីប្រចាំថ្ងៃ</h2>
            <span className="chart-card-sub">{scopeLabel}</span>
          </div>
          <DailyGainBars points={points} />
        </section>

        <section className="glass-panel chart-card">
          <div className="chart-card-head">
            <h2 className="chart-card-title">សិស្សតាមនិទ្ទេស</h2>
            <span className="chart-card-sub">{scopeLabel}</span>
          </div>
          <GradeDonut grades={grades} />
        </section>
      </div>

      {/* Exports — same filters as the charts */}
      <section className="glass-panel" style={{ padding: '18px 22px', display: 'flex', alignItems: 'center', gap: '16px', flexWrap: 'wrap' }}>
        <div style={{ flex: '1 1 220px' }}>
          <h2 className="chart-card-title">នាំចេញរបាយការណ៍</h2>
          <div className="chart-card-sub">ប្រើចន្លោះកាលបរិច្ឆេទ និងផ្នែកដូចខាងលើ</div>
          {exportMsg && (
            <div role="status" style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '6px', fontSize: '0.8rem', color: exportMsg.ok ? 'var(--emerald-primary)' : 'var(--rose-primary)' }}>
              {exportMsg.ok ? <CheckCircle2 size={14} /> : <AlertCircle size={14} />}
              {exportMsg.text}
            </div>
          )}
        </div>
        <label style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
          ឆ្នាំសិក្សា
          <input type="number" className="input-field" style={{ width: '96px' }} value={academicYear}
            onChange={(e) => setAcademicYear(Number(e.target.value))} />
        </label>
        <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
          {EXPORTS.map(({ format, label, ext, icon: Icon }) => (
            <button key={format} onClick={() => handleDownload(format, ext)} disabled={exporting !== null} className="btn btn-secondary">
              {exporting === format ? <RefreshCw size={15} className="spin" /> : <Icon size={15} />}
              {label}
            </button>
          ))}
        </div>
      </section>

      {/* Table view of the same data (readable without the charts) */}
      <section className="glass-panel" style={{ overflow: 'hidden' }}>
        <div style={{ padding: '16px 22px 10px' }}>
          <h2 className="chart-card-title">ថ្ងៃដែលមានការចុះឈ្មោះ</h2>
          <div className="chart-card-sub">{activeDays.length} ថ្ងៃ ក្នុងចន្លោះកាលបរិច្ឆេទនេះ</div>
        </div>
        {activeDays.length === 0 ? (
          <div className="chart-empty" style={{ minHeight: '100px' }}>មិនទាន់មានទិន្នន័យ</div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.875rem' }}>
              <thead>
                <tr>
                  <th style={{ padding: '10px 22px', textAlign: 'left' }}>កាលបរិច្ឆេទ</th>
                  <th style={{ padding: '10px 14px', textAlign: 'right' }}>សិស្សថ្មី</th>
                  <th style={{ padding: '10px 14px', textAlign: 'right' }}>ស្រី</th>
                  <th style={{ padding: '10px 14px', textAlign: 'right' }}>ភ្នំពេញ</th>
                  <th style={{ padding: '10px 14px', textAlign: 'right' }}>ខេត្ត</th>
                  <th style={{ padding: '10px 22px', textAlign: 'right' }}>សរុបទាំងអស់</th>
                </tr>
              </thead>
              <tbody>
                {[...activeDays].reverse().map((p) => (
                  <tr key={p.date} style={{ fontVariantNumeric: 'tabular-nums' }}>
                    <td style={{ padding: '10px 22px', fontWeight: 600 }}>{khDate(p.date)}</td>
                    <td style={{ padding: '10px 14px', textAlign: 'right', fontWeight: 700 }}>+{p.gain.total}</td>
                    <td style={{ padding: '10px 14px', textAlign: 'right' }}>{p.gain.female}</td>
                    <td style={{ padding: '10px 14px', textAlign: 'right' }}>{p.gain.pp}</td>
                    <td style={{ padding: '10px 14px', textAlign: 'right' }}>{p.gain.kp}</td>
                    <td style={{ padding: '10px 22px', textAlign: 'right', color: 'var(--text-muted)' }}>{p.total}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}
