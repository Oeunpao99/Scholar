import React from 'react'
import { CategoryGain } from './CategoryGenderBars'

interface Props {
  total: number
  female: number
  categories: CategoryGain[]
}

const pct = (part: number, whole: number) => (whole > 0 ? Math.round((part / whole) * 100) : 0)

/** Girls vs boys for the current range, plus a few plain-language takeaways. */
export const GenderSplit: React.FC<Props> = ({ total, female, categories }) => {
  if (total === 0) return <div className="chart-empty">មិនទាន់មានសិស្សថ្មីក្នុងចន្លោះកាលបរិច្ឆេទនេះ</div>

  const male = total - female
  const fPct = pct(female, total)
  const mPct = 100 - fPct
  const withData = categories.filter((c) => c.total > 0)
  const biggest = [...withData].sort((a, b) => b.total - a.total)[0]
  const mostFemale = [...withData].sort((a, b) => b.female / b.total - a.female / a.total)[0]
  const gap = Math.abs(female - male)

  const insights: string[] = [
    gap === 0
      ? 'សិស្សស្រី និងប្រុសមានចំនួនស្មើគ្នា'
      : female > male
        ? `សិស្សស្រីច្រើនជាងប្រុស ${gap} នាក់`
        : `សិស្សប្រុសច្រើនជាងស្រី ${gap} នាក់`,
  ]
  if (biggest && withData.length > 1) {
    insights.push(`${biggest.roman} ${biggest.title} មានសិស្សថ្មីច្រើនជាងគេ (${biggest.total} នាក់ · ${pct(biggest.total, total)}%)`)
  }
  if (mostFemale && withData.length > 1) {
    insights.push(`ភាគរយស្រីខ្ពស់ជាងគេ៖ ${mostFemale.roman} ${mostFemale.title} (${pct(mostFemale.female, mostFemale.total)}%)`)
  }

  return (
    <div className="gs-chart">
      <div className="gs-figures">
        <div>
          <div className="gs-label"><i style={{ background: 'var(--gender-f)' }} />ស្រី</div>
          <div className="gs-value">{female}</div>
          <div className="gs-pct">{fPct}%</div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div className="gs-label" style={{ justifyContent: 'flex-end' }}><i style={{ background: 'var(--gender-m)' }} />ប្រុស</div>
          <div className="gs-value">{male}</div>
          <div className="gs-pct">{mPct}%</div>
        </div>
      </div>
      <div className="gs-bar" role="img" aria-label={`ស្រី ${female} (${fPct}%), ប្រុស ${male} (${mPct}%)`}>
        {female > 0 && <span style={{ flexGrow: female, background: 'var(--gender-f)' }} title={`ស្រី ${female}`} />}
        {male > 0 && <span style={{ flexGrow: male, background: 'var(--gender-m)' }} title={`ប្រុស ${male}`} />}
      </div>
      <ul className="gs-insights">
        {insights.map((t) => <li key={t}>{t}</li>)}
      </ul>
    </div>
  )
}
