import React, { useState } from 'react'
import { useAuth } from './context/AuthContext'
import { Layout } from './components/layout/Layout'
import { LoginPage } from './pages/LoginPage'
import { DashboardPage } from './pages/DashboardPage'
import { DailyReportEntryPage } from './pages/DailyReportEntryPage'
import { ReportsHistoryPage } from './pages/ReportsHistoryPage'
import { TelegramCenterPage } from './pages/TelegramCenterPage'
import { AIAssistantPage } from './pages/AIAssistantPage'
import { AnalyticsExportPage } from './pages/AnalyticsExportPage'
import { SettingsPage } from './pages/SettingsPage'
import { UsersManagementPage } from './pages/UsersManagementPage'
import { AuditLogsPage } from './pages/AuditLogsPage'
import { StudentsPage } from './pages/StudentsPage'
import { RefreshCw } from 'lucide-react'
import { Logo } from './components/Logo'

export const App: React.FC = () => {
  const { isAuthenticated, isLoading } = useAuth()
  const [currentTab, setCurrentTab] = useState<string>('dashboard')
  const [tabParam, setTabParam] = useState<string | undefined>(undefined)

  const handleNavigate = (tab: string, dateParam?: string) => {
    setCurrentTab(tab)
    setTabParam(dateParam)
  }

  // Loading state
  if (isLoading) {
    return (
      <div
        style={{
          minHeight: '100vh',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'var(--bg-dark)',
          gap: '16px',
        }}
      >
        <Logo size={60} />
        <div style={{ fontWeight: 800, fontSize: '1.25rem', letterSpacing: '-0.02em', color: 'var(--text-main)' }}>
          SCHOLAR
        </div>
        <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <RefreshCw size={14} className="pulse-glow" />
          កំពុងចាប់ផ្តើមប្រព័ន្ធ...
        </div>
      </div>
    )
  }

  // Unauthenticated -> Login
  if (!isAuthenticated) {
    return <LoginPage />
  }

  // Render Page Content based on tab
  const renderContent = () => {
    switch (currentTab) {
      case 'dashboard':
        return <DashboardPage onNavigate={handleNavigate} />
      case 'daily-entry':
        return <DailyReportEntryPage initialDate={tabParam} />
      case 'reports':
        return <ReportsHistoryPage onNavigate={handleNavigate} />
      case 'students':
        return <StudentsPage />
      case 'telegram':
        return <TelegramCenterPage initialDate={tabParam} onNavigate={handleNavigate} />
      case 'ai-assistant':
        return <AIAssistantPage onNavigate={handleNavigate} />
      case 'exports':
        return <AnalyticsExportPage />
      case 'settings':
        return <SettingsPage />
      case 'users':
        return <UsersManagementPage />
      case 'audit':
        return <AuditLogsPage />
      default:
        return <DashboardPage onNavigate={handleNavigate} />
    }
  }

  return (
    <Layout currentTab={currentTab} setCurrentTab={handleNavigate}>
      {renderContent()}
    </Layout>
  )
}
export default App
