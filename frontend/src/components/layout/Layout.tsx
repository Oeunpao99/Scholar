import React, { useState } from 'react'
import { Sidebar } from './Sidebar'
import { Header } from './Header'

interface LayoutProps {
  currentTab: string
  setCurrentTab: (tab: string) => void
  children: React.ReactNode
}

export const Layout: React.FC<LayoutProps> = ({ currentTab, setCurrentTab, children }) => {
  // Desktop: sidebar can be collapsed. Mobile: sidebar is a slide-in drawer.
  const [collapsed, setCollapsed] = useState(false)
  const [mobileOpen, setMobileOpen] = useState(false)

  const toggleSidebar = () => {
    if (window.innerWidth < 992) setMobileOpen((prev) => !prev)
    else setCollapsed((prev) => !prev)
  }

  return (
    <div className={`app-container ${collapsed ? 'collapsed' : ''} ${mobileOpen ? 'mobile-open' : ''}`}>
      <Sidebar
        currentTab={currentTab}
        setCurrentTab={setCurrentTab}
        onClose={() => setMobileOpen(false)}
        collapsed={collapsed}
      />
      {mobileOpen && (
        <div
          onClick={() => setMobileOpen(false)}
          style={{ position: 'fixed', inset: 0, background: 'var(--overlay)', zIndex: 35 }}
        />
      )}
      <div className="main-content">
        <Header
          currentTab={currentTab}
          onToggleSidebar={toggleSidebar}
          onQuickAdd={() => setCurrentTab('daily-entry')}
        />
        <main className="content-body">
          {children}
        </main>
      </div>
    </div>
  )
}
