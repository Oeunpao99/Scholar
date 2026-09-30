import React, { useEffect, useState } from 'react'
import { Send, Copy, Check, AlertCircle, RefreshCw, CheckCircle2 } from 'lucide-react'
import { api } from '../lib/api'
import { TelegramMessage } from '../types'
import { DatePicker } from '../components/ui/DatePicker'

interface TelegramCenterPageProps {
  initialDate?: string
  onNavigate?: (tab: string, dateParam?: string) => void
}

interface BotStatus {
  ok: boolean
  configured?: boolean
  username?: string
}

export const TelegramCenterPage: React.FC<TelegramCenterPageProps> = ({ initialDate, onNavigate }) => {
  const [reportDate, setReportDate] = useState<string>(
    initialDate || new Date().toISOString().split('T')[0]
  )

  // Message options
  const [includeGrandTotal, setIncludeGrandTotal] = useState<boolean>(true)
  const [includeEmptyCategories, setIncludeEmptyCategories] = useState<boolean>(true)
  const [includeTodayGrades, setIncludeTodayGrades] = useState<boolean>(true)
  const [zeroPad, setZeroPad] = useState<boolean>(false)
  // Empty = every grade; otherwise the report (lines and totals) covers only these.
  const [grades, setGrades] = useState<string[]>([])

  const toggleGrade = (g: string) =>
    setGrades((prev) => (prev.includes(g) ? prev.filter((x) => x !== g) : [...prev, g]))

  // Preview
  const [message, setMessage] = useState<TelegramMessage | null>(null)
  const [loading, setLoading] = useState<boolean>(true)
  const [copied, setCopied] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)

  // Bot + sending
  const [botStatus, setBotStatus] = useState<BotStatus | null>(null)
  const [botChecking, setBotChecking] = useState<boolean>(false)
  const [chatId, setChatId] = useState<string>('')
  const [isDryRun, setIsDryRun] = useState<boolean>(false)
  const [sending, setSending] = useState<boolean>(false)
  const [sendResult, setSendResult] = useState<{ ok: boolean; msg: string } | null>(null)

  const fetchPreview = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await api.getTelegramPreview({
        date: reportDate,
        include_grand_total: includeGrandTotal,
        include_empty_categories: includeEmptyCategories,
        include_today_grades: includeTodayGrades,
        zero_pad: zeroPad,
        grades,
      })
      setMessage(res)
    } catch (err: any) {
      setError(err.message || 'បរាជ័យក្នុងការបង្កើតសារ Telegram')
    } finally {
      setLoading(false)
    }
  }

  const checkBot = async () => {
    setBotChecking(true)
    try {
      setBotStatus(await api.verifyTelegramBot())
    } catch {
      setBotStatus({ ok: false })
    } finally {
      setBotChecking(false)
    }
  }

  useEffect(() => {
    fetchPreview()
  }, [reportDate, includeGrandTotal, includeEmptyCategories, includeTodayGrades, zeroPad, grades])

  useEffect(() => {
    checkBot()
  }, [])

  const handleCopy = () => {
    if (!message?.text) return
    navigator.clipboard.writeText(message.text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleBroadcast = async () => {
    setSending(true)
    setSendResult(null)
    try {
      const res = await api.sendTelegram({
        report_date: reportDate,
        chat_id: chatId || undefined,
        dry_run: isDryRun,
        include_today_grades: includeTodayGrades,
        include_grand_total: includeGrandTotal,
        include_empty_categories: includeEmptyCategories,
        zero_pad: zeroPad,
        grades,
      })
      setSendResult({
        ok: true,
        msg: isDryRun
          ? 'ការធ្វើតេស្តបានផ្ទៀងផ្ទាត់សាររួចរាល់'
          : `បានផ្ញើទៅកាន់ Telegram ${res.chat_id || ''} រួចរាល់`,
      })
    } catch (err: any) {
      setSendResult({ ok: false, msg: `បរាជ័យក្នុងការផ្ញើ: ${err.message}` })
    } finally {
      setSending(false)
    }
  }

  const botLabel = botStatus?.ok
    ? `@${botStatus.username || 'bot'}`
    : botStatus?.configured === false
      ? 'មិនទាន់កំណត់បូត'
      : 'បូតមិនដំណើរការ'

  const options: Array<{ label: string; checked: boolean; set: (v: boolean) => void }> = [
    { label: 'រួមបញ្ចូលសរុបរួម', checked: includeGrandTotal, set: setIncludeGrandTotal },
    { label: 'បង្ហាញគ្រប់ផ្នែក (ទោះពុំមានកើន)', checked: includeEmptyCategories, set: setIncludeEmptyCategories },
    { label: 'បំបែកតាមនិទ្ទេស A-E ថ្ងៃនេះ', checked: includeTodayGrades, set: setIncludeTodayGrades },
    { label: 'បន្ថែមលេខសូន្យខាងមុខ (01, 02…)', checked: zeroPad, set: setZeroPad },
  ]

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <div className="page-header">
        <div>
          <h1 className="page-title">របាយការណ៍ Telegram</h1>
          <p className="page-subtitle">បង្កើតសារផ្លូវការជាភាសាខ្មែរ ហើយផ្ញើទៅកាន់គ្រុប ឬឆានែល Telegram</p>
        </div>
        <div className="page-actions" style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
          <span style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            background: botStatus?.ok ? 'var(--emerald-primary)' : 'var(--amber-primary)',
          }} />
          {botLabel}
          <button onClick={checkBot} className="btn btn-ghost" title="ពិនិត្យស្ថានភាពបូតឡើងវិញ" aria-label="ពិនិត្យស្ថានភាពបូតឡើងវិញ">
            <RefreshCw size={15} className={botChecking ? 'spin' : ''} />
          </button>
        </div>
      </div>

      <div className="glass-panel split-panel">
        {/* ── Left: settings + send ── */}
        <aside className="split-panel-side">
          <section>
            <h2 className="section-title">កាលបរិច្ឆេទរបាយការណ៍</h2>
            <DatePicker ariaLabel="កាលបរិច្ឆេទរបាយការណ៍" value={reportDate} onChange={setReportDate} />
          </section>

          <section>
            <h2 className="section-title">ទម្រង់សារ</h2>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {options.map((opt) => (
                <label key={opt.label} className="check-row">
                  <input type="checkbox" checked={opt.checked} onChange={(e) => opt.set(e.target.checked)} />
                  <span>{opt.label}</span>
                </label>
              ))}
            </div>
          </section>

          <section>
            <h2 className="section-title">ច្រោះតាមនិទ្ទេស</h2>
            <div className="grade-filter" role="group" aria-label="ច្រោះតាមនិទ្ទេស">
              <button
                type="button"
                className={`grade-filter-btn ${grades.length === 0 ? 'active' : ''}`}
                aria-pressed={grades.length === 0}
                onClick={() => setGrades([])}
              >
                ទាំងអស់
              </button>
              {['A', 'B', 'C', 'D', 'E'].map((g) => (
                <button
                  key={g}
                  type="button"
                  className={`grade-filter-btn ${grades.includes(g) ? 'active' : ''}`}
                  aria-pressed={grades.includes(g)}
                  onClick={() => toggleGrade(g)}
                >
                  <span className="grade-pill-dot" style={{ background: `var(--grade-${g})` }} />
                  {g}
                </button>
              ))}
            </div>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '8px' }}>
              {grades.length === 0
                ? 'បង្ហាញគ្រប់និទ្ទេស'
                : 'ចំនួនសរុបក្នុងសារ គិតតែនិទ្ទេសដែលបានជ្រើសប៉ុណ្ណោះ'}
            </p>
          </section>

          <section>
            <h2 className="section-title">ផ្ញើទៅកាន់ Telegram</h2>
            <div className="input-group" style={{ marginBottom: '12px' }}>
              <label className="input-label" htmlFor="tg-chat">គ្រុប ឬឆានែល (ទុកទំនេរ = លំនាំដើម)</label>
              <input
                id="tg-chat"
                type="text"
                className="input-field"
                placeholder="@my_channel ឬ -10012345678"
                value={chatId}
                onChange={(e) => setChatId(e.target.value)}
              />
            </div>

            <label className="check-row" style={{ marginBottom: '14px' }}>
              <input type="checkbox" checked={isDryRun} onChange={(e) => setIsDryRun(e.target.checked)} />
              <span>ធ្វើតេស្តប៉ុណ្ណោះ (មិនផ្ញើពិតប្រាកដ)</span>
            </label>

            {sendResult && (
              <div className={`badge ${sendResult.ok ? 'badge-emerald' : 'badge-rose'}`} style={{ whiteSpace: 'normal', borderRadius: 'var(--radius-md)', padding: '8px 12px', marginBottom: '12px', width: '100%' }}>
                {sendResult.ok ? <CheckCircle2 size={14} /> : <AlertCircle size={14} />}
                <span>{sendResult.msg}</span>
              </div>
            )}

            <button
              onClick={handleBroadcast}
              disabled={sending || loading || !message?.text}
              className="btn btn-primary"
              style={{ width: '100%' }}
            >
              <Send size={15} />
              {sending ? 'កំពុងផ្ញើ...' : isDryRun ? 'ធ្វើតេស្ត' : 'ផ្ញើឥឡូវនេះ'}
            </button>
          </section>
        </aside>

        {/* ── Right: live preview ── */}
        <div className="split-panel-main">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px', marginBottom: '16px' }}>
            <div>
              <h2 className="section-title" style={{ margin: 0 }}>ទិដ្ឋភាពសារ</h2>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-dim)' }}>ធ្វើបច្ចុប្បន្នភាពដោយស្វ័យប្រវត្តិ</div>
            </div>
            <div style={{ display: 'flex', gap: '6px' }}>
              <button onClick={fetchPreview} className="btn btn-ghost" title="បង្កើតសារឡើងវិញ" aria-label="បង្កើតសារឡើងវិញ">
                <RefreshCw size={16} className={loading ? 'spin' : ''} />
              </button>
              <button onClick={handleCopy} disabled={!message?.text} className="btn btn-secondary btn-sm">
                {copied ? <Check size={15} /> : <Copy size={15} />}
                {copied ? 'បានចម្លង' : 'ចម្លងសារ'}
              </button>
            </div>
          </div>

          {error ? (
            <div style={{ padding: '60px 20px', textAlign: 'center' }}>
              <AlertCircle size={28} color="var(--rose-primary)" style={{ margin: '0 auto 10px', display: 'block' }} />
              <div style={{ fontWeight: 600 }}>ពុំមានទិន្នន័យសម្រាប់កាលបរិច្ឆេទនេះឡើយ</div>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '4px' }}>{error}</p>
              {onNavigate && (
                <button onClick={() => onNavigate('daily-entry', reportDate)} className="btn btn-primary btn-sm" style={{ marginTop: '14px' }}>
                  បញ្ចូលទិន្នន័យថ្ងៃ {reportDate}
                </button>
              )}
            </div>
          ) : (
            <pre className="message-preview" style={{ opacity: loading ? 0.5 : 1 }}>
              {message?.text || (loading ? 'កំពុងបង្កើតសារ...' : 'ជ្រើសរើសកាលបរិច្ឆេទដើម្បីមើលសារ')}
            </pre>
          )}
        </div>
      </div>
    </div>
  )
}
