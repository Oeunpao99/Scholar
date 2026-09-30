import React, { useState } from 'react'
import {
  GraduationCap,
  Lock,
  User,
  ArrowRight,
  AlertCircle,
  Sparkles,
  ShieldCheck,
  Sun,
  Moon
} from 'lucide-react'
import confetti from 'canvas-confetti'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'

export const LoginPage: React.FC = () => {
  const { login } = useAuth()
  const { theme, toggleTheme } = useTheme()
  const [username, setUsername] = useState<string>('')
  const [password, setPassword] = useState<string>('')
  const [loading, setLoading] = useState<boolean>(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!username || !password) {
      setError('សូមបញ្ចូលឈ្មោះគណនី និងពាក្យសម្ងាត់')
      return
    }

    setLoading(true)
    setError(null)
    try {
      await login(username, password)
      confetti({
        particleCount: 50,
        spread: 60,
        origin: { y: 0.7 },
      })
    } catch (err: any) {
      setError(err.message || 'ឈ្មោះគណនី ឬពាក្យសម្ងាត់មិនត្រឹមត្រូវ')
    } finally {
      setLoading(false)
    }
  }

  // Quick fill demo credentials
  const handleQuickDemo = async () => {
    setUsername('admin@scholar.local')
    setPassword('ChangeMe123!')
    setLoading(true)
    setError(null)
    try {
      await login('admin@scholar.local', 'ChangeMe123!')
      confetti({
        particleCount: 60,
        spread: 70,
        origin: { y: 0.6 },
      })
    } catch (err: any) {
      setError(err.message || 'ការចូលសាកល្បងមិនបានសម្រេច')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '24px',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* Background glowing orbs */}
      <div
        style={{
          position: 'absolute',
          width: '500px',
          height: '500px',
          borderRadius: '50%',
          background: 'radial-gradient(circle, var(--accent-soft) 0%, transparent 70%)',
          top: '10%',
          left: '15%',
          pointerEvents: 'none',
        }}
      />
      <div
        style={{
          position: 'absolute',
          width: '450px',
          height: '450px',
          borderRadius: '50%',
          background: 'radial-gradient(circle, var(--accent-soft) 0%, transparent 70%)',
          bottom: '10%',
          right: '15%',
          pointerEvents: 'none',
        }}
      />

      {/* Top right theme toggle */}
      <div style={{ position: 'absolute', top: '20px', right: '20px', zIndex: 20 }}>
        <button
          onClick={toggleTheme}
          type="button"
          className="btn btn-secondary btn-sm"
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            padding: '8px 14px',
            borderRadius: 'var(--radius-full)',
            boxShadow: 'var(--shadow-sm)',
          }}
          title={theme === 'light' ? 'ប្តូរទៅផ្ទៃងងឹត' : 'ប្តូរទៅផ្ទៃពន្លឺ'}
        >
          {theme === 'light' ? (
            <>
              <Moon size={15} color="var(--sky-primary)" />
              <span style={{ fontSize: '0.8rem', fontWeight: 600 }}>ងងឹត</span>
            </>
          ) : (
            <>
              <Sun size={15} color="var(--amber-primary)" />
              <span style={{ fontSize: '0.8rem', fontWeight: 600 }}>ពន្លឺ</span>
            </>
          )}
        </button>
      </div>

      <div
        className="glass-panel animate-fade-in"
        style={{
          maxWidth: '440px',
          width: '100%',
          padding: '40px 32px',
          borderRadius: '24px',
          background: 'var(--bg-card)',
          border: '1px solid var(--border-subtle)',
          boxShadow: 'var(--shadow-lg), var(--shadow-glow-cyan)',
          position: 'relative',
          zIndex: 10,
        }}
      >
        {/* Brand header */}
        <div style={{ textAlign: 'center', marginBottom: '32px' }}>
          <div
            style={{
              width: '64px',
              height: '64px',
              borderRadius: '18px',
              background: 'var(--gradient-brand)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 16px',
              boxShadow: 'var(--shadow-glow-cyan)',
            }}
          >
            <GraduationCap size={36} color="#FFF" />
          </div>

          <h1 style={{ fontSize: '1.75rem', fontWeight: 800, letterSpacing: '-0.02em', color: 'var(--text-main)' }}>
            SCHOLAR
          </h1>
          <div style={{ fontSize: '0.875rem', color: 'var(--text-muted)', marginTop: '4px' }}>
            ប្រព័ន្ធគ្រប់គ្រងការចុះឈ្មោះសិស្សបាក់ឌុប
          </div>
        </div>

        {/* Error Alert */}
        {error && (
          <div
            style={{
              background: 'var(--rose-soft)',
              border: '1px solid var(--rose-border)',
              borderRadius: '12px',
              padding: '12px 14px',
              marginBottom: '20px',
              color: 'var(--rose-primary)',
              fontSize: '0.85rem',
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
            }}
          >
            <AlertCircle size={18} />
            <span>{error}</span>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
          <div className="input-group">
            <label className="input-label">ឈ្មោះគណនី ឬអ៊ីមែល</label>
            <div style={{ position: 'relative' }}>
              <input
                type="text"
                required
                className="input-field font-outfit"
                placeholder="admin@scholar.local"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                style={{ paddingLeft: '38px' }}
              />
              <User size={16} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-dim)' }} />
            </div>
          </div>

          <div className="input-group">
            <label className="input-label">ពាក្យសម្ងាត់</label>
            <div style={{ position: 'relative' }}>
              <input
                type="password"
                required
                className="input-field font-outfit"
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                style={{ paddingLeft: '38px' }}
              />
              <Lock size={16} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-dim)' }} />
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="btn btn-primary btn-lg"
            style={{ width: '100%', marginTop: '6px' }}
          >
            {loading ? (
              'កំពុងផ្ទៀងផ្ទាត់...'
            ) : (
              <>
                ចូលប្រើប្រាស់ប្រព័ន្ធ
                <ArrowRight size={18} />
              </>
            )}
          </button>
        </form>

        {/* Quick Demo Button */}
        <div style={{ marginTop: '24px', paddingTop: '20px', borderTop: '1px solid var(--border-subtle)', textAlign: 'center' }}>
          <div style={{ fontSize: '0.78rem', color: 'var(--text-dim)', marginBottom: '10px' }}>
            សម្រាប់តេស្តសាកល្បង
          </div>
          <button
            type="button"
            onClick={handleQuickDemo}
            disabled={loading}
            className="btn btn-secondary btn-sm"
            style={{ width: '100%', borderColor: 'var(--accent-border)', color: 'var(--cyan-primary)' }}
          >
            <Sparkles size={14} />
            ចូលដោយស្វ័យប្រវត្តិជាអ្នកគ្រប់គ្រងជាន់ខ្ពស់
          </button>
          <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', marginTop: '8px', fontFamily: 'var(--font-sans)' }}>
            admin@scholar.local / ChangeMe123!
          </div>
        </div>
      </div>
    </div>
  )
}
