import React, { useEffect, useState } from 'react'
import {
  Users,
  UserPlus,
  Shield,
  Edit2,
  KeyRound,
  Trash2,
  CheckCircle2,
  AlertTriangle,
  X,
  Save,
  Search,
  RefreshCw,
  Mail,
  UserCheck,
  ShieldAlert
} from 'lucide-react'
import confetti from 'canvas-confetti'
import { api } from '../lib/api'
import { PaginatedResponse, Role, User } from '../types'
import { useAuth } from '../context/AuthContext'

export const UsersManagementPage: React.FC = () => {
  const { user: currentUser } = useAuth()
  const isAdmin = currentUser?.role === 'superadmin' || currentUser?.role === 'admin'

  const [usersData, setUsersData] = useState<PaginatedResponse<User> | null>(null)
  const [loading, setLoading] = useState<boolean>(true)
  const [error, setError] = useState<string | null>(null)
  const [page, setPage] = useState<number>(1)
  const [search, setSearch] = useState<string>('')

  // Modals
  const [isAddOpen, setIsAddOpen] = useState<boolean>(false)
  const [userToEdit, setUserToEdit] = useState<User | null>(null)
  const [userToResetPassword, setUserToResetPassword] = useState<User | null>(null)
  const [userToDelete, setUserToDelete] = useState<User | null>(null)

  // Forms
  const [addForm, setAddForm] = useState({
    full_name: '',
    username: '',
    email: '',
    password: '',
    role: 'staff' as Role,
  })
  const [editForm, setEditForm] = useState({
    full_name: '',
    role: 'staff' as Role,
    is_active: true,
  })
  const [newPassword, setNewPassword] = useState<string>('')
  const [formSubmitting, setFormSubmitting] = useState<boolean>(false)

  const fetchUsers = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await api.getUsers(page, 50)
      setUsersData(res)
    } catch (err: any) {
      setError(err.message || 'បរាជ័យក្នុងការទាញយកបញ្ជីអ្នកប្រើប្រាស់')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (isAdmin) {
      fetchUsers()
    }
  }, [page, isAdmin])

  if (!isAdmin) {
    return (
      <div className="glass-panel" style={{ padding: '60px 20px', textAlign: 'center', maxWidth: '500px', margin: '40px auto' }}>
        <ShieldAlert size={48} color="var(--rose-primary)" style={{ margin: '0 auto 16px' }} />
        <h2 style={{ fontSize: '1.3rem', fontWeight: 800 }}>ពុំមានសិទ្ធិចូលមើលទំព័រនេះឡើយ</h2>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginTop: '8px' }}>
          ទំព័រគ្រប់គ្រងអ្នកប្រើប្រាស់ត្រូវបានកំណត់សម្រាប់តែអ្នករៀបចំប្រព័ន្ធ និងអ្នកគ្រប់គ្រងជាន់ខ្ពស់ប៉ុណ្ណោះ។
        </p>
      </div>
    )
  }

  // Handle Add User
  const handleAddUser = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormSubmitting(true)
    try {
      await api.createUser(addForm)
      setIsAddOpen(false)
      setAddForm({ full_name: '', username: '', email: '', password: '', role: 'staff' })
      confetti({ particleCount: 50, spread: 60 })
      fetchUsers()
    } catch (err: any) {
      alert(`បរាជ័យក្នុងការបង្កើតអ្នកប្រើប្រាស់: ${err.message}`)
    } finally {
      setFormSubmitting(false)
    }
  }

  // Handle Edit User
  const handleEditUser = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!userToEdit) return
    setFormSubmitting(true)
    try {
      await api.updateUser(userToEdit.id, editForm)
      setUserToEdit(null)
      fetchUsers()
    } catch (err: any) {
      alert(`បរាជ័យក្នុងការកែប្រែ: ${err.message}`)
    } finally {
      setFormSubmitting(false)
    }
  }

  // Handle Reset Password
  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!userToResetPassword || !newPassword) return
    setFormSubmitting(true)
    try {
      await api.resetUserPassword(userToResetPassword.id, newPassword)
      setUserToResetPassword(null)
      setNewPassword('')
      alert('បានផ្លាស់ប្តូរពាក្យសម្ងាត់ថ្មីដោយជោគជ័យ!')
    } catch (err: any) {
      alert(`បរាជ័យក្នុងការផ្លាស់ប្តូរពាក្យសម្ងាត់: ${err.message}`)
    } finally {
      setFormSubmitting(false)
    }
  }

  // Handle Delete User
  const handleDeleteUser = async () => {
    if (!userToDelete) return
    try {
      await api.deleteUser(userToDelete.id)
      setUserToDelete(null)
      fetchUsers()
    } catch (err: any) {
      alert(`បរាជ័យក្នុងការលុបអ្នកប្រើប្រាស់: ${err.message}`)
    }
  }

  const getRoleBadge = (role: Role) => {
    switch (role) {
      case 'superadmin':
        return <span className="badge badge-rose">អ្នកគ្រប់គ្រងជាន់ខ្ពស់</span>
      case 'admin':
        return <span className="badge badge-blue">អ្នករៀបចំប្រព័ន្ធ</span>
      case 'manager':
        return <span className="badge badge-cyan">អ្នកគ្រប់គ្រង</span>
      case 'staff':
        return <span className="badge badge-emerald">បុគ្គលិក</span>
      default:
        return <span className="badge badge-amber">អ្នកមើល</span>
    }
  }

  const filteredUsers = (usersData?.items || []).filter((u) => {
    if (!search) return true
    const s = search.toLowerCase()
    return (
      u.full_name?.toLowerCase().includes(s) ||
      u.username?.toLowerCase().includes(s) ||
      u.email?.toLowerCase().includes(s) ||
      u.role?.toLowerCase().includes(s)
    )
  })

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <h1 className="page-title">គ្រប់គ្រងអ្នកប្រើប្រាស់ និងតួនាទី</h1>
          </div>
          <p className="page-subtitle">
            បន្ថែម ប្តូរតួនាទី កំណត់ពាក្យសម្ងាត់ឡើងវិញ និងត្រួតពិនិត្យសកម្មភាពគណនីបុគ្គលិក
          </p>
        </div>

        <div style={{ display: 'flex', gap: '10px' }}>
          <button onClick={() => setIsAddOpen(true)} className="btn btn-primary">
            <UserPlus size={16} />
            បន្ថែមអ្នកប្រើប្រាស់ថ្មី
          </button>
          <button onClick={fetchUsers} className="btn btn-secondary">
            <RefreshCw size={15} className={loading ? 'pulse-glow' : ''} />
          </button>
        </div>
      </div>

      {/* Filter / Search Bar */}
      <div className="glass-panel" style={{ padding: '16px 20px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '16px' }}>
        <div style={{ position: 'relative', maxWidth: '360px', width: '100%' }}>
          <input
            type="text"
            className="input-field"
            placeholder="ស្វែងរកឈ្មោះ អ៊ីមែល ឬតួនាទី..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{ paddingLeft: '36px' }}
          />
          <Search size={16} style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-dim)' }} />
        </div>

        <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
          សរុប <strong style={{ color: 'var(--text-main)' }}>{filteredUsers.length}</strong> គណនី
        </div>
      </div>

      {/* Users Table */}
      <div className="glass-panel" style={{ overflow: 'hidden' }}>
        {loading && !usersData ? (
          <div style={{ padding: '60px', textAlign: 'center', color: 'var(--text-muted)' }}>
            <RefreshCw size={28} className="pulse-glow" style={{ margin: '0 auto 12px' }} />
            <div>កំពុងផ្ទុកបញ្ជីអ្នកប្រើប្រាស់...</div>
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem' }}>
              <thead>
                <tr style={{ background: 'var(--bg-subtle)', borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-dim)', fontSize: '0.8rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  <th style={{ padding: '14px 18px', textAlign: 'left' }}>អ្នកប្រើប្រាស់</th>
                  <th style={{ padding: '14px 18px', textAlign: 'left' }}>ឈ្មោះគណនី / អ៊ីមែល</th>
                  <th style={{ padding: '14px 18px', textAlign: 'center' }}>តួនាទី</th>
                  <th style={{ padding: '14px 18px', textAlign: 'center' }}>ស្ថានភាព</th>
                  <th style={{ padding: '14px 18px', textAlign: 'right' }}>សកម្មភាព</th>
                </tr>
              </thead>
              <tbody>
                {filteredUsers.map((u) => {
                  const initials = u.full_name
                    ? u.full_name.slice(0, 2).toUpperCase()
                    : u.username.slice(0, 2).toUpperCase()

                  return (
                    <tr
                      key={u.id}
                      style={{ borderBottom: '1px solid var(--border-subtle)' }}
                    >
                      {/* Name & Avatar */}
                      <td style={{ padding: '14px 18px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                          <div
                            style={{
                              width: '38px',
                              height: '38px',
                              borderRadius: '10px',
                              background: 'var(--gradient-brand)',
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'center',
                              fontWeight: 700,
                              color: '#FFF',
                              fontSize: '0.85rem',
                              fontFamily: 'var(--font-sans)',
                            }}
                          >
                            {initials}
                          </div>
                          <div>
                            <div style={{ fontWeight: 700, color: 'var(--text-main)' }}>
                              {u.full_name || u.username}
                            </div>
                            <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', fontFamily: 'var(--font-sans)' }}>
                              @{u.username}
                            </div>
                          </div>
                        </div>
                      </td>

                      {/* Email */}
                      <td style={{ padding: '14px 18px' }}>
                        <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', fontFamily: 'var(--font-sans)' }}>
                          {u.email}
                        </div>
                      </td>

                      {/* Role */}
                      <td style={{ padding: '14px 18px', textAlign: 'center' }}>
                        {getRoleBadge(u.role)}
                      </td>

                      {/* Status */}
                      <td style={{ padding: '14px 18px', textAlign: 'center' }}>
                        {u.is_active ? (
                          <span className="badge badge-emerald" style={{ fontSize: '0.7rem' }}>
                            សកម្ម
                          </span>
                        ) : (
                          <span className="badge badge-rose" style={{ fontSize: '0.7rem' }}>
                            ផ្អាក
                          </span>
                        )}
                      </td>

                      {/* Actions */}
                      <td style={{ padding: '14px 18px', textAlign: 'right' }}>
                        <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                          <button
                            onClick={() => {
                              setUserToEdit(u)
                              setEditForm({
                                full_name: u.full_name || '',
                                role: u.role,
                                is_active: u.is_active,
                              })
                            }}
                            className="btn btn-secondary btn-sm"
                            title="កែសម្រួលគណនី"
                            style={{ padding: '6px 8px' }}
                          >
                            <Edit2 size={14} color="var(--amber-primary)" />
                          </button>

                          <button
                            onClick={() => {
                              setUserToResetPassword(u)
                              setNewPassword('')
                            }}
                            className="btn btn-secondary btn-sm"
                            title="កំណត់ពាក្យសម្ងាត់ថ្មី"
                            style={{ padding: '6px 8px' }}
                          >
                            <KeyRound size={14} color="var(--accent-text)" />
                          </button>

                          {currentUser?.id !== u.id && (
                            <button
                              onClick={() => setUserToDelete(u)}
                              className="btn btn-danger btn-sm"
                              title="លុបអ្នកប្រើប្រាស់"
                              style={{ padding: '6px 8px' }}
                            >
                              <Trash2 size={14} />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ADD USER MODAL */}
      {isAddOpen && (
        <div style={{
          position: 'fixed',
          inset: 0,
          backgroundColor: 'var(--overlay)',
          backdropFilter: 'blur(8px)',
          zIndex: 50,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '20px'
        }}>
          <div className="glass-panel" style={{ maxWidth: '500px', width: '100%', background: 'var(--bg-surface)', padding: '28px', borderRadius: '20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '14px' }}>
              <h2 style={{ fontSize: '1.25rem', fontWeight: 800 }}>បន្ថែមអ្នកប្រើប្រាស់ថ្មី</h2>
              <button onClick={() => setIsAddOpen(false)} className="btn btn-secondary btn-sm">
                <X size={16} />
              </button>
            </div>

            <form onSubmit={handleAddUser} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div className="input-group">
                <label className="input-label">ឈ្មោះពេញ</label>
                <input
                  type="text"
                  required
                  className="input-field"
                  placeholder="ឧ. អ៊ឺន ប៉ាវ"
                  value={addForm.full_name}
                  onChange={(e) => setAddForm({ ...addForm, full_name: e.target.value })}
                />
              </div>

              <div className="input-group">
                <label className="input-label">ឈ្មោះគណនី</label>
                <input
                  type="text"
                  required
                  className="input-field font-outfit"
                  placeholder="username"
                  value={addForm.username}
                  onChange={(e) => setAddForm({ ...addForm, username: e.target.value })}
                />
              </div>

              <div className="input-group">
                <label className="input-label">អ៊ីមែល</label>
                <input
                  type="email"
                  required
                  className="input-field font-outfit"
                  placeholder="user@scholar.local"
                  value={addForm.email}
                  onChange={(e) => setAddForm({ ...addForm, email: e.target.value })}
                />
              </div>

              <div className="input-group">
                <label className="input-label">ពាក្យសម្ងាត់ដំបូង</label>
                <input
                  type="password"
                  required
                  minLength={6}
                  className="input-field font-outfit"
                  placeholder="••••••••"
                  value={addForm.password}
                  onChange={(e) => setAddForm({ ...addForm, password: e.target.value })}
                />
              </div>

              <div className="input-group">
                <label className="input-label">តួនាទី</label>
                <select
                  className="input-field"
                  value={addForm.role}
                  onChange={(e) => setAddForm({ ...addForm, role: e.target.value as Role })}
                >
                  <option value="staff">បុគ្គលិកបញ្ចូលទិន្នន័យ</option>
                  <option value="manager">អ្នកគ្រប់គ្រង</option>
                  <option value="admin">អ្នករៀបចំប្រព័ន្ធ</option>
                  <option value="viewer">អ្នកមើលរបាយការណ៍តែប៉ុណ្ណោះ</option>
                </select>
              </div>

              <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '16px' }}>
                <button type="button" onClick={() => setIsAddOpen(false)} className="btn btn-secondary">
                  បោះបង់
                </button>
                <button type="submit" disabled={formSubmitting} className="btn btn-primary">
                  <UserPlus size={16} />
                  {formSubmitting ? 'កំពុងបង្កើត...' : 'បង្កើតគណនី'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* EDIT USER MODAL */}
      {userToEdit && (
        <div style={{
          position: 'fixed',
          inset: 0,
          backgroundColor: 'var(--overlay)',
          backdropFilter: 'blur(8px)',
          zIndex: 50,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '20px'
        }}>
          <div className="glass-panel" style={{ maxWidth: '480px', width: '100%', background: 'var(--bg-surface)', padding: '28px', borderRadius: '20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '14px' }}>
              <h2 style={{ fontSize: '1.25rem', fontWeight: 800 }}>កែសម្រួលគណនី @{userToEdit.username}</h2>
              <button onClick={() => setUserToEdit(null)} className="btn btn-secondary btn-sm">
                <X size={16} />
              </button>
            </div>

            <form onSubmit={handleEditUser} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div className="input-group">
                <label className="input-label">ឈ្មោះពេញ</label>
                <input
                  type="text"
                  required
                  className="input-field"
                  value={editForm.full_name}
                  onChange={(e) => setEditForm({ ...editForm, full_name: e.target.value })}
                />
              </div>

              <div className="input-group">
                <label className="input-label">តួនាទី</label>
                <select
                  className="input-field"
                  value={editForm.role}
                  onChange={(e) => setEditForm({ ...editForm, role: e.target.value as Role })}
                >
                  <option value="staff">បុគ្គលិក</option>
                  <option value="manager">អ្នកគ្រប់គ្រង</option>
                  <option value="admin">អ្នករៀបចំប្រព័ន្ធ</option>
                  <option value="viewer">អ្នកមើល</option>
                </select>
              </div>

              <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', marginTop: '6px' }}>
                <input
                  type="checkbox"
                  checked={editForm.is_active}
                  onChange={(e) => setEditForm({ ...editForm, is_active: e.target.checked })}
                  style={{ accentColor: 'var(--cyan-primary)', width: '18px', height: '18px' }}
                />
                <span style={{ fontSize: '0.9rem', color: 'var(--text-main)', fontWeight: 600 }}>
                  គណនីសកម្ម
                </span>
              </label>

              <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '16px' }}>
                <button type="button" onClick={() => setUserToEdit(null)} className="btn btn-secondary">
                  បោះបង់
                </button>
                <button type="submit" disabled={formSubmitting} className="btn btn-primary">
                  <Save size={16} />
                  {formSubmitting ? 'កំពុងរក្សាទុក...' : 'រក្សាទុក'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* RESET PASSWORD MODAL */}
      {userToResetPassword && (
        <div style={{
          position: 'fixed',
          inset: 0,
          backgroundColor: 'var(--overlay)',
          backdropFilter: 'blur(8px)',
          zIndex: 50,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '20px'
        }}>
          <div className="glass-panel" style={{ maxWidth: '440px', width: '100%', background: 'var(--bg-surface)', padding: '24px', borderRadius: '20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '12px' }}>
              <h2 style={{ fontSize: '1.2rem', fontWeight: 800 }}>កំណត់ពាក្យសម្ងាត់ឡើងវិញ</h2>
              <button onClick={() => setUserToResetPassword(null)} className="btn btn-secondary btn-sm">
                <X size={16} />
              </button>
            </div>

            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '16px' }}>
              កំណត់ពាក្យសម្ងាត់ថ្មីសម្រាប់អ្នកប្រើប្រាស់ <strong>@{userToResetPassword.username}</strong>
            </p>

            <form onSubmit={handleResetPassword} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div className="input-group">
                <label className="input-label">ពាក្យសម្ងាត់ថ្មី</label>
                <input
                  type="password"
                  required
                  minLength={6}
                  className="input-field font-outfit"
                  placeholder="••••••••"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                />
              </div>

              <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '12px' }}>
                <button type="button" onClick={() => setUserToResetPassword(null)} className="btn btn-secondary">
                  បោះបង់
                </button>
                <button type="submit" disabled={formSubmitting || !newPassword} className="btn btn-primary">
                  <KeyRound size={16} />
                  ផ្លាស់ប្តូរពាក្យសម្ងាត់
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* DELETE USER CONFIRMATION */}
      {userToDelete && (
        <div style={{
          position: 'fixed',
          inset: 0,
          backgroundColor: 'var(--overlay)',
          backdropFilter: 'blur(8px)',
          zIndex: 55,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '20px'
        }}>
          <div className="glass-panel" style={{ maxWidth: '420px', width: '100%', background: 'var(--bg-surface)', padding: '24px', borderRadius: '20px', textAlign: 'center', border: '1px solid var(--rose-border)' }}>
            <Trash2 size={36} color="var(--rose-primary)" style={{ margin: '0 auto 14px' }} />
            <h3 style={{ fontSize: '1.2rem', fontWeight: 700, marginBottom: '8px' }}>បញ្ជាក់ការលុបអ្នកប្រើប្រាស់</h3>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: '20px', lineHeight: 1.5 }}>
              តើអ្នកពិតជាចង់លុបគណនី <strong>@{userToDelete.username}</strong> ({userToDelete.full_name}) មែនឬទេ? សកម្មភាពនេះមិនអាចត្រឡប់វិញបានឡើយ។
            </p>

            <div style={{ display: 'flex', gap: '10px' }}>
              <button onClick={() => setUserToDelete(null)} className="btn btn-secondary" style={{ flex: 1 }}>
                បោះបង់
              </button>
              <button onClick={handleDeleteUser} className="btn btn-danger" style={{ flex: 1 }}>
                លុបចេញ
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
