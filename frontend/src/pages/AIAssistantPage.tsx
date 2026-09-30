import React, { useEffect, useState } from 'react'
import { Sparkles, FileText, Image as ImageIcon, CheckCircle2, AlertTriangle, UploadCloud, RefreshCw, Database } from 'lucide-react'
import confetti from 'canvas-confetti'
import { api } from '../lib/api'
import { formatCategory, localISODate } from '../lib/format'
import { AIParseResponse, Category } from '../types'

interface AIAssistantPageProps {
  onNavigate?: (tab: string, dateParam?: string) => void
}

type Mode = 'text' | 'image'

export const AIAssistantPage: React.FC<AIAssistantPageProps> = ({ onNavigate }) => {
  const [mode, setMode] = useState<Mode>('text')
  const [inputText, setInputText] = useState<string>('')
  const [imageData, setImageData] = useState<string | null>(null)
  const [provider, setProvider] = useState<string>('auto')

  const [categories, setCategories] = useState<Category[]>([])
  const [currentYear, setCurrentYear] = useState<number | undefined>(undefined)
  const [caps, setCaps] = useState<{ llm: boolean; ocr: boolean } | null>(null)

  const [parsing, setParsing] = useState(false)
  const [result, setResult] = useState<AIParseResponse | null>(null)
  const [parseError, setParseError] = useState<string | null>(null)
  const [applyDate, setApplyDate] = useState<string>('')
  const [applying, setApplying] = useState(false)
  const [applied, setApplied] = useState(false)
  const [applyError, setApplyError] = useState<string | null>(null)

  useEffect(() => {
    api.getAICapabilities().then(setCaps).catch(() => setCaps({ llm: false, ocr: false }))
    api.getCategories().then((r) => setCategories(r.items)).catch(() => undefined)
    api.getCurrentYear().then((r) => setCurrentYear(r.current_year)).catch(() => undefined)
  }, [])

  const resetResult = () => {
    setResult(null)
    setApplied(false)
    setParseError(null)
    setApplyError(null)
  }

  const loadSample = async () => {
    try {
      const sample = await api.getAISample()
      setInputText(sample.text)
      resetResult()
    } catch (err: any) {
      setParseError(`បរាជ័យក្នុងការទាញយកអត្ថបទគំរូ: ${err.message}`)
    }
  }

  const onFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = () => {
      setImageData(reader.result as string)
      resetResult()
    }
    reader.readAsDataURL(file)
  }

  const canAnalyze = mode === 'text' ? inputText.trim().length > 0 : !!imageData

  const analyze = async () => {
    if (!canAnalyze) return
    setParsing(true)
    resetResult()
    try {
      const isImage = mode === 'image'
      const chosen = provider === 'auto' ? undefined : provider === 'llm' && isImage ? 'llm+ocr' : provider
      const res = await api.parseAIText({
        text: isImage ? '' : inputText,
        images: isImage && imageData ? [imageData] : [],
        provider: chosen,
        current_year: currentYear,
      })
      setResult(res)
      setApplyDate(res.extracted.date || '')
    } catch (err: any) {
      setParseError(err.message || 'បរាជ័យក្នុងការវិភាគទិន្នន័យ')
    } finally {
      setParsing(false)
    }
  }

  const save = async () => {
    if (!result || !applyDate) return
    setApplying(true)
    setApplyError(null)
    try {
      await api.applyAIExtraction({
        report_date: applyDate,
        categories: result.extracted.categories,
        dry_run: false, // backend default is a dry run that saves nothing
      })
      setApplied(true)
      confetti({ particleCount: 60, spread: 70, origin: { y: 0.7 } })
    } catch (err: any) {
      setApplyError(err.message || 'បរាជ័យក្នុងការរក្សាទុក')
    } finally {
      setApplying(false)
    }
  }

  const catName = (code: string, fallback?: string | null) => {
    const c = categories.find((x) => x.code === code)
    return c ? formatCategory(c.roman_numeral, c.title) : fallback || code
  }

  const extracted = result?.extracted
  const dateMissing = !!extracted && !extracted.date
  const totals = (extracted?.categories || []).reduce(
    (a, c) => ({ total: a.total + c.total, female: a.female + c.female, pp: a.pp + c.pp, kp: a.kp + c.kp }),
    { total: 0, female: 0, pp: 0, kp: 0 }
  )

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div className="page-header">
        <div>
          <h1 className="page-title">ជំនួយការស្កេនទិន្នន័យ</h1>
          <p className="page-subtitle">បិទភ្ជាប់សារ Telegram ឬស្កេនរូបភាពតារាង — ប្រព័ន្ធនឹងស្រង់តួលេខឱ្យអ្នកពិនិត្យ មុនពេលរក្សាទុក</p>
        </div>
      </div>

      <div className="ai-grid">
        {/* ── Input ── */}
        <section className="glass-panel" style={{ padding: '6px 22px 22px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div className="tab-strip" role="tablist">
            <button role="tab" aria-selected={mode === 'text'} className={`tab ${mode === 'text' ? 'active' : ''}`} onClick={() => { setMode('text'); resetResult() }}>
              <FileText size={15} /> អត្ថបទ Telegram
            </button>
            <button role="tab" aria-selected={mode === 'image'} className={`tab ${mode === 'image' ? 'active' : ''}`} onClick={() => { setMode('image'); resetResult() }}>
              <ImageIcon size={15} /> ស្កេនរូបភាព
            </button>
          </div>

          {mode === 'text' ? (
            <div className="input-group">
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <label className="input-label" htmlFor="ai-text">សារ Telegram</label>
                <button type="button" onClick={loadSample} className="link-button">ប្រើអត្ថបទគំរូ</button>
              </div>
              <textarea
                id="ai-text"
                className="input-field"
                placeholder="បិទភ្ជាប់សាររបាយការណ៍នៅទីនេះ…"
                value={inputText}
                onChange={(e) => { setInputText(e.target.value); if (result) resetResult() }}
                style={{ height: '360px', fontSize: '0.875rem' }}
              />
            </div>
          ) : (
            <label className="dropzone">
              <input type="file" accept="image/*" onChange={onFile} />
              {imageData ? (
                <>
                  <img src={imageData} alt="រូបភាពដែលបានជ្រើស" style={{ maxHeight: '260px', maxWidth: '100%', borderRadius: 'var(--radius-md)', objectFit: 'contain' }} />
                  <span style={{ fontSize: '0.8rem', color: 'var(--accent-text)' }}>ចុចដើម្បីប្តូររូបភាព</span>
                </>
              ) : (
                <>
                  <UploadCloud size={32} color="var(--accent-text)" />
                  <span style={{ fontWeight: 600 }}>ចុច ឬអូសរូបភាពតារាងមកទីនេះ</span>
                  <span style={{ fontSize: '0.78rem', color: 'var(--text-dim)' }}>PNG, JPG</span>
                </>
              )}
              {caps && !caps.ocr && (
                <span className="badge badge-amber" style={{ marginTop: '6px' }}>ម៉ាស៊ីនស្កេនរូបភាពមិនទាន់ដំណើរការលើម៉ាស៊ីនមេនេះ</span>
              )}
            </label>
          )}

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', justifyContent: 'flex-end' }}>
            {caps?.llm && (
              <select className="input-field" style={{ width: 'auto' }} value={provider} onChange={(e) => setProvider(e.target.value)} aria-label="ម៉ាស៊ីនវិភាគ">
                <option value="auto">ស្វ័យប្រវត្តិ</option>
                <option value="builtin">ច្បាប់វិភាគមូលដ្ឋាន</option>
                <option value="llm">បញ្ញាសិប្បនិម្មិត</option>
              </select>
            )}
            <button onClick={analyze} disabled={parsing || !canAnalyze} className="btn btn-primary">
              {parsing ? <RefreshCw size={16} className="spin" /> : <Sparkles size={16} />}
              {parsing ? 'កំពុងវិភាគ…' : 'វិភាគ'}
            </button>
          </div>
        </section>

        {/* ── Result ── */}
        <section className="glass-panel" style={{ padding: '20px 22px', display: 'flex', flexDirection: 'column', gap: '16px', minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', gap: '12px' }}>
            <h2 className="chart-card-title">លទ្ធផល</h2>
            {extracted && (
              <span className="chart-card-sub">ភាពជឿជាក់ {Math.round(extracted.confidence * 100)}%</span>
            )}
          </div>

          {parsing ? (
            <div className="chart-empty"><RefreshCw size={20} className="spin" style={{ marginRight: 8 }} /> កំពុងវិភាគអត្ថបទ…</div>
          ) : parseError ? (
            <div role="alert" className="notice notice-rose"><AlertTriangle size={16} /> {parseError}</div>
          ) : !extracted ? (
            <div className="chart-empty">លទ្ធផលនឹងបង្ហាញនៅទីនេះ បន្ទាប់ពីចុច "វិភាគ"</div>
          ) : (
            <>
              <label className="input-group">
                <span className="input-label">កាលបរិច្ឆេទរបាយការណ៍</span>
                <input
                  type="date"
                  className="input-field"
                  style={{ width: 'auto', maxWidth: '220px', ...(dateMissing && !applyDate ? { borderColor: 'var(--amber-primary)' } : {}) }}
                  value={applyDate}
                  max={localISODate()}
                  onChange={(e) => setApplyDate(e.target.value)}
                  disabled={applied}
                />
                {dateMissing && (
                  <span style={{ fontSize: '0.78rem', color: 'var(--amber-primary)' }}>រកមិនឃើញកាលបរិច្ឆេទក្នុងអត្ថបទ — សូមជ្រើសរើស</span>
                )}
              </label>

              {extracted.warnings.filter((w) => !w.includes('កាលបរិច្ឆេទ') && !w.includes('តែឆ្នាំ')).length > 0 && (
                <ul className="notice notice-amber" style={{ listStyle: 'none', flexDirection: 'column', alignItems: 'stretch', gap: '4px' }}>
                  {extracted.warnings
                    .filter((w) => !w.includes('កាលបរិច្ឆេទ') && !w.includes('តែឆ្នាំ'))
                    .map((w, i) => (
                      <li key={i} style={{ display: 'flex', gap: '8px' }}>
                        <AlertTriangle size={14} style={{ flexShrink: 0, marginTop: 3 }} /> <span>{w}</span>
                      </li>
                    ))}
                </ul>
              )}

              {extracted.categories.length === 0 ? (
                <div className="chart-empty" style={{ minHeight: '120px' }}>រកមិនឃើញទិន្នន័យផ្នែកណាមួយក្នុងអត្ថបទនេះទេ</div>
              ) : (
                <div style={{ overflowX: 'auto', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-md)' }}>
                  <table className="result-table">
                    <thead>
                      <tr>
                        <th style={{ textAlign: 'left' }}>ផ្នែក</th>
                        <th>សិស្សថ្មី</th>
                        <th>ស្រី</th>
                        <th>ភ្នំពេញ</th>
                        <th>ខេត្ត</th>
                        <th style={{ textAlign: 'left' }}>និទ្ទេស</th>
                      </tr>
                    </thead>
                    <tbody>
                      {extracted.categories.map((c, i) => (
                        <tr key={`${c.category}-${i}`}>
                          <td style={{ textAlign: 'left', fontWeight: 600 }}>{catName(c.category, c.title)}</td>
                          <td style={{ fontWeight: 700 }}>{c.total}</td>
                          <td>{c.female}</td>
                          <td>{c.pp}</td>
                          <td>{c.kp}</td>
                          <td style={{ textAlign: 'left' }}>
                            {c.grades.filter((g) => g.total > 0).map((g) => (
                              <span key={g.grade} className="grade-pill" style={{ marginRight: 4 }}>
                                <span className="grade-pill-dot" style={{ background: `var(--grade-${g.grade})` }} />
                                {g.grade} <strong>{g.total}</strong>
                              </span>
                            ))}
                            {c.grades.every((g) => g.total === 0) && <span style={{ color: 'var(--text-dim)' }}>–</span>}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                    <tfoot>
                      <tr>
                        <th style={{ textAlign: 'left' }}>សរុប</th>
                        <td>{totals.total}</td>
                        <td>{totals.female}</td>
                        <td>{totals.pp}</td>
                        <td>{totals.kp}</td>
                        <td />
                      </tr>
                    </tfoot>
                  </table>
                </div>
              )}

              {applied ? (
                <div className="notice notice-emerald" style={{ justifyContent: 'space-between', flexWrap: 'wrap' }}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <CheckCircle2 size={16} /> បានរក្សាទុកទិន្នន័យថ្ងៃ {applyDate} រួចរាល់
                  </span>
                  {onNavigate && (
                    <span style={{ display: 'flex', gap: '8px' }}>
                      <button onClick={() => onNavigate('reports')} className="btn btn-secondary btn-sm">មើលប្រវត្តិ</button>
                      <button onClick={() => onNavigate('telegram', applyDate)} className="btn btn-secondary btn-sm">មើលសារ Telegram</button>
                    </span>
                  )}
                </div>
              ) : (
                <>
                  {applyError && <div role="alert" className="notice notice-rose"><AlertTriangle size={16} /> {applyError}</div>}
                  <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                    <button
                      onClick={save}
                      disabled={applying || !applyDate || extracted.categories.length === 0}
                      className="btn btn-primary"
                      title={!applyDate ? 'សូមជ្រើសរើសកាលបរិច្ឆេទជាមុនសិន' : undefined}
                    >
                      {applying ? <RefreshCw size={16} className="spin" /> : <Database size={16} />}
                      {applying ? 'កំពុងរក្សាទុក…' : 'រក្សាទុកទៅក្នុងប្រព័ន្ធ'}
                    </button>
                  </div>
                </>
              )}
            </>
          )}
        </section>
      </div>
    </div>
  )
}
