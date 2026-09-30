import React, { useState } from 'react'
import { Counters } from '../../types'

const GRADES = ['A', 'B', 'C', 'D', 'E'] as const

interface GradeDonutProps {
  grades: Record<string, Counters>
}

const SIZE = 200
const C = SIZE / 2
const R_OUT = 96
const R_IN = 64

const polar = (r: number, angle: number) => [C + r * Math.sin(angle), C - r * Math.cos(angle)]

/** Annular sector from a0 to a1 (radians, clockwise from 12 o'clock). */
const arcPath = (a0: number, a1: number) => {
  const large = a1 - a0 > Math.PI ? 1 : 0
  const [x0, y0] = polar(R_OUT, a0)
  const [x1, y1] = polar(R_OUT, a1)
  const [x2, y2] = polar(R_IN, a1)
  const [x3, y3] = polar(R_IN, a0)
  return `M${x0},${y0} A${R_OUT},${R_OUT} 0 ${large} 1 ${x1},${y1} L${x2},${y2} A${R_IN},${R_IN} 0 ${large} 0 ${x3},${y3} Z`
}

/** Part-to-whole of students by BacII grade — one colour per grade (see --grade-X in index.css). */
export const GradeDonut: React.FC<GradeDonutProps> = ({ grades }) => {
  const [active, setActive] = useState<string | null>(null)
  const rows = GRADES.map((g) => ({ grade: g, count: grades[g]?.total || 0, female: grades[g]?.female || 0 }))
  const total = rows.reduce((s, r) => s + r.count, 0)
  const pct = (n: number) => (total > 0 ? Math.round((n / total) * 100) : 0)

  const nonZero = rows.filter((r) => r.count > 0)
  let cursor = 0
  const slices = nonZero.map((r) => {
    const a0 = cursor
    cursor += (r.count / total) * Math.PI * 2
    return { ...r, a0, a1: cursor }
  })

  const focus = active ? rows.find((r) => r.grade === active) : null

  if (total === 0) {
    return (
      <div className="chart-empty">មិនទាន់មានទិន្នន័យនិទ្ទេសក្នុងចន្លោះកាលបរិច្ឆេទនេះ</div>
    )
  }

  return (
    <div className="donut-layout">
      <svg
        viewBox={`0 0 ${SIZE} ${SIZE}`}
        className="donut-svg"
        role="img"
        aria-label={`ចំនួនសិស្សតាមនិទ្ទេស: ${rows.map((r) => `${r.grade} ${r.count}`).join(', ')}`}
      >
        {slices.length === 1 ? (
          // A single grade is a full ring — an arc can't span 360°.
          <circle
            cx={C}
            cy={C}
            r={(R_OUT + R_IN) / 2}
            fill="none"
            stroke={`var(--grade-${slices[0].grade})`}
            strokeWidth={R_OUT - R_IN}
            onMouseEnter={() => setActive(slices[0].grade)}
            onMouseLeave={() => setActive(null)}
          />
        ) : (
          slices.map((s) => (
            <path
              key={s.grade}
              d={arcPath(s.a0, s.a1)}
              fill={`var(--grade-${s.grade})`}
              // 2px surface gap between slices
              stroke="var(--bg-card)"
              strokeWidth={2}
              strokeLinejoin="round"
              opacity={active && active !== s.grade ? 0.35 : 1}
              style={{ transition: 'opacity 0.15s ease', cursor: 'default' }}
              onMouseEnter={() => setActive(s.grade)}
              onMouseLeave={() => setActive(null)}
            />
          ))
        )}
        {/* Grade letter on every slice wide enough to hold it — the palette's
            red/green and blue/pink pairs need a non-colour cue. */}
        {slices.map((s) => {
          if (slices.length > 1 && s.a1 - s.a0 < 0.4) return null
          const mid = slices.length === 1 ? 0 : (s.a0 + s.a1) / 2
          const [x, y] = polar((R_OUT + R_IN) / 2, mid)
          return (
            <text
              key={`label-${s.grade}`}
              x={x}
              y={y}
              dy="0.35em"
              textAnchor="middle"
              className="donut-slice-label"
              style={{ fill: `var(--grade-${s.grade}-ink)`, opacity: active && active !== s.grade ? 0.35 : 1 }}
              pointerEvents="none"
            >
              {s.grade}
            </text>
          )
        })}
        <text x={C} y={C - 4} textAnchor="middle" className="donut-center-value">
          {focus ? focus.count : total}
        </text>
        <text x={C} y={C + 18} textAnchor="middle" className="donut-center-label">
          {focus ? `និទ្ទេស ${focus.grade}` : 'សិស្សសរុប'}
        </text>
      </svg>

      <ul className="donut-legend">
        {rows.map((r) => (
          <li
            key={r.grade}
            className={active === r.grade ? 'active' : ''}
            onMouseEnter={() => setActive(r.grade)}
            onMouseLeave={() => setActive(null)}
          >
            <span className="legend-swatch" style={{ background: `var(--grade-${r.grade})` }} />
            <span className="legend-label">និទ្ទេស {r.grade}</span>
            <span className="legend-value">{r.count}</span>
            <span className="legend-pct">{pct(r.count)}%</span>
          </li>
        ))}
      </ul>
    </div>
  )
}
