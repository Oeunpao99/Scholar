import React, { useEffect, useState } from 'react'
import {
  Users,
  TrendingUp,
  UserCheck,
  Building2,
  Send,
  FilePlus,
  Download,
  ChevronRight
} from 'lucide-react'
import { api } from '../lib/api'
import { DashboardResponse } from '../types'
import { DatePicker } from '../components/ui/DatePicker'

interface DashboardPageProps {
  onNavigate: (tab: string, dateParam?: string) => void
}

export const DashboardPage: React.FC<DashboardPageProps> = ({ onNavigate }) => {
  const [data, setData] = useState<DashboardResponse | null>(null)
  const [selectedDate, setSelectedDate] = useState<string>('')
  const [error, setError] = useState<string | null>(null)

  const fetchDashboard = async (targetDate?: string) => {
    setError(null)
    try {
      const res = await api.getDashboard(targetDate)
      setData(res)
      if (!selectedDate && res.generated_for) {
        setSelectedDate(res.generated_for)
      }
    } catch (err: any) {
      setError(err.message || 'បរាជ័យក្នុងការផ្ទុកផ្ទាំងគ្រប់គ្រង')
    }
  }

  useEffect(() => {
    fetchDashboard(selectedDate || undefined)
  }, [selectedDate])

  const headline = data?.headline || { total: 0, female: 0, pp: 0, kp: 0 }
  const today = data?.today || { total: 0, female: 0, pp: 0, kp: 0 }
  const gender = data?.gender || { male: 0, female: 0, male_pct: 0, female_pct: 0 }
  const provinces = data?.provinces || { pp: 0, kp: 0, pp_pct: 0, kp_pct: 0 }

  return (
    <div className="animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Page Header */}
      <div className="page-header" style={{ alignItems: 'center' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
            <h1 className="page-title">
              ផ្ទាំងគ្រប់គ្រងទិន្នន័យចុះឈ្មោះ
            </h1>
            <span className="badge badge-blue" style={{ fontSize: '0.75rem' }}>
              ឆ្នាំ {data?.current_year || 2026}
            </span>
          </div>
          <p className="page-subtitle hide-phone">
            ទិដ្ឋភាពរួមនៃការទទួលពាក្យសុំចុះឈ្មោះនិស្សិតប្រចាំថ្ងៃ និងសរុបទាំងអស់
          </p>
        </div>

        {/* Action Controls */}
        <div className="page-actions dash-actions">
          {/* Date Selector */}
          <DatePicker className="dash-date" ariaLabel="កាលបរិច្ឆេទ" value={selectedDate} onChange={setSelectedDate} />

          <button
            onClick={() => onNavigate('daily-entry', selectedDate)}
            className="btn btn-primary btn-sm"
          >
            <FilePlus size={15} />
            <span>បញ្ចូលទិន្នន័យ</span>
          </button>

          <button
            onClick={() => onNavigate('telegram', selectedDate)}
            className="btn btn-secondary btn-sm"
            title="ផ្ញើទម្រង់ Telegram"
          >
            <Send size={14} color="var(--sky-primary)" />
            <span>Telegram</span>
          </button>

          <button
            onClick={() => onNavigate('exports')}
            className="btn btn-secondary btn-sm"
            title="ទាញយកឯកសារ"
          >
            <Download size={14} />
            <span>ទាញយក</span>
          </button>
        </div>
      </div>

      {error && (
        <div style={{ padding: '12px 16px', background: 'var(--rose-soft)', border: '1px solid var(--rose-border)', borderRadius: 'var(--radius-md)', color: 'var(--rose-primary)', fontSize: '0.875rem' }}>
          {error}
        </div>
      )}

      {/* 4 Clean Metric Cards (No glowing orbs, no containers inside containers) */}
      <div className="dash-metrics" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '16px' }}>
        {/* Metric 1 */}
        <div className="glass-panel" style={{ padding: '18px 20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
            <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)' }}>សរុបទាំងអស់</span>
            <TrendingUp size={16} color="var(--sky-primary)" />
          </div>
          <div style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--text-main)', fontFamily: 'var(--font-sans)', letterSpacing: '-0.02em', lineHeight: 1.1 }}>
            {headline.total.toLocaleString()}
          </div>
          <div style={{ fontSize: '0.8rem', color: 'var(--emerald-primary)', fontWeight: 600, marginTop: '6px' }}>
            +{today.total} ថ្ងៃនេះ
          </div>
        </div>

        {/* Metric 2 */}
        <div className="glass-panel" style={{ padding: '18px 20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
            <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)' }}>កើនថ្ងៃនេះ</span>
            <Users size={16} color="var(--cyan-primary)" />
          </div>
          <div style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--sky-primary)', fontFamily: 'var(--font-sans)', letterSpacing: '-0.02em', lineHeight: 1.1 }}>
            +{today.total.toLocaleString()}
          </div>
          <div className="hide-phone" style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '6px' }}>
            ស្រី: <strong style={{ color: 'var(--text-main)' }}>{today.female}</strong> • ភ្នំពេញ: <strong style={{ color: 'var(--text-main)' }}>{today.pp}</strong> • ខេត្ត: <strong style={{ color: 'var(--text-main)' }}>{today.kp}</strong>
          </div>
        </div>

        {/* Metric 3 */}
        <div className="glass-panel" style={{ padding: '18px 20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
            <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)' }}>និស្សិតស្រី</span>
            <UserCheck size={16} color="var(--rose-primary)" />
          </div>
          <div style={{ fontSize: '2rem', fontWeight: 800, color: 'var(--text-main)', fontFamily: 'var(--font-sans)', letterSpacing: '-0.02em', lineHeight: 1.1 }}>
            {headline.female.toLocaleString()}
          </div>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '6px' }}>
            <strong style={{ color: 'var(--rose-primary)' }}>{Math.round(gender.female_pct)}%</strong> នៃចំនួនសរុប
          </div>
        </div>

        {/* Metric 4 */}
        <div className="glass-panel" style={{ padding: '18px 20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
            <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)' }}>រាជធានី-ខេត្ត</span>
            <Building2 size={16} color="var(--emerald-primary)" />
          </div>
          <div style={{ fontSize: '1.45rem', fontWeight: 800, color: 'var(--text-main)', fontFamily: 'var(--font-sans)', letterSpacing: '-0.01em', lineHeight: 1.2 }}>
            {headline.pp.toLocaleString()} <span style={{ color: 'var(--text-dim)', fontWeight: 400 }}>/</span> {headline.kp.toLocaleString()}
            <div style={{ fontSize: '0.75rem', fontWeight: 500, color: 'var(--text-muted)', letterSpacing: 0 }}>ភ្នំពេញ / ខេត្ត</div>
          </div>
          <div className="hide-phone" style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '6px' }}>
            ភ្នំពេញ {provinces.pp_pct}% • ខេត្ត {provinces.kp_pct}%
          </div>
        </div>
      </div>

      {/* Clean Category Ledger Table (Replacing 3 bulky cards and 15 nested chips) */}
      <div className="glass-panel dash-ledger" style={{ padding: '20px 24px', overflow: 'hidden' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px', flexWrap: 'wrap', marginBottom: '16px' }}>
          <div>
            <h2 style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text-main)' }}>
              តារាងសង្ខេបតាមប្រភេទពាក្យស្នើសុំ
            </h2>
            <p className="hide-phone" style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              ទិន្នន័យលម្អិតបែងចែកតាមផ្នែក និទ្ទេស និងរាជធានី-ខេត្ត
            </p>
          </div>
          <button
            onClick={() => onNavigate('reports')}
            className="btn btn-secondary btn-sm"
          >
            <span>ប្រវត្តិរបាយការណ៍</span>
            <ChevronRight size={14} />
          </button>
        </div>

        <div style={{ overflowX: 'auto' }}>
          <table className="ledger-table" style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.875rem' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-subtle)', color: 'var(--text-muted)' }}>
                <th style={{ padding: '10px 12px', fontWeight: 600 }}>ប្រភេទពាក្យ</th>
                <th style={{ padding: '10px 12px', fontWeight: 600, textAlign: 'center' }}>ថ្ងៃនេះ</th>
                <th style={{ padding: '10px 12px', fontWeight: 600, textAlign: 'center' }}>ខែនេះ</th>
                <th style={{ padding: '10px 12px', fontWeight: 600, textAlign: 'center' }}>ភ្នំពេញ</th>
                <th style={{ padding: '10px 12px', fontWeight: 600, textAlign: 'center' }}>ខេត្ត</th>
                <th style={{ padding: '10px 12px', fontWeight: 600 }}>និទ្ទេស (A - E)</th>
                <th style={{ padding: '10px 12px', fontWeight: 600, textAlign: 'right' }}>សរុបទាំងអស់</th>
              </tr>
            </thead>
            <tbody>
              {(data?.categories || []).map((cat) => (
                <tr
                  key={cat.category_id}
                  className={cat.cumulative.total === 0 && cat.today.total === 0 ? 'ledger-empty' : undefined}
                  style={{ borderBottom: '1px solid var(--table-border)', transition: 'background-color 0.15s ease' }}
                  onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'var(--table-hover)'}
                  onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                >
                  <td className="ledger-title" style={{ padding: '14px 12px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span className="badge badge-blue" style={{ fontSize: '0.7rem' }}>
                        {cat.roman_numeral}
                      </span>
                      <span style={{ fontWeight: 600, color: 'var(--text-main)' }}>
                        {cat.title}
                      </span>
                    </div>
                  </td>
                  <td data-label="ថ្ងៃនេះ" style={{ padding: '14px 12px', textAlign: 'center' }}>
                    <span style={{ fontWeight: 700, color: 'var(--sky-primary)' }}>
                      +{cat.today.total}
                    </span>
                    <span className="hide-phone" style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginLeft: '4px' }}>
                      (ស្រី {cat.today.female})
                    </span>
                  </td>
                  <td data-label="ខែនេះ" style={{ padding: '14px 12px', textAlign: 'center', fontWeight: 600, color: 'var(--text-main)' }}>
                    {cat.month.total}
                  </td>
                  <td data-label="ភ្នំពេញ" style={{ padding: '14px 12px', textAlign: 'center', color: 'var(--text-muted)' }}>
                    {cat.cumulative.pp}
                  </td>
                  <td data-label="ខេត្ត" style={{ padding: '14px 12px', textAlign: 'center', color: 'var(--text-muted)' }}>
                    {cat.cumulative.kp}
                  </td>
                  <td className="ledger-grades" style={{ padding: '14px 12px' }}>
                    <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                      {['A', 'B', 'C', 'D', 'E'].map((g) => {
                        const count = cat.cumulative_grades?.[g]?.total || 0
                        return (
                          <span key={g} style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', opacity: count > 0 ? 1 : 0.45 }}>
                            <span className="grade-pill-dot" style={{ background: `var(--grade-${g})` }} />
                            <strong style={{ color: 'var(--text-main)' }}>{g}</strong> {count}
                          </span>
                        )
                      })}
                    </div>
                  </td>
                  <td className="ledger-total" style={{ padding: '14px 12px', textAlign: 'right' }}>
                    <span style={{ fontSize: '1.1rem', fontWeight: 800, color: 'var(--text-main)', fontFamily: 'var(--font-sans)' }}>
                      {cat.cumulative.total.toLocaleString()}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
