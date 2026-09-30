import {
  LayoutDashboard,
  FilePlus,
  History,
  Send,
  BarChart3,
  Settings,
  Users,
  ShieldCheck,
  LucideIcon,
} from 'lucide-react'
import { Role } from '../../types'

export interface NavItem {
  id: string
  label: string
  icon: LucideIcon
  roles?: Role[]
}

export interface NavSection {
  title?: string
  items: NavItem[]
}

export const NAV_SECTIONS: NavSection[] = [
  {
    items: [
      { id: 'dashboard', label: 'ផ្ទាំងគ្រប់គ្រង', icon: LayoutDashboard },
      { id: 'daily-entry', label: 'បញ្ចូលទិន្នន័យថ្ងៃនេះ', icon: FilePlus },
      { id: 'reports', label: 'ប្រវត្តិរបាយការណ៍', icon: History },
    ],
  },
  {
    title: 'ផ្សព្វផ្សាយ និងស្វ័យប្រវត្តិ',
    items: [
      { id: 'telegram', label: 'របាយការណ៍ Telegram', icon: Send },
      // Hidden until needed; the page and its route in App.tsx are kept.
      // { id: 'ai-assistant', label: 'ជំនួយការស្កេនទិន្នន័យ', icon: Sparkles },
    ],
  },
  {
    title: 'ការវិភាគ',
    items: [{ id: 'exports', label: 'ការវិភាគ និងនាំចេញ', icon: BarChart3 }],
  },
  {
    title: 'ការគ្រប់គ្រង',
    items: [
      { id: 'users', label: 'អ្នកប្រើប្រាស់', icon: Users, roles: ['superadmin', 'admin'] },
      { id: 'audit', label: 'កំណត់ហេតុសវនកម្ម', icon: ShieldCheck, roles: ['superadmin', 'admin'] },
      { id: 'settings', label: 'ការកំណត់', icon: Settings },
    ],
  },
]

export const PAGE_TITLES: Record<string, string> = Object.fromEntries(
  NAV_SECTIONS.flatMap((s) => s.items).map((i) => [i.id, i.label])
)

export const ROLE_LABELS: Record<string, string> = {
  superadmin: 'អ្នកគ្រប់គ្រងជាន់ខ្ពស់',
  admin: 'អ្នករៀបចំប្រព័ន្ធ',
  manager: 'អ្នកគ្រប់គ្រង',
  staff: 'បុគ្គលិក',
  viewer: 'អ្នកមើល',
}
