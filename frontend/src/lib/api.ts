import {
  AIParseResponse,
  AppSetting,
  AuditLogItem,
  Category,
  Counters,
  DailyReport,
  DashboardResponse,
  ExtractedCategory,
  Grade,
  PaginatedResponse,
  SeriesPoint,
  Student,
  StudentExtraction,
  StudentInput,
  TelegramMessage,
  User,
} from '../types'

const BASE_URL = import.meta.env.VITE_API_URL || '/api/v1'

class ApiError extends Error {
  status: number
  code?: string
  details?: any

  constructor(message: string, status: number, code?: string, details?: any) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.details = details
  }
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = localStorage.getItem('scholar_token')
  const headers: Record<string, string> = {
    // FormData sets its own multipart Content-Type (with the boundary).
    ...(options.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
    ...(options.headers as Record<string, string>),
  }

  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const url = endpoint.startsWith('http') ? endpoint : `${BASE_URL}${endpoint}`
  const response = await fetch(url, {
    ...options,
    headers,
  })

  if (response.status === 204) {
    return {} as T
  }

  const contentType = response.headers.get('content-type') || ''
  const isJson = contentType.includes('application/json')

  if (!response.ok) {
    let errorMsg = `សំណើមិនបានសម្រេច (${response.status})`
    let code: string | undefined
    let details: any

    if (isJson) {
      try {
        const data = await response.json()
        errorMsg = data.error?.message || data.detail || data.message || errorMsg
        code = data.error?.code
        details = data.error?.details || data.details
      } catch {
        // fallback
      }
    } else {
      const text = await response.text()
      if (text) errorMsg = text
    }

    if (response.status === 401) {
      localStorage.removeItem('scholar_token')
      localStorage.removeItem('scholar_user')
      if (!window.location.pathname.includes('/login')) {
        window.location.href = '/login'
      }
    }

    throw new ApiError(errorMsg, response.status, code, details)
  }

  if (isJson) {
    return (await response.json()) as T
  }

  return (await response.text()) as unknown as T
}

export const api = {
  // Auth
  async login(login: string, password: string):Promise<{ access_token: string; token_type: string }> {
    return request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ login, password }),
    })
  },

  async getMe(): Promise<User> {
    return request<User>('/auth/me')
  },

  async changePassword(current_password: string, new_password: string): Promise<{ message: string }> {
    return request('/auth/change-password', {
      method: 'POST',
      body: JSON.stringify({ current_password, new_password }),
    })
  },

  // References
  async getCategories(): Promise<{ items: Category[]; total: number }> {
    return request('/references/categories')
  },

  async getGrades(): Promise<{ items: Grade[]; total: number }> {
    return request('/references/grades')
  },

  // Dashboard
  async getDashboard(date?: string, trend_days: number = 30): Promise<DashboardResponse> {
    const params = new URLSearchParams()
    if (date) params.append('date', date)
    params.append('trend_days', trend_days.toString())
    return request(`/dashboard?${params.toString()}`)
  },

  // Daily Reports
  async getTodayReports(report_date?: string): Promise<DailyReport[]> {
    const params = new URLSearchParams()
    if (report_date) params.append('report_date', report_date)
    return request(`/reports/today?${params.toString()}`)
  },

  async getReportsHistory(params: {
    page?: number
    size?: number
    start?: string
    end?: string
    category_id?: string
    category_code?: string
    q?: string
  }): Promise<PaginatedResponse<DailyReport>> {
    const q = new URLSearchParams()
    if (params.page) q.append('page', params.page.toString())
    if (params.size) q.append('size', params.size.toString())
    if (params.start) q.append('start', params.start)
    if (params.end) q.append('end', params.end)
    if (params.category_id) q.append('category_id', params.category_id)
    if (params.category_code) q.append('category_code', params.category_code)
    if (params.q) q.append('q', params.q)
    return request(`/reports/history?${q.toString()}`)
  },

  async getReportDates(start?: string, end?: string): Promise<string[]> {
    const q = new URLSearchParams()
    if (start) q.append('start', start)
    if (end) q.append('end', end)
    return request(`/reports/dates?${q.toString()}`)
  },

  async getReport(id: string): Promise<DailyReport> {
    return request(`/reports/daily/${id}`)
  },

  async createReport(payload: any): Promise<DailyReport> {
    return request('/reports/daily', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  async bulkCreateReports(reports: any[]): Promise<DailyReport[]> {
    return request('/reports/bulk', {
      method: 'POST',
      body: JSON.stringify({ reports }),
    })
  },

  async updateReport(id: string, payload: any): Promise<DailyReport> {
    return request(`/reports/daily/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    })
  },

  async deleteReport(id: string): Promise<void> {
    return request(`/reports/daily/${id}`, {
      method: 'DELETE',
    })
  },

  async getCumulativeSeries(
    start?: string,
    end?: string,
    categoryId?: string
  ): Promise<{ start: string; end: string; points: SeriesPoint[]; grades: Record<string, Counters> }> {
    const q = new URLSearchParams()
    if (start) q.append('start', start)
    if (end) q.append('end', end)
    if (categoryId) q.append('category_id', categoryId)
    return request(`/reports/cumulative/series?${q.toString()}`)
  },

  // Telegram
  async getTelegramPreview(params: {
    date?: string
    include_today_grades?: boolean
    include_grand_total?: boolean
    include_empty_categories?: boolean
    zero_pad?: boolean
    grades?: string[]
  }): Promise<TelegramMessage> {
    const q = new URLSearchParams()
    if (params.date) q.append('date', params.date)
    for (const g of params.grades || []) q.append('grades', g)
    if (params.include_today_grades !== undefined) q.append('include_today_grades', String(params.include_today_grades))
    if (params.include_grand_total !== undefined) q.append('include_grand_total', String(params.include_grand_total))
    if (params.include_empty_categories !== undefined) q.append('include_empty_categories', String(params.include_empty_categories))
    if (params.zero_pad !== undefined) q.append('zero_pad', String(params.zero_pad))
    return request(`/telegram/preview?${q.toString()}`)
  },

  async sendTelegram(payload: {
    report_date: string
    chat_id?: string
    dry_run?: boolean
    include_today_grades?: boolean
    include_grand_total?: boolean
    include_empty_categories?: boolean
    zero_pad?: boolean
    grades?: string[]
  }): Promise<TelegramMessage> {
    return request('/telegram/send', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  async verifyTelegramBot(): Promise<{ ok: boolean; configured?: boolean; username?: string; first_name?: string; message?: string }> {
    return request('/telegram/bot/verify')
  },

  // AI & OCR
  async getAICapabilities(): Promise<{ builtin: boolean; llm: boolean; ocr: boolean; model?: string; languages: string[] }> {
    return request('/ai/capabilities')
  },

  async getAISample(): Promise<{ text: string }> {
    return request('/ai/sample')
  },

  async parseAIText(payload: { text?: string; images?: string[]; provider?: string; current_year?: number }): Promise<AIParseResponse> {
    return request('/ai/parse', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  async applyAIExtraction(payload: {
    report_date: string
    categories: ExtractedCategory[]
    dry_run: boolean
  }): Promise<Record<string, unknown>> {
    return request('/ai/apply', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  // Exports
  async exportData(format: 'excel' | 'pdf' | 'csv' | 'telegram', requestData: {
    start?: string
    end?: string
    category_id?: string
    academic_year?: number
  }): Promise<Blob> {
    const token = localStorage.getItem('scholar_token')
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    }
    if (token) headers['Authorization'] = `Bearer ${token}`

    const res = await fetch(`${BASE_URL}/export/${format}`, {
      method: 'POST',
      headers,
      body: JSON.stringify(requestData),
    })

    if (!res.ok) {
      throw new Error(`ការនាំចេញមិនបានសម្រេច (${res.status})`)
    }

    return res.blob()
  },

  // Settings
  async getSettings(): Promise<AppSetting[]> {
    return request('/settings')
  },

  async getCurrentYear(): Promise<{ current_year: number }> {
    return request('/settings/current-year')
  },

  async setCurrentYear(current_year: number): Promise<{ message: string }> {
    return request('/settings/current-year', {
      method: 'PUT',
      body: JSON.stringify({ current_year }),
    })
  },

  async updateSetting(key: string, value: any): Promise<AppSetting> {
    return request(`/settings/${key}`, {
      method: 'PUT',
      body: JSON.stringify({ value }),
    })
  },

  async updateCategoryTitle(category_id: string, title_template: string): Promise<Category> {
    return request(`/settings/categories/${category_id}/title`, {
      method: 'PUT',
      body: JSON.stringify({ title_template }),
    })
  },

  // Students
  async getStudents(params: {
    page?: number
    size?: number
    academic_year?: number
    q?: string
    gender?: string
    grade?: string
    stream?: string
  }): Promise<PaginatedResponse<Student>> {
    const q = new URLSearchParams()
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== '') q.append(k, String(v))
    }
    return request(`/students?${q.toString()}`)
  },

  async createStudent(payload: StudentInput): Promise<Student> {
    return request('/students', { method: 'POST', body: JSON.stringify(payload) })
  },

  async updateStudent(id: string, payload: Partial<StudentInput>): Promise<Student> {
    return request(`/students/${id}`, { method: 'PATCH', body: JSON.stringify(payload) })
  },

  async deleteStudent(id: string): Promise<void> {
    return request(`/students/${id}`, { method: 'DELETE' })
  },

  /** OCR one application form; returns fields to review. Nothing is saved. */
  async extractStudent(file: File, signal?: AbortSignal): Promise<StudentExtraction> {
    const body = new FormData()
    body.append('file', file)
    return request('/students/extract', { method: 'POST', body, signal })
  },

  /** The photo as a Blob. <img src> can't send the bearer token, so fetch it. */
  async getStudentPhoto(id: string, version?: string | null): Promise<Blob> {
    const token = localStorage.getItem('scholar_token')
    const v = version ? `?v=${encodeURIComponent(version)}` : ''
    const res = await fetch(`${BASE_URL}/students/${id}/photo${v}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
    if (!res.ok) throw new ApiError(`រកមិនឃើញរូបថត (${res.status})`, res.status)
    return res.blob()
  },

  async setStudentPhoto(id: string, photo: Blob): Promise<Student> {
    const body = new FormData()
    body.append('file', photo, 'photo.jpg')
    return request(`/students/${id}/photo`, { method: 'PUT', body })
  },

  async deleteStudentPhoto(id: string): Promise<Student> {
    return request(`/students/${id}/photo`, { method: 'DELETE' })
  },

  // Users
  async getUsers(page: number = 1, size: number = 50): Promise<PaginatedResponse<User>> {
    return request(`/users?page=${page}&size=${size}`)
  },

  async createUser(payload: { email: string; username: string; full_name: string; password: string; role: string }): Promise<User> {
    return request('/users', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  },

  async updateUser(id: string, payload: Partial<User>): Promise<User> {
    return request(`/users/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    })
  },

  async resetUserPassword(id: string, new_password: string): Promise<{ message: string }> {
    return request(`/users/${id}/password`, {
      method: 'POST',
      body: JSON.stringify({ new_password }),
    })
  },

  async deleteUser(id: string): Promise<void> {
    return request(`/users/${id}`, {
      method: 'DELETE',
    })
  },

  // Audit Logs
  async getAuditLogs(params: {
    page?: number
    size?: number
    action?: string
    entity_type?: string
    start?: string
    end?: string
    q?: string
  }): Promise<PaginatedResponse<AuditLogItem>> {
    const q = new URLSearchParams()
    if (params.page) q.append('page', params.page.toString())
    if (params.size) q.append('size', params.size.toString())
    if (params.action) q.append('action', params.action)
    if (params.entity_type) q.append('entity_type', params.entity_type)
    if (params.start) q.append('start', params.start)
    if (params.end) q.append('end', params.end)
    if (params.q) q.append('q', params.q)
    return request(`/audit?${q.toString()}`)
  },

  // Health probe
  async getHealth(): Promise<{ status: string; database: boolean }> {
    return request<{ status: string; database: boolean }>('/health')
  },
}
