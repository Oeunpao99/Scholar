import React, { useEffect, useRef, useState } from 'react'
import { SeriesPoint } from '../../types'
import { khDate, shortDate } from '../../lib/format'

interface DailyGainBarsProps {
  points: SeriesPoint[]
}

const HEIGHT = 260
const M = { top: 22, right: 8, bottom: 28, left: 36 }

/** Round the axis max up to 1/2/5 × 10ⁿ so ticks land on whole numbers. */
const niceScale = (max: number, target = 4) => {
  if (max <= 0) return { top: 4, step: 1 }
  const raw = max / target
  const pow = Math.pow(10, Math.floor(Math.log10(raw)))
  const step = Math.max(1, [1, 2, 5, 10].map((m) => m * pow).find((s) => s >= raw) || pow * 10)
  return { top: Math.ceil(max / step) * step, step }
}

/** Bar with a 4px rounded data-end, anchored square to the baseline. */
const barPath = (x: number, y: number, w: number, h: number) => {
  const r = Math.min(4, w / 2, h)
  const base = y + h
  return `M${x},${base} V${y + r} Q${x},${y} ${x + r},${y} H${x + w - r} Q${x + w},${y} ${x + w},${y + r} V${base} Z`
}

/** Students gained per day — one series, so no legend box; the title names it. */
export const DailyGainBars: React.FC<DailyGainBarsProps> = ({ points }) => {
  const wrapRef = useRef<HTMLDivElement>(null)
  const [width, setWidth] = useState(640)
  const [active, setActive] = useState<number | null>(null)

  useEffect(() => {
    const el = wrapRef.current
    if (!el) return
    const ro = new ResizeObserver(([entry]) => setWidth(Math.max(280, entry.contentRect.width)))
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  const n = points.length
  const values = points.map((p) => p.gain?.total || 0)
  const max = Math.max(0, ...values)

  // Same wrapper element in every state, so the ResizeObserver stays attached.
  if (n === 0 || max === 0) {
    return (
      <div ref={wrapRef} className="bars-wrap">
        <div className="chart-empty">មិនមានសិស្សចុះឈ្មោះថ្មីក្នុងចន្លោះកាលបរិច្ឆេទនេះទេ</div>
      </div>
    )
  }

  const { top, step } = niceScale(max)
  const plotW = width - M.left - M.right
  const plotH = HEIGHT - M.top - M.bottom
  const band = plotW / n
  const barW = Math.max(2, Math.min(28, band - 2)) // ≥ 2px surface gap between bars
  const y = (v: number) => M.top + plotH - (v / top) * plotH
  const ticks = Array.from({ length: Math.round(top / step) + 1 }, (_, i) => i * step)
  const labelEvery = Math.max(1, Math.ceil(n / Math.max(1, Math.floor(plotW / 46))))
  const peakIdx = values.indexOf(max)

  const hovered = active !== null ? points[active] : null
  const tipLeft = active !== null ? M.left + band * active + band / 2 : 0

  return (
    <div ref={wrapRef} className="bars-wrap" onMouseLeave={() => setActive(null)}>
      <svg
        width={width}
        height={HEIGHT}
        role="img"
        aria-label={`សិស្សចុះឈ្មោះថ្មីប្រចាំថ្ងៃ ${n} ថ្ងៃ ខ្ពស់បំផុត ${max} នាក់ នៅថ្ងៃ ${khDate(points[peakIdx].date)}`}
      >
        {/* Recessive grid + y ticks */}
        {ticks.map((t) => (
          <g key={t}>
            <line x1={M.left} x2={width - M.right} y1={y(t)} y2={y(t)} stroke={t === 0 ? 'var(--viz-axis)' : 'var(--viz-grid)'} strokeWidth={1} />
            <text x={M.left - 8} y={y(t)} dy="0.32em" textAnchor="end" className="axis-text">{t}</text>
          </g>
        ))}

        {points.map((p, i) => {
          const v = values[i]
          const x = M.left + band * i + (band - barW) / 2
          const isActive = active === i
          return (
            <g key={p.date}>
              {isActive && <rect x={M.left + band * i} y={M.top} width={band} height={plotH} fill="var(--bg-subtle)" />}
              {v > 0 && (
                <path
                  d={barPath(x, y(v), barW, y(0) - y(v))}
                  fill={isActive ? 'var(--viz-bar-active)' : 'var(--viz-bar)'}
                />
              )}
              {/* Selective direct label: the peak day only */}
              {i === peakIdx && (
                <text x={x + barW / 2} y={y(v) - 6} textAnchor="middle" className="bar-peak-label">{v}</text>
              )}
              {i % labelEvery === 0 && (
                <text x={M.left + band * i + band / 2} y={HEIGHT - 8} textAnchor="middle" className="axis-text">
                  {shortDate(p.date)}
                </text>
              )}
              {/* Hit target: the full column, larger than the mark */}
              <rect
                x={M.left + band * i}
                y={M.top}
                width={band}
                height={plotH}
                fill="transparent"
                onMouseEnter={() => setActive(i)}
              />
            </g>
          )
        })}
      </svg>

      {hovered && (
        <div
          className="chart-tooltip"
          style={{ left: Math.min(Math.max(tipLeft, 90), width - 90), top: Math.max(4, y(values[active!]) - 12) }}
        >
          <div className="chart-tooltip-title">{khDate(hovered.date)}</div>
          <div className="chart-tooltip-row"><span>សិស្សថ្មី</span><strong>{hovered.gain.total} នាក់</strong></div>
          <div className="chart-tooltip-row"><span>ស្រី</span><strong>{hovered.gain.female}</strong></div>
          <div className="chart-tooltip-row"><span>ភ្នំពេញ</span><strong>{hovered.gain.pp}</strong></div>
          <div className="chart-tooltip-row"><span>ខេត្ត</span><strong>{hovered.gain.kp}</strong></div>
          <div className="chart-tooltip-foot">សរុបទាំងអស់ {hovered.total}</div>
        </div>
      )}
    </div>
  )
}
