import React, { useRef, useState } from 'react'
import { Lock, User, ArrowRight, AlertCircle, ShieldCheck, Eye, EyeOff, Sun, Moon, RefreshCw } from 'lucide-react'
import { Logo } from '../components/Logo'
import confetti from 'canvas-confetti'
import { useAuth } from '../context/AuthContext'
import { useTheme } from '../context/ThemeContext'

type LoginError = { message: string; field?: 'username' | 'password' | 'both' }

/** Turn an API failure into a message people can act on. */
const describeError = (err: any): LoginError => {
  const status: number | undefined = err?.status
  if (status === 401) return { message: 'ឈ្មោះគណនី ឬពាក្យសម្ងាត់មិនត្រឹមត្រូវ។ សូមពិនិត្យ ហើយព្យាយាមម្តងទៀត។', field: 'both' }
  if (status === 422) return { message: 'ពាក្យសម្ងាត់ត្រូវមានយ៉ាងហោចណាស់ ៦ តួអក្សរ។', field: 'password' }
  if (status === 403) return { message: 'គណនីនេះត្រូវបានបិទ។ សូមទាក់ទងអ្នកគ្រប់គ្រងប្រព័ន្ធ។', field: 'username' }
  if (status === 429) return { message: 'ព្យាយាមចូលច្រើនដងពេក។ សូមរង់ចាំបន្តិច រួចព្យាយាមម្តងទៀត។' }
  if (status && status >= 500) return { message: 'ម៉ាស៊ីនមេមានបញ្ហា។ សូមព្យាយាមម្តងទៀតនៅពេលក្រោយ។' }
  if (err instanceof TypeError) return { message: 'មិនអាចភ្ជាប់ទៅម៉ាស៊ីនមេបានទេ។ សូមពិនិត្យអ៊ីនធឺណិត។' }
  return { message: err?.message || 'ការចូលមិនបានសម្រេច។ សូមព្យាយាមម្តងទៀត។' }
}

export const LoginPage: React.FC = () => {
  const { login } = useAuth()
  const { theme, toggleTheme } = useTheme()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<LoginError | null>(null)
  // Bumped on every failure so the error box re-runs its shake animation.
  const [attempt, setAttempt] = useState(0)
  const [showPassword, setShowPassword] = useState(false)
  const [capsLock, setCapsLock] = useState(false)
  const usernameRef = useRef<HTMLInputElement>(null)
  const passwordRef = useRef<HTMLInputElement>(null)

  const fail = (e: LoginError) => {
    setError(e)
    setAttempt((n) => n + 1)
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!username.trim()) {
      fail({ message: 'សូមបញ្ចូលឈ្មោះគណនី ឬអ៊ីមែល', field: 'username' })
      usernameRef.current?.focus()
      return
    }
    if (!password) {
      fail({ message: 'សូមបញ្ចូលពាក្យសម្ងាត់', field: 'password' })
      passwordRef.current?.focus()
      return
    }

    setLoading(true)
    setError(null)
    try {
      await login(username.trim(), password)
      confetti({ particleCount: 50, spread: 60, origin: { y: 0.7 } })
    } catch (err: any) {
      const described = describeError(err)
      fail(described)
      if (described.field === 'both' || described.field === 'password') {
        setPassword('')
        passwordRef.current?.focus()
      } else if (described.field === 'username') {
        usernameRef.current?.focus()
      }
    } finally {
      setLoading(false)
    }
  }

  const invalid = (f: 'username' | 'password') => !!error && (error.field === f || error.field === 'both')
  const onType = (setter: (v: string) => void) => (e: React.ChangeEvent<HTMLInputElement>) => {
    setter(e.target.value)
    if (error) setError(null)
  }
  const onKey = (e: React.KeyboardEvent<HTMLInputElement>) => setCapsLock(e.getModifierState?.('CapsLock') ?? false)

  return (
    <div className="login-screen">
      <div className="login-glow" aria-hidden="true" />

      <header className="login-top">
        <button
          onClick={toggleTheme}
          type="button"
          className="btn btn-secondary btn-sm login-theme"
          title={theme === 'light' ? 'ប្តូរទៅផ្ទៃងងឹត' : 'ប្តូរទៅផ្ទៃពន្លឺ'}
        >
          {theme === 'light' ? <Moon size={15} /> : <Sun size={15} />}
          <span>{theme === 'light' ? 'ងងឹត' : 'ពន្លឺ'}</span>
        </button>
      </header>

      <main className="login-card animate-fade-in">
        <div className="login-brand">
          <Logo size={60} style={{ borderRadius: 16 }} />
          <h1>SCHOLAR</h1>
          <p>ប្រព័ន្ធគ្រប់គ្រងការចុះឈ្មោះសិស្សបាក់ឌុប</p>
        </div>

        {error && (
          <div key={attempt} role="alert" aria-live="assertive" className="login-error">
            <AlertCircle size={18} style={{ flexShrink: 0 }} />
            <span>{error.message}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} noValidate className="login-form">
          <label className="input-group">
            <span className="input-label">ឈ្មោះគណនី ឬអ៊ីមែល</span>
            <span className="login-field">
              <User size={17} className="login-field-icon" />
              <input
                ref={usernameRef}
                type="text"
                autoComplete="username"
                autoCapitalize="none"
                autoCorrect="off"
                spellCheck={false}
                inputMode="email"
                className={`input-field font-outfit ${invalid('username') ? 'is-invalid' : ''}`}
                aria-invalid={invalid('username')}
                placeholder="name@example.com"
                value={username}
                onChange={onType(setUsername)}
                onKeyUp={onKey}
                disabled={loading}
              />
            </span>
          </label>

          <label className="input-group">
            <span className="input-label">ពាក្យសម្ងាត់</span>
            <span className="login-field">
              <Lock size={17} className="login-field-icon" />
              <input
                ref={passwordRef}
                type={showPassword ? 'text' : 'password'}
                autoComplete="current-password"
                className={`input-field font-outfit ${invalid('password') ? 'is-invalid' : ''}`}
                aria-invalid={invalid('password')}
                placeholder="••••••••"
                value={password}
                onChange={onType(setPassword)}
                onKeyUp={onKey}
                disabled={loading}
                style={{ paddingRight: 46 }}
              />
              <button
                type="button"
                className="btn btn-ghost login-eye"
                onClick={() => setShowPassword((v) => !v)}
                aria-label={showPassword ? 'លាក់ពាក្យសម្ងាត់' : 'បង្ហាញពាក្យសម្ងាត់'}
                title={showPassword ? 'លាក់ពាក្យសម្ងាត់' : 'បង្ហាញពាក្យសម្ងាត់'}
              >
                {showPassword ? <EyeOff size={17} /> : <Eye size={17} />}
              </button>
            </span>
            {capsLock && <span className="login-hint">Caps Lock កំពុងបើក</span>}
          </label>

          <button type="submit" disabled={loading} className="btn btn-primary btn-lg login-submit">
            {loading ? (
              <>
                <RefreshCw size={17} className="spin" /> កំពុងផ្ទៀងផ្ទាត់…
              </>
            ) : (
              <>
                ចូលប្រើប្រាស់ប្រព័ន្ធ <ArrowRight size={18} />
              </>
            )}
          </button>
        </form>

        <footer className="login-foot">
          <ShieldCheck size={15} style={{ flexShrink: 0 }} />
          <span>មិនទាន់មានគណនី ឬភ្លេចពាក្យសម្ងាត់? សូមទាក់ទងអ្នកគ្រប់គ្រងប្រព័ន្ធ</span>
        </footer>
      </main>
    </div>
  )
}
