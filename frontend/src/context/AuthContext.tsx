import React, { createContext, useContext, useEffect, useState } from 'react'
import { api } from '../lib/api'
import { User } from '../types'

interface AuthContextType {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (loginText: string, passText: string) => Promise<void>
  logout: () => void
  refreshUser: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(localStorage.getItem('scholar_token'))
  const [isLoading, setIsLoading] = useState<boolean>(true)

  const refreshUser = async () => {
    try {
      const me = await api.getMe()
      setUser(me)
      localStorage.setItem('scholar_user', JSON.stringify(me))
    } catch {
      logout()
    }
  }

  useEffect(() => {
    const initAuth = async () => {
      const savedToken = localStorage.getItem('scholar_token')
      if (savedToken) {
        setToken(savedToken)
        try {
          const me = await api.getMe()
          setUser(me)
        } catch {
          logout()
        }
      }
      setIsLoading(false)
    }
    initAuth()
  }, [])

  // No global isLoading here: it swaps the login page for the splash screen,
  // which remounts the form and throws away its error message. The form shows
  // its own progress.
  const login = async (loginText: string, passText: string) => {
    const res = await api.login(loginText, passText)
    localStorage.setItem('scholar_token', res.access_token)
    try {
      const me = await api.getMe()
      setToken(res.access_token)
      setUser(me)
      localStorage.setItem('scholar_user', JSON.stringify(me))
    } catch (err) {
      localStorage.removeItem('scholar_token')
      throw err
    }
  }

  const logout = () => {
    localStorage.removeItem('scholar_token')
    localStorage.removeItem('scholar_user')
    setToken(null)
    setUser(null)
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!token && !!user,
        isLoading,
        login,
        logout,
        refreshUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
