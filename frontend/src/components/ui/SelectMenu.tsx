import React, { useEffect, useId, useRef, useState } from 'react'
import { Check, ChevronDown } from 'lucide-react'

export interface SelectOption {
  value: string
  label: string
  /** Small text on the left, e.g. a roman numeral. */
  prefix?: string
  /** A colour dot on the left, e.g. a grade colour. */
  dot?: string
}

interface Props {
  value: string
  options: SelectOption[]
  onChange: (value: string) => void
  ariaLabel?: string
  className?: string
  /** Open above the button - for pickers near the bottom of a clipped panel. */
  placement?: 'down' | 'up'
}

/**
 * A styled replacement for <select>: a button that opens a menu of options.
 * Keyboard: ↑/↓ move, Enter/Space choose, Esc closes. On phones the menu
 * opens as a bottom sheet (see .select-menu in index.css).
 */
export const SelectMenu: React.FC<Props> = ({ value, options, onChange, ariaLabel, className, placement = 'down' }) => {
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(0)
  const rootRef = useRef<HTMLDivElement>(null)
  const buttonRef = useRef<HTMLButtonElement>(null)
  const listRef = useRef<HTMLUListElement>(null)
  const listId = useId()
  const selected = options.find((o) => o.value === value) ?? options[0]

  const openMenu = () => {
    setActive(Math.max(0, options.findIndex((o) => o.value === value)))
    setOpen(true)
  }
  const choose = (i: number) => {
    onChange(options[i].value)
    setOpen(false)
    buttonRef.current?.focus()
  }

  useEffect(() => {
    if (!open) return
    listRef.current?.focus()
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

  useEffect(() => {
    if (open) listRef.current?.children[active]?.scrollIntoView({ block: 'nearest' })
  }, [active, open])

  const onListKey = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') { e.preventDefault(); setActive((i) => Math.min(options.length - 1, i + 1)) }
    else if (e.key === 'ArrowUp') { e.preventDefault(); setActive((i) => Math.max(0, i - 1)) }
    else if (e.key === 'Home') { e.preventDefault(); setActive(0) }
    else if (e.key === 'End') { e.preventDefault(); setActive(options.length - 1) }
    else if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); choose(active) }
    else if (e.key === 'Escape' || e.key === 'Tab') { setOpen(false); buttonRef.current?.focus() }
  }

  return (
    <div ref={rootRef} className={`select-menu ${open ? 'open' : ''} ${placement === 'up' ? 'up' : ''} ${className || ''}`}>
      <button
        ref={buttonRef}
        type="button"
        className="input-field select-menu-button"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={listId}
        aria-label={ariaLabel}
        onClick={() => (open ? setOpen(false) : openMenu())}
        onKeyDown={(e) => {
          if (e.key === 'ArrowDown' || e.key === 'ArrowUp') { e.preventDefault(); openMenu() }
        }}
      >
        <span className="select-menu-value">
          {selected?.dot && <span className="grade-pill-dot" style={{ background: selected.dot }} />}
          {selected?.prefix && <span className="select-menu-prefix">{selected.prefix}</span>}
          {selected?.label}
        </span>
        <ChevronDown size={16} className="select-menu-chevron" />
      </button>

      {open && (
        <>
          <div className="select-menu-backdrop" onClick={() => setOpen(false)} />
          <ul
            ref={listRef}
            id={listId}
            role="listbox"
            tabIndex={-1}
            aria-label={ariaLabel}
            aria-activedescendant={`${listId}-${active}`}
            className="select-menu-list"
            onKeyDown={onListKey}
          >
            {options.map((o, i) => {
              const isSel = o.value === value
              return (
                <li
                  key={o.value}
                  id={`${listId}-${i}`}
                  role="option"
                  aria-selected={isSel}
                  className={`select-menu-option ${i === active ? 'active' : ''} ${isSel ? 'selected' : ''}`}
                  onMouseEnter={() => setActive(i)}
                  onClick={() => choose(i)}
                >
                  {o.dot && <span className="grade-pill-dot" style={{ background: o.dot }} />}
                  {o.prefix && <span className="select-menu-prefix">{o.prefix}</span>}
                  <span className="select-menu-label">{o.label}</span>
                  {isSel && <Check size={16} className="select-menu-check" />}
                </li>
              )
            })}
          </ul>
        </>
      )}
    </div>
  )
}
