export type Role = 'superadmin' | 'admin' | 'manager' | 'staff' | 'viewer'

export interface User {
  id: string
  email: string
  username: string
  full_name: string
  role: Role
  is_active: boolean
  is_superuser: boolean
  created_at?: string
  last_login?: string
}

export interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  isLoading: boolean
}

export interface Counters {
  total: number
  female: number
  pp: number
  kp: number
}

export interface Category {
  id: string
  code: string
  position: number
  roman_numeral: string
  title_template: string
  title: string
  is_active: boolean
  description?: string
}

export interface Grade {
  id: string
  code: 'A' | 'B' | 'C' | 'D' | 'E'
  position: number
  label?: string
  is_active: boolean
  description?: string
}

export interface GradeEntry {
  id?: string
  grade: 'A' | 'B' | 'C' | 'D' | 'E'
  position?: number
  total: number
  female: number
  pp: number
  kp: number
}

export interface DailyReport {
  id: string
  report_date: string
  category_id: string
  category_code?: string
  category_title?: string
  roman_numeral?: string
  today: Counters
  cumulative: Counters
  today_total?: number
  today_female?: number
  today_pp?: number
  today_kp?: number
  grades: GradeEntry[]
  grade_cumulative?: Record<string, Counters>
  note?: string | null
  source?: string
  is_locked?: boolean
  male?: number
  is_consistent?: boolean
  created_by?: string
  created_by_username?: string
  created_at?: string
  updated_at?: string
}

export interface PageMeta {
  page: number
  size: number
  total: number
  total_pages: number
  has_next: boolean
  has_prev: boolean
}

export interface PaginatedResponse<T> {
  items: T[]
  meta: PageMeta
}

// Mirrors backend app/schemas/analytics.py
export interface DashboardResponse {
  generated_for: string
  current_year: number
  headline: Counters
  today: Counters
  month: Counters
  year: Counters
  gender: {
    male: number
    female: number
    male_pct: number
    female_pct: number
  }
  provinces: {
    pp: number
    kp: number
    pp_pct: number
    kp_pct: number
  }
  categories: Array<{
    category_id: string
    category_code: string
    title: string
    roman_numeral: string
    position: number
    today: Counters
    month: Counters
    year: Counters
    cumulative: Counters
    cumulative_grades: Record<string, Counters>
  }>
  daily_trend: Array<{
    date: string
    total: number
    female: number
    male: number
    pp: number
    kp: number
  }>
  recent_activities: Array<{
    id: string
    action: string
    entity_type: string
    summary?: string
    created_at?: string
    user_email?: string
  }>
  has_report_today: boolean
}

// Mirrors backend app/schemas/student.py
export type StudentGender = 'M' | 'F'
export type StudentStream = 'science' | 'social_science'

export interface Student {
  id: string
  academic_year: number
  full_name: string
  gender: StudentGender
  grade?: 'A' | 'B' | 'C' | 'D' | 'E' | null
  score_rank?: number | null
  high_school?: string | null
  stream?: StudentStream | null
  university?: string | null
  major?: string | null
  phone?: string | null
  note?: string | null
  created_at?: string
  updated_at?: string
}

export type StudentInput = Omit<Student, 'id' | 'created_at' | 'updated_at' | 'academic_year'> & {
  academic_year?: number
}

// /reports/cumulative/series — running totals plus that day's own gain.
export interface SeriesPoint {
  date: string
  total: number
  female: number
  male: number
  pp: number
  kp: number
  gain: Counters
}

export interface TelegramMessage {
  report_date: string
  text: string
  sent: boolean
  chat_id?: string
  sent_at?: string
}

// Mirrors backend app/schemas/ai.py
export interface ExtractedGrade {
  grade: string
  total: number
  female: number
  pp: number
  kp: number
}

export interface ExtractedCategory {
  category: string // current_year | before_current_year | other_province
  title?: string | null
  total: number
  female: number
  male: number
  pp: number
  kp: number
  grades: ExtractedGrade[]
}

export interface ExtractedReport {
  date?: string | null
  current_year?: number | null
  categories: ExtractedCategory[]
  source_language?: string | null
  confidence: number
  warnings: string[]
}

export interface AIParseResponse {
  provider: string
  extracted: ExtractedReport
  preview_text?: string | null
  ocr_text?: string | null
  raw_response?: string | null
}

export interface AuditLogItem {
  id: string
  user_id?: string
  user_email?: string
  action: string
  entity_type: string
  entity_id?: string
  summary?: string
  changes?: Record<string, any>
  ip_address?: string
  user_agent?: string
  created_at?: string
}

export interface AppSetting {
  key: string
  value: any
  value_type: string
  description?: string
  is_secret?: boolean
  updated_at?: string
}
