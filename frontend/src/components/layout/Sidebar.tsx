import React from 'react'
import { LogOut } from 'lucide-react'
import { Logo } from '../Logo'
import { useAuth } from '../../context/AuthContext'
import { NAV_SECTIONS, ROLE_LABELS } from './navigation'

interface SidebarProps {
  currentTab: string
  setCurrentTab: (tab: string) => void
  onClose: () => void
  collapsed: boolean
}

export const Sidebar: React.FC<SidebarProps> = ({ currentTab, setCurrentTab, onClose, collapsed }) => {
  const { user, logout } = useAuth()
  const userRole = user?.role || 'viewer'
  const displayName = user?.full_name || user?.username || ''
  const initials = (displayName || 'U').slice(0, 2).toUpperCase()

  const handleSelect = (tab: string) => {
    setCurrentTab(tab)
    if (window.innerWidth < 992) onClose()
  }

  const sections = NAV_SECTIONS
    .map((section) => ({
      ...section,
      items: section.items.filter((item) => !item.roles || item.roles.includes(userRole)),
    }))
    .filter((section) => section.items.length > 0)

  return (
    <aside className="sidebar">
      {/* Brand */}
      <div className="sidebar-brand">
        <Logo size={34} />
        <div className="sidebar-text" style={{ lineHeight: 1.25 }}>
          <div style={{ fontWeight: 700, fontSize: '1.05rem', color: 'var(--text-main)' }}>SCHOLAR</div>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>ប្រព័ន្ធចុះឈ្មោះបាក់ឌុប</div>
        </div>
      </div>

      {/* Workspace card */}
      <div className="sidebar-workspace" style={{ padding: '0 16px 8px' }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          padding: '10px 12px',
          background: 'var(--bg-card)',
          border: '1px solid var(--border-subtle)',
          borderRadius: 'var(--radius-md)',
          boxShadow: 'var(--shadow-sm)',
        }}>
          <div style={{
            width: '30px',
            height: '30px',
            borderRadius: '8px',
            background: 'var(--accent-soft)',
            color: 'var(--accent-text)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontWeight: 700,
            fontSize: '0.8rem',
          }}>
            ប
          </div>
          <div style={{ minWidth: 0 }}>
            <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-main)' }}>ការចុះឈ្មោះបាក់ឌុប</div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>កន្លែងធ្វើការចម្បង</div>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="sidebar-nav">
        {sections.map((section, idx) => (
          <div key={section.title || idx}>
            {idx > 0 && <div className="nav-divider" />}
            {section.title && <div className="nav-section-title">{section.title}</div>}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
              {section.items.map((item) => {
                const Icon = item.icon
                const isActive = currentTab === item.id
                return (
                  <button
                    key={item.id}
                    onClick={() => handleSelect(item.id)}
                    className={`nav-item ${isActive ? 'active' : ''}`}
                    aria-current={isActive ? 'page' : undefined}
                    title={collapsed ? item.label : undefined}
                    aria-label={item.label}
                  >
                    <Icon size={18} />
                    <span className="sidebar-text">{item.label}</span>
                  </button>
                )
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* User card */}
      <div className="sidebar-user">
        <div className="avatar" title={collapsed ? displayName : undefined}>{initials}</div>
        <div className="sidebar-text" style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-main)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {displayName}
          </div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {ROLE_LABELS[userRole] || userRole}
          </div>
        </div>
        <button onClick={logout} className="btn btn-ghost" title="ចាកចេញ" aria-label="ចាកចេញ">
          <LogOut size={17} />
        </button>
      </div>
    </aside>
  )
}
