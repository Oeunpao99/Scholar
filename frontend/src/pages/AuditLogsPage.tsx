import React, { useEffect, useState } from 'react'
import { ShieldAlert, Search, RefreshCw, ChevronLeft, ChevronRight, ChevronRight as RowChevron, X, Code } from 'lucide-react'
import { api } from '../lib/api'
import {
  ACTION_META,
  ENTITY_LABELS,
  actionMeta,
  changeRows,
  entityLabel,
  formatValue,
  khDateTime,
  khmerSummary,
} from '../lib/auditFormat'
import { AuditLogItem, PaginatedResponse } from '../types'
import { useAuth } from '../context/AuthContext'

const EMPTY: PaginatedResponse<AuditLogItem> = {
  items: [],
  meta: { page: 1, size: 20, total: 0, total_pages: 1, has_next: false, has_prev: false },
}

const ActionBadge: React.FC<{ action: string }> = ({ action }) => {
  const meta = actionMeta(action)
  return <span className={`badge badge-${meta.tone}`}>{meta.label}</span>
}

export const AuditLogsPage: React.FC = () => {
  const { user } = useAuth()
  const isAdmin = user?.role === 'superadmin' || user?.role === 'admin'

  const [page, setPage] = useState(1)
  const [action, setAction] = useState('')
  const [entityType, setEntityType] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')

  const [logs, setLogs] = useState<PaginatedResponse<AuditLogItem>>(EMPTY)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selected, setSelected] = useState<AuditLogItem | null>(null)

  // Search as you type (debounced) — no separate filter button needed.
  useEffect(() => {
    const t = setTimeout(() => { setSearch(searchInput.trim()); setPage(1) }, 350)
    return () => clearTimeout(t)
  }, [searchInput])

  const fetchLogs = async () => {
    setLoading(true)
    setError(null)
    try {
      setLogs(await api.getAuditLogs({ page, size: 20, action: action || undefined, entity_type: entityType || undefined, q: search || undefined }))
    } catch (err: any) {
      setError(err.message || 'បរាជ័យក្នុងការផ្ទុកកំណត់ហេតុ')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (isAdmin) fetchLogs()
  }, [page, action, entityType, search, isAdmin])

  useEffect(() => {
    if (!selected) return
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setSelected(null)
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [selected])

  if (!isAdmin) {
    return (
      <div className="glass-panel" style={{ padding: '48px 20px', textAlign: 'center', maxWidth: '480px', margin: '40px auto' }}>
        <ShieldAlert size={40} color="var(--rose-primary)" style={{ margin: '0 auto 12px', display: 'block' }} />
        <h2 style={{ fontSize: '1.1rem' }}>ពុំមានសិទ្ធិចូលមើលទំព័រនេះឡើយ</h2>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginTop: '6px' }}>
          កំណត់ហេតុសវនកម្មសម្រាប់តែអ្នករៀបចំប្រព័ន្ធ និងអ្នកគ្រប់គ្រងជាន់ខ្ពស់ប៉ុណ្ណោះ។
        </p>
      </div>
    )
  }

  const hasFilters = !!(action || entityType || searchInput)
  const clearFilters = () => {
    setAction('')
    setEntityType('')
    setSearchInput('')
    setPage(1)
  }

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <div className="page-header">
        <div>
          <h1 className="page-title">កំណត់ហេតុសវនកម្ម</h1>
          <p className="page-subtitle">ប្រវត្តិរាល់សកម្មភាព — អ្នកណា ធ្វើអ្វី និងនៅពេលណា</p>
        </div>
        <button onClick={fetchLogs} className="btn btn-secondary btn-sm" disabled={loading}>
          <RefreshCw size={14} className={loading ? 'spin' : ''} /> ផ្ទុកឡើងវិញ
        </button>
      </div>

      {/* Filters — one plain row */}
      <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', alignItems: 'center' }}>
        <div style={{ position: 'relative', flex: '1 1 260px', maxWidth: '380px' }}>
          <Search size={15} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-dim)' }} />
          <input
            type="search"
            className="input-field"
            placeholder="ស្វែងរកអ្នកប្រើ ឬសេចក្តីលម្អិត…"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            style={{ paddingLeft: '36px' }}
            aria-label="ស្វែងរក"
          />
        </div>
        <select className="input-field" style={{ width: 'auto' }} value={action} onChange={(e) => { setAction(e.target.value); setPage(1) }} aria-label="សកម្មភាព">
          <option value="">សកម្មភាពទាំងអស់</option>
          {Object.entries(ACTION_META).map(([value, m]) => <option key={value} value={value}>{m.label}</option>)}
        </select>
        <select className="input-field" style={{ width: 'auto' }} value={entityType} onChange={(e) => { setEntityType(e.target.value); setPage(1) }} aria-label="ប្រភេទ">
          <option value="">គ្រប់ប្រភេទ</option>
          {Object.entries(ENTITY_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select>
        {hasFilters && <button onClick={clearFilters} className="link-button">សម្អាតតម្រង</button>}
      </div>

      <section className="glass-panel" style={{ overflow: 'hidden' }}>
        {error ? (
          <div className="chart-empty" style={{ color: 'var(--rose-primary)' }}>{error}</div>
        ) : loading && logs.items.length === 0 ? (
          <div className="chart-empty"><RefreshCw size={18} className="spin" style={{ marginRight: 8 }} /> កំពុងផ្ទុក…</div>
        ) : logs.items.length === 0 ? (
          <div className="chart-empty">ពុំមានកំណត់ហេតុត្រូវនឹងតម្រងនេះទេ</div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table className="audit-table">
              <thead>
                <tr>
                  <th style={{ width: '170px' }}>ពេលវេលា</th>
                  <th style={{ width: '220px' }}>អ្នកប្រើប្រាស់</th>
                  <th style={{ width: '130px' }}>សកម្មភាព</th>
                  <th>សេចក្តីលម្អិត</th>
                  <th style={{ width: '32px' }} aria-label="បើក" />
                </tr>
              </thead>
              <tbody>
                {logs.items.map((log) => (
                  <tr
                    key={log.id}
                    onClick={() => setSelected(log)}
                    onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && (e.preventDefault(), setSelected(log))}
                    tabIndex={0}
                    role="button"
                    aria-label={`មើលលម្អិត: ${khmerSummary(log.summary)}`}
                  >
                    <td className="audit-time">{khDateTime(log.created_at)}</td>
                    <td>
                      <div className="audit-user">{log.user_email || 'ប្រព័ន្ធ'}</div>
                    </td>
                    <td><ActionBadge action={log.action} /></td>
                    <td>
                      <div className="audit-summary">{khmerSummary(log.summary)}</div>
                      <div className="audit-entity">{entityLabel(log.entity_type)}</div>
                    </td>
                    <td><RowChevron size={16} color="var(--text-dim)" /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {logs.meta && logs.items.length > 0 && (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 18px', borderTop: '1px solid var(--border-subtle)', flexWrap: 'wrap', gap: '10px' }}>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              ទំព័រ {logs.meta.page} នៃ {logs.meta.total_pages || 1} · សរុប {logs.meta.total} កំណត់ហេតុ
            </span>
            <div style={{ display: 'flex', gap: '6px' }}>
              <button disabled={!logs.meta.has_prev} onClick={() => setPage((p) => Math.max(1, p - 1))} className="btn btn-secondary btn-sm">
                <ChevronLeft size={15} /> ថយក្រោយ
              </button>
              <button disabled={!logs.meta.has_next} onClick={() => setPage((p) => p + 1)} className="btn btn-secondary btn-sm">
                ទៅមុខ <ChevronRight size={15} />
              </button>
            </div>
          </div>
        )}
      </section>

      {/* Detail */}
      {selected && (
        <div className="modal-backdrop" onClick={() => setSelected(null)}>
          <div
            className="glass-panel"
            role="dialog"
            aria-modal="true"
            aria-labelledby="audit-detail-title"
            onClick={(e) => e.stopPropagation()}
            style={{ maxWidth: '680px', width: '100%', maxHeight: '86vh', overflowY: 'auto', padding: '22px 24px', boxShadow: 'var(--shadow-lg)' }}
          >
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '12px', marginBottom: '16px' }}>
              <div>
                <ActionBadge action={selected.action} />
                <h2 id="audit-detail-title" style={{ fontSize: '1.05rem', marginTop: '8px', lineHeight: 1.5 }}>{khmerSummary(selected.summary)}</h2>
              </div>
              <button onClick={() => setSelected(null)} className="btn btn-ghost" aria-label="បិទ"><X size={18} /></button>
            </div>

            <dl className="audit-meta">
              <div><dt>ពេលវេលា</dt><dd>{khDateTime(selected.created_at)}</dd></div>
              <div><dt>អ្នកប្រើប្រាស់</dt><dd>{selected.user_email || 'ប្រព័ន្ធ'}</dd></div>
              <div><dt>ប្រភេទ</dt><dd>{entityLabel(selected.entity_type)}</dd></div>
              <div><dt>អាសយដ្ឋាន IP</dt><dd>{selected.ip_address || '–'}</dd></div>
            </dl>

            {selected.changes && (() => {
              const rows = changeRows(selected.changes)
              return (
                <div style={{ marginTop: '18px' }}>
                  <h3 style={{ fontSize: '0.875rem', marginBottom: '8px' }}>{rows ? 'អ្វីដែលបានផ្លាស់ប្តូរ' : 'ព័ត៌មានលម្អិត'}</h3>
                  {rows ? (
                    <div style={{ border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-md)', overflow: 'hidden' }}>
                      <table className="result-table" style={{ fontSize: '0.85rem' }}>
                        <thead>
                          <tr>
                            <th style={{ textAlign: 'left', width: '28%' }}>ព័ត៌មាន</th>
                            <th style={{ textAlign: 'left' }}>មុនពេលកែ</th>
                            <th style={{ textAlign: 'left' }}>ក្រោយពេលកែ</th>
                          </tr>
                        </thead>
                        <tbody>
                          {rows.map((r) => (
                            <tr key={r.field} style={{ opacity: r.changed ? 1 : 0.6 }}>
                              <td style={{ textAlign: 'left', fontWeight: 600, verticalAlign: 'top' }}>{r.field}</td>
                              <td style={{ textAlign: 'left', whiteSpace: 'pre-line', color: 'var(--text-muted)', verticalAlign: 'top' }}>{r.before}</td>
                              <td style={{ textAlign: 'left', whiteSpace: 'pre-line', fontWeight: r.changed ? 600 : 400, verticalAlign: 'top' }}>
                                {r.changed ? r.after : 'មិនប្រែប្រួល'}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <div style={{ background: 'var(--bg-subtle)', padding: '10px 14px', borderRadius: 'var(--radius-md)', fontSize: '0.85rem', whiteSpace: 'pre-line' }}>
                      {formatValue(selected.changes)}
                    </div>
                  )}
                  <details style={{ marginTop: '12px' }}>
                    <summary style={{ fontSize: '0.78rem', color: 'var(--text-dim)', cursor: 'pointer' }}>
                      <Code size={12} style={{ verticalAlign: '-2px', marginRight: 4 }} />
                      មើលទិន្នន័យដើម (សម្រាប់អ្នកបច្ចេកទេស)
                    </summary>
                    <pre style={{ marginTop: '8px', background: 'var(--code-bg)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-md)', padding: '12px', fontSize: '0.75rem', color: 'var(--text-muted)', overflowX: 'auto', maxHeight: '220px' }}>
                      {JSON.stringify(selected.changes, null, 2)}
                    </pre>
                  </details>
                </div>
              )
            })()}
          </div>
        </div>
      )}
    </div>
  )
}
