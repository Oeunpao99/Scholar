import React, { useEffect, useState } from 'react'
import { Save, CheckCircle2, AlertCircle, RefreshCw, Sun, Moon, Pencil, X, Check } from 'lucide-react'
import { api } from '../lib/api'
import { formatRoman } from '../lib/format'
import { Category, Grade } from '../types'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'
import { Segmented } from '../components/ui/Segmented'

// Meaning of each BacII grade (the seeded DB labels are misspelt, so the page
// always shows "និទ្ទេស X" plus this description instead).
const GRADE_MEANING: Record<string, string> = {
  A: 'ឆ្នើម',
  B: 'ល្អណាស់',
  C: 'ល្អ',
  D: 'មធ្យម',
  E: 'ជាប់កម្រិតមូលដ្ឋាន',
}

type Feedback = { type: 'success' | 'error'; text: string } | null

export const SettingsPage: React.FC = () => {
  const { user } = useAuth()
  const { theme, setTheme } = useTheme()
  const isAdmin = user?.role === 'superadmin' || user?.role === 'admin'

  const [savedYear, setSavedYear] = useState<number>(2026)
  const [yearInput, setYearInput] = useState<string>('2026')
  const [savingYear, setSavingYear] = useState(false)

  const [categories, setCategories] = useState<Category[]>([])
  const [grades, setGrades] = useState<Grade[]>([])
  const [editing, setEditing] = useState<{ id: string; template: string } | null>(null)
  const [savingTemplate, setSavingTemplate] = useState(false)

  const [health, setHealth] = useState<{ api: boolean; db: boolean } | null>(null)
  const [healthLoading, setHealthLoading] = useState(false)

  const [feedback, setFeedback] = useState<Feedback>(null)

  const loadData = async () => {
    try {
      const [yearRes, catRes, gradeRes] = await Promise.all([api.getCurrentYear(), api.getCategories(), api.getGrades()])
      setSavedYear(yearRes.current_year)
      setYearInput(String(yearRes.current_year))
      setCategories(catRes.items)
      setGrades(gradeRes.items)
    } catch (err) {
      console.error('Error loading settings', err)
    }
  }

  const checkHealth = async () => {
    setHealthLoading(true)
    try {
      const res = await api.getHealth()
      // The API answers "ok" (older builds said "healthy") — a response at all means it is up.
      setHealth({ api: ['ok', 'healthy'].includes(res.status), db: res.database })
    } catch {
      setHealth({ api: false, db: false })
    } finally {
      setHealthLoading(false)
    }
  }

  useEffect(() => {
    loadData()
    checkHealth()
  }, [])

  const yearNumber = Number(yearInput)
  const yearValid = Number.isInteger(yearNumber) && yearNumber >= 2000 && yearNumber <= 2100
  const yearChanged = yearValid && yearNumber !== savedYear

  const saveYear = async () => {
    if (!isAdmin || !yearChanged) return
    setSavingYear(true)
    setFeedback(null)
    try {
      await api.setCurrentYear(yearNumber)
      setFeedback({ type: 'success', text: `បានប្តូរឆ្នាំសិក្សាទៅ ${yearNumber} — ចំណងជើងផ្នែកត្រូវបានធ្វើបច្ចុប្បន្នភាព` })
      await loadData()
    } catch (err: any) {
      setFeedback({ type: 'error', text: `បរាជ័យក្នុងការប្តូរឆ្នាំសិក្សា: ${err.message}` })
    } finally {
      setSavingYear(false)
    }
  }

  const saveTemplate = async () => {
    if (!editing || !isAdmin) return
    setSavingTemplate(true)
    setFeedback(null)
    try {
      await api.updateCategoryTitle(editing.id, editing.template)
      setEditing(null)
      setFeedback({ type: 'success', text: 'បានរក្សាទុកចំណងជើងផ្នែក' })
      await loadData()
    } catch (err: any) {
      setFeedback({ type: 'error', text: `បរាជ័យក្នុងការកែចំណងជើងផ្នែក: ${err.message}` })
    } finally {
      setSavingTemplate(false)
    }
  }

  // Preview of a template as it will read with the chosen year.
  const renderTemplate = (template: string) => template.replace(/\{year\}/g, String(yearValid ? yearNumber : savedYear))

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div className="page-header">
        <div>
          <h1 className="page-title">ការកំណត់</h1>
          <p className="page-subtitle">រូបរាងកម្មវិធី ឆ្នាំសិក្សា ចំណងជើងផ្នែក និងស្ថានភាពប្រព័ន្ធ</p>
        </div>
      </div>

      {feedback && (
        <div role="status" className={`notice ${feedback.type === 'success' ? 'notice-emerald' : 'notice-rose'}`}>
          {feedback.type === 'success' ? <CheckCircle2 size={16} /> : <AlertCircle size={16} />}
          <span style={{ flex: 1 }}>{feedback.text}</span>
          <button className="btn btn-ghost" style={{ padding: 2 }} onClick={() => setFeedback(null)} aria-label="បិទ"><X size={14} /></button>
        </div>
      )}

      <section className="glass-panel settings-list">
        {/* Appearance */}
        <div className="settings-row">
          <div className="settings-row-text">
            <h2>រូបរាង</h2>
            <p>ផ្ទៃពន្លឺសម្រាប់ពេលថ្ងៃ ឬផ្ទៃងងឹតស្រទន់ភ្នែក</p>
          </div>
          <Segmented
            ariaLabel="រូបរាង"
            className="theme-toggle"
            value={theme}
            onChange={(v) => setTheme(v as 'light' | 'dark')}
            options={[
              { value: 'light', label: <><Sun size={15} /> ពន្លឺ</> },
              { value: 'dark', label: <><Moon size={15} /> ងងឹត</> },
            ]}
          />
        </div>

        {/* Academic year */}
        <div className="settings-row">
          <div className="settings-row-text">
            <h2>ឆ្នាំសិក្សាបាក់ឌុប</h2>
            <p>ឆ្នាំនេះប្រើក្នុងចំណងជើងផ្នែក I និង II (ឧ. «ឆ្នាំ{savedYear}» និង «មុនឆ្នាំ{savedYear}»)</p>
            {!isAdmin && <p style={{ color: 'var(--text-dim)' }}>មានតែអ្នករៀបចំប្រព័ន្ធប៉ុណ្ណោះដែលអាចប្តូរបាន</p>}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <input
              type="number"
              className="input-field"
              style={{ width: '110px', fontWeight: 700, fontSize: '1rem' }}
              value={yearInput}
              min={2000}
              max={2100}
              disabled={!isAdmin}
              onChange={(e) => setYearInput(e.target.value)}
              aria-label="ឆ្នាំសិក្សា"
            />
            {isAdmin && (
              <button onClick={saveYear} disabled={!yearChanged || savingYear} className="btn btn-primary">
                {savingYear ? <RefreshCw size={15} className="spin" /> : <Save size={15} />}
                រក្សាទុក
              </button>
            )}
          </div>
        </div>

        {/* Category titles */}
        <div className="settings-row settings-row-stack">
          <div className="settings-row-text">
            <h2>ចំណងជើងផ្នែកសិស្ស</h2>
            <p>ចំណងជើងទាំងនេះបង្ហាញក្នុងរបាយការណ៍ និងសារ Telegram។ សរសេរ {'{year}'} ដើម្បីដាក់ឆ្នាំសិក្សាដោយស្វ័យប្រវត្តិ</p>
          </div>
          <ul className="settings-sublist">
            {categories.map((c) => {
              const isEditing = editing?.id === c.id
              return (
                <li key={c.id}>
                  <span className="settings-roman">{formatRoman(c.roman_numeral)}</span>
                  {isEditing ? (
                    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '4px' }}>
                      <div style={{ display: 'flex', gap: '6px' }}>
                        <input
                          autoFocus
                          className="input-field"
                          value={editing.template}
                          onChange={(e) => setEditing({ id: c.id, template: e.target.value })}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') saveTemplate()
                            if (e.key === 'Escape') setEditing(null)
                          }}
                        />
                        <button onClick={saveTemplate} disabled={savingTemplate || !editing.template.trim()} className="btn btn-primary btn-sm" aria-label="រក្សាទុក">
                          <Check size={15} />
                        </button>
                        <button onClick={() => setEditing(null)} className="btn btn-secondary btn-sm" aria-label="បោះបង់">
                          <X size={15} />
                        </button>
                      </div>
                      <span style={{ fontSize: '0.78rem', color: 'var(--text-dim)' }}>
                        នឹងបង្ហាញជា: <strong style={{ color: 'var(--text-main)' }}>{renderTemplate(editing.template)}</strong>
                      </span>
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)', display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
                        <code style={{ padding: '0 5px', borderRadius: 4, background: 'var(--bg-subtle)' }}>{'{year}'}</code>
                        ប្តូរជាឆ្នាំសិក្សា ({savedYear}) ដោយស្វ័យប្រវត្តិ
                        {!editing.template.includes('{year}') && (
                          <button type="button" className="link-button" style={{ fontSize: '0.75rem' }}
                            onClick={() => setEditing({ ...editing, template: `${editing.template}{year}` })}>
                            + បញ្ចូល {'{year}'}
                          </button>
                        )}
                      </span>
                    </div>
                  ) : (
                    <>
                      <span style={{ flex: 1, fontWeight: 600 }}>{c.title}</span>
                      {isAdmin && (
                        <button onClick={() => setEditing({ id: c.id, template: c.title_template })} className="btn btn-ghost" aria-label={`កែ ${c.title}`} title="កែ">
                          <Pencil size={15} />
                        </button>
                      )}
                    </>
                  )}
                </li>
              )
            })}
          </ul>
        </div>

        {/* Grades (reference) */}
        <div className="settings-row settings-row-stack">
          <div className="settings-row-text">
            <h2>និទ្ទេសបាក់ឌុប</h2>
            <p>កម្រិតនិទ្ទេសដែលប្រើក្នុងការបញ្ចូលទិន្នន័យ</p>
          </div>
          <div className="grade-scale">
            {(grades.length ? grades.map((g) => g.code) : Object.keys(GRADE_MEANING)).map((code) => (
              <div key={code} className="grade-scale-item">
                <span className="grade-scale-letter" style={{ background: `var(--grade-${code})`, color: `var(--grade-${code}-ink)` }}>{code}</span>
                <span className="grade-scale-name">និទ្ទេស {code}</span>
                <span className="grade-scale-meaning">{GRADE_MEANING[code] || ''}</span>
              </div>
            ))}
          </div>
        </div>

        {/* System status */}
        <div className="settings-row">
          <div className="settings-row-text">
            <h2>ស្ថានភាពប្រព័ន្ធ</h2>
            <p>ពិនិត្យថាម៉ាស៊ីនមេ និងមូលដ្ឋានទិន្នន័យកំពុងដំណើរការ</p>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '18px', flexWrap: 'wrap' }}>
            <StatusDot ok={health?.api} label="ម៉ាស៊ីនមេ" />
            <StatusDot ok={health?.db} label="មូលដ្ឋានទិន្នន័យ" />
            <button onClick={checkHealth} className="btn btn-ghost" aria-label="ពិនិត្យឡើងវិញ" title="ពិនិត្យឡើងវិញ">
              <RefreshCw size={15} className={healthLoading ? 'spin' : ''} />
            </button>
          </div>
        </div>
      </section>
    </div>
  )
}

const StatusDot: React.FC<{ ok?: boolean; label: string }> = ({ ok, label }) => (
  <span style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.875rem' }}>
    <span style={{
      width: '8px',
      height: '8px',
      borderRadius: '50%',
      background: ok === undefined ? 'var(--border-strong)' : ok ? 'var(--emerald-primary)' : 'var(--rose-primary)',
    }} />
    <span style={{ color: 'var(--text-muted)' }}>{label}</span>
    <strong style={{ color: ok === undefined ? 'var(--text-dim)' : ok ? 'var(--emerald-primary)' : 'var(--rose-primary)' }}>
      {ok === undefined ? '…' : ok ? 'ដំណើរការ' : 'មានបញ្ហា'}
    </strong>
  </span>
)
