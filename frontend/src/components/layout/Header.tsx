import React, { useEffect, useState } from 'react'
import { PanelLeft, ChevronRight, Calendar, Plus, Sun, Moon } from 'lucide-react'
import { api } from '../../lib/api'
import { useTheme } from '../../context/ThemeContext'
import { useAuth } from '../../context/AuthContext'
import { PAGE_TITLES } from './navigation'

interface HeaderProps {
  currentTab: string
  onToggleSidebar: () => void
  onQuickAdd: () => void
}

export const Header: React.FC<HeaderProps> = ({ currentTab, onToggleSidebar, onQuickAdd }) => {
  const { theme, toggleTheme } = useTheme()
  const { user } = useAuth()
  const [currentYear, setCurrentYear] = useState<number>(2026)
  const [dbHealthy, setDbHealthy] = useState<boolean>(true)

  useEffect(() => {
    const fetchMeta = async () => {
      try {
        const y = await api.getCurrentYear()
        if (y.current_year) setCurrentYear(y.current_year)
        const health = await api.getHealth()
        setDbHealthy(health.database)
      } catch {
        setDbHealthy(false)
      }
    }
    fetchMeta()
  }, [])

  const initials = (user?.full_name || user?.username || 'U').slice(0, 2).toUpperCase()
  const pageTitle = PAGE_TITLES[currentTab] || PAGE_TITLES.dashboard

  return (
    <header className="topbar">
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', minWidth: 0 }}>
        <button onClick={onToggleSidebar} className="btn btn-ghost" title="បើក/បិទ ម៉ឺនុយ" aria-label="បើក/បិទ ម៉ឺនុយ">
          <PanelLeft size={19} />
        </button>
        <div style={{ width: '1px', height: '22px', background: 'var(--border-subtle)' }} />
        <nav className="breadcrumb" aria-label="breadcrumb">
          {currentTab !== 'dashboard' && (
            <>
              <span className="hide-mobile">{PAGE_TITLES.dashboard}</span>
              <ChevronRight size={14} className="hide-mobile" />
            </>
          )}
          <strong>{pageTitle}</strong>
        </nav>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        <div className="badge badge-blue hide-mobile" style={{ padding: '5px 12px' }}>
          <Calendar size={13} />
          ឆ្នាំសិក្សា {currentYear}
        </div>

        <div
          className="hide-mobile"
          title={dbHealthy ? 'ប្រព័ន្ធដំណើរការធម្មតា' : 'បាត់ការតភ្ជាប់'}
          style={{ alignItems: 'center', gap: '6px', fontSize: '0.8rem', color: 'var(--text-muted)' }}
        >
          <span style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            background: dbHealthy ? 'var(--emerald-primary)' : 'var(--rose-primary)',
          }} />
          {dbHealthy ? 'ដំណើរការធម្មតា' : 'បាត់ការតភ្ជាប់'}
        </div>

        <button
          onClick={toggleTheme}
          className="btn btn-ghost"
          title={theme === 'light' ? 'ប្តូរទៅផ្ទៃងងឹត' : 'ប្តូរទៅផ្ទៃពន្លឺ'}
          aria-label={theme === 'light' ? 'ប្តូរទៅផ្ទៃងងឹត' : 'ប្តូរទៅផ្ទៃពន្លឺ'}
        >
          {theme === 'light' ? <Moon size={18} /> : <Sun size={18} />}
        </button>

        <button onClick={onQuickAdd} className="btn btn-primary">
          <Plus size={16} />
          <span className="hide-mobile">បញ្ចូលរបាយការណ៍ថ្មី</span>
        </button>

        <div className="avatar" title={user?.full_name || user?.username}>{initials}</div>
      </div>
    </header>
  )
}
