import React from 'react'

export interface SegmentOption {
  value: string
  label: React.ReactNode
  /** Accessible name when the label is not plain text. */
  title?: string
}

interface Props {
  value: string
  options: SegmentOption[]
  onChange: (value: string) => void
  ariaLabel: string
  /** Tapping the chosen option again clears it (for optional fields). */
  allowClear?: boolean
  className?: string
}

/** One-tap choice between a few options - a radio group styled as buttons. */
export const Segmented: React.FC<Props> = ({ value, options, onChange, ariaLabel, allowClear, className }) => (
  <div role="radiogroup" aria-label={ariaLabel} className={`segmented ${className || ''}`}>
    {options.map((o) => {
      const on = o.value === value
      return (
        <button
          key={o.value}
          type="button"
          role="radio"
          aria-checked={on}
          title={o.title}
          className={`segmented-option ${on ? 'on' : ''}`}
          onClick={() => onChange(on && allowClear ? '' : o.value)}
        >
          {o.label}
        </button>
      )
    })}
  </div>
)
