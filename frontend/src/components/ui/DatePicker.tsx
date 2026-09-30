import React, { useEffect, useRef, useState } from 'react'
import { Calendar, ChevronLeft, ChevronRight } from 'lucide-react'
import { khDate, localISODate } from '../../lib/format'

const MONTHS = ['មករា', 'កុម្ភៈ', 'មីនា', 'មេសា', 'ឧសភា', 'មិថុនា', 'កក្កដា', 'សីហា', 'កញ្ញា', 'តុលា', 'វិច្ឆិកា', 'ធ្នូ']
// Week starts on Monday, as on Cambodian calendars.
const WEEKDAYS = ['ច', 'អ', 'ពុ', 'ព្រ', 'សុ', 'ស', 'អា']

interface Props {
  value: string // YYYY-MM-DD, or '' for none
  onChange: (value: string) => void
  min?: string
  max?: string
  ariaLabel?: string
  className?: string
  /** Show a "clear" action (for optional dates such as range filters). */
  clearable?: boolean
  placeholder?: string
}

const parse = (iso: string) => {
  const [y, m, d] = iso.split('-').map(Number)
  return new Date(y, m - 1, d)
}

/**
 * Date field with a Khmer calendar popover (a bottom sheet on phones).
 * Values are local YYYY-MM-DD strings, the same as <input type="date">.
 */
export const DatePicker: React.FC<Props> = ({ value, onChange, min, max, ariaLabel, className, clearable, placeholder = 'ជ្រើសថ្ងៃ' }) => {
  const [open, setOpen] = useState(false)
  const initial = value ? parse(value) : new Date()
  const [view, setView] = useState({ y: initial.getFullYear(), m: initial.getMonth() })
  const [focus, setFocus] = useState(value || localISODate())
  const rootRef = useRef<HTMLDivElement>(null)
  const buttonRef = useRef<HTMLButtonElement>(null)
  const gridRef = useRef<HTMLDivElement>(null)
  const today = localISODate()

  const disabled = (iso: string) => (!!min && iso < min) || (!!max && iso > max)

  const openPicker = () => {
    const start = value || (max && today > max ? max : today)
    const d = parse(start)
    setView({ y: d.getFullYear(), m: d.getMonth() })
    setFocus(start)
    setOpen(true)
  }
  const close = () => { setOpen(false); buttonRef.current?.focus() }
  const pick = (iso: string) => {
    if (disabled(iso)) return
    onChange(iso)
    close()
  }

  useEffect(() => {
    if (!open) return
    gridRef.current?.focus()
    const onDown = (e: MouseEvent | TouchEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', onDown)
    document.addEventListener('touchstart', onDown)
    return () => {
      document.removeEventListener('mousedown', onDown)
      document.removeEventListener('touchstart', onDown)
    }
  }, [open])

  const shiftMonth = (delta: number) =>
    setView((v) => {
      const d = new Date(v.y, v.m + delta, 1)
      return { y: d.getFullYear(), m: d.getMonth() }
    })

  const moveFocus = (days: number) => {
    const d = parse(focus)
    d.setDate(d.getDate() + days)
    const iso = localISODate(d)
    setFocus(iso)
    setView({ y: d.getFullYear(), m: d.getMonth() })
  }

  const onGridKey = (e: React.KeyboardEvent) => {
    const keys: Record<string, number> = { ArrowLeft: -1, ArrowRight: 1, ArrowUp: -7, ArrowDown: 7 }
    if (e.key in keys) { e.preventDefault(); moveFocus(keys[e.key]) }
    else if (e.key === 'PageUp') { e.preventDefault(); shiftMonth(-1) }
    else if (e.key === 'PageDown') { e.preventDefault(); shiftMonth(1) }
    else if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); pick(focus) }
    else if (e.key === 'Escape') close()
  }

  // 6 rows x 7 days, Monday first.
  const first = new Date(view.y, view.m, 1)
  const lead = (first.getDay() + 6) % 7
  const cells = Array.from({ length: 42 }, (_, i) => {
    const d = new Date(view.y, view.m, 1 - lead + i)
    return { iso: localISODate(d), day: d.getDate(), inMonth: d.getMonth() === view.m }
  })

  const todayDisabled = disabled(today)

  return (
    <div ref={rootRef} className={`date-picker ${open ? 'open' : ''} ${className || ''}`}>
      <button
        ref={buttonRef}
        type="button"
        className="input-field date-picker-button"
        aria-haspopup="dialog"
        aria-expanded={open}
        aria-label={ariaLabel ? `${ariaLabel}: ${value ? khDate(value) : placeholder}` : undefined}
        onClick={() => (open ? setOpen(false) : openPicker())}
      >
        <Calendar size={15} className="date-picker-icon" />
        <span className={value ? '' : 'date-picker-placeholder'}>{value ? khDate(value) : placeholder}</span>
      </button>

      {open && (
        <>
          <div className="select-menu-backdrop" onClick={() => setOpen(false)} />
          <div className="date-picker-pop" role="dialog" aria-label={ariaLabel || 'ជ្រើសថ្ងៃ'}>
            <div className="date-picker-head">
              <button type="button" className="btn btn-ghost" onClick={() => shiftMonth(-1)} aria-label="ខែមុន"><ChevronLeft size={18} /></button>
              <div className="date-picker-title" aria-live="polite">ខែ{MONTHS[view.m]} {view.y}</div>
              <button type="button" className="btn btn-ghost" onClick={() => shiftMonth(1)} aria-label="ខែបន្ទាប់"><ChevronRight size={18} /></button>
            </div>

            <div className="date-picker-weekdays" aria-hidden="true">
              {WEEKDAYS.map((w) => <span key={w}>{w}</span>)}
            </div>
            <div ref={gridRef} className="date-picker-grid" role="grid" tabIndex={-1} onKeyDown={onGridKey}
              aria-activedescendant={`dp-${focus}`}>
              {cells.map((c) => {
                const off = disabled(c.iso)
                return (
                  <button
                    key={c.iso}
                    id={`dp-${c.iso}`}
                    type="button"
                    tabIndex={-1}
                    role="gridcell"
                    aria-selected={c.iso === value}
                    aria-label={khDate(c.iso)}
                    disabled={off}
                    className={[
                      'date-picker-day',
                      c.inMonth ? '' : 'outside',
                      c.iso === today ? 'today' : '',
                      c.iso === value ? 'selected' : '',
                      c.iso === focus ? 'focused' : '',
                    ].join(' ')}
                    onClick={() => pick(c.iso)}
                  >
                    {c.day}
                  </button>
                )
              })}
            </div>

            <div className="date-picker-foot">
              {clearable && value ? (
                <button type="button" className="link-button" onClick={() => { onChange(''); close() }}>សម្អាត</button>
              ) : <span />}
              <button type="button" className="btn btn-secondary btn-sm" disabled={todayDisabled} onClick={() => pick(today)}>ថ្ងៃនេះ</button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
