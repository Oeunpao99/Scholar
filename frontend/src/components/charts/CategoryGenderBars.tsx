import React, { useState } from 'react'

export interface CategoryGain {
  id: string
  roman: string
  title: string
  total: number
  female: number
  pp: number
  kp: number
}

interface Props {
  rows: CategoryGain[]
  selectedId?: string
  onSelect?: (id: string) => void
}

const pct = (part: number, whole: number) => (whole > 0 ? Math.round((part / whole) * 100) : 0)

/** New students per category, each bar split girls | boys and scaled to the largest category. */
export const CategoryGenderBars: React.FC<Props> = ({ rows, selectedId, onSelect }) => {
  const [hover, setHover] = useState<string | null>(null)
  const max = Math.max(1, ...rows.map((r) => r.total))
  const sum = rows.reduce((s, r) => s + r.total, 0)

  if (rows.length === 0) return <div className="chart-empty">មិនទាន់មានផ្នែកសិស្ស</div>

  const toggle = (id: string) => onSelect?.(selectedId === id ? '' : id)

  return (
    <div className="cg-chart">
      <ul className="cg-legend" aria-hidden="true">
        <li><span className="legend-swatch" style={{ background: 'var(--gender-f)' }} />ស្រី</li>
        <li><span className="legend-swatch" style={{ background: 'var(--gender-m)' }} />ប្រុស</li>
      </ul>
      <ol className="cg-rows">
        {rows.map((r) => {
          const male = r.total - r.female
          const dim = (hover !== null && hover !== r.id) || (!!selectedId && selectedId !== r.id)
          return (
            <li
              key={r.id}
              className={`cg-row ${dim ? 'dim' : ''} ${onSelect ? 'clickable' : ''}`}
              onMouseEnter={() => setHover(r.id)}
              onMouseLeave={() => setHover(null)}
              onClick={() => toggle(r.id)}
              tabIndex={onSelect ? 0 : undefined}
              onKeyDown={(e) => e.key === 'Enter' && toggle(r.id)}
              aria-pressed={onSelect ? selectedId === r.id : undefined}
              aria-label={`${r.roman} ${r.title}: ${r.total} នាក់, ស្រី ${r.female}, ប្រុស ${male}`}
            >
              <div className="cg-head">
                <span className="badge badge-blue cg-roman">{r.roman}</span>
                <span className="cg-title">{r.title}</span>
                <span className="cg-value">{r.total}</span>
                <span className="cg-pct">{pct(r.total, sum)}%</span>
              </div>
              <div className="cg-track">
                {r.total > 0 ? (
                  <div className="cg-bar" style={{ width: `${(r.total / max) * 100}%` }}>
                    {r.female > 0 && <span className="cg-seg" style={{ flexGrow: r.female, background: 'var(--gender-f)' }} />}
                    {male > 0 && <span className="cg-seg" style={{ flexGrow: male, background: 'var(--gender-m)' }} />}
                  </div>
                ) : (
                  <span className="cg-zero">គ្មានសិស្សថ្មី</span>
                )}
              </div>
              {hover === r.id && r.total > 0 && (
                <div className="chart-tooltip cg-tip" role="tooltip">
                  <div className="chart-tooltip-title">{r.roman} {r.title}</div>
                  <div className="cg-tip-grid">
                    <span><i style={{ background: 'var(--gender-f)' }} />ស្រី</span><b>{r.female}</b><em>{pct(r.female, r.total)}%</em>
                    <span><i style={{ background: 'var(--gender-m)' }} />ប្រុស</span><b>{male}</b><em>{pct(male, r.total)}%</em>
                    <span>ភ្នំពេញ</span><b>{r.pp}</b><em>{pct(r.pp, r.total)}%</em>
                    <span>ខេត្ត</span><b>{r.kp}</b><em>{pct(r.kp, r.total)}%</em>
                  </div>
                </div>
              )}
            </li>
          )
        })}
      </ol>
      {onSelect && <div className="cg-hint">ចុចលើផ្នែកណាមួយ ដើម្បីច្រោះក្រាហ្វទាំងអស់ · ចុចម្តងទៀតដើម្បីបង្ហាញគ្រប់ផ្នែក</div>}
    </div>
  )
}
