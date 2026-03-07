import { useEffect, useEffectEvent, useRef, useState } from 'react'
import './App.css'

const defaultScenario = {
  jurisdiction: 'BC',
  children: '2',
  childrenUnderSix: '0',
  taxYear: '2023',
  payorIncome: '244658',
  recipientIncome: '30600',
  targetMinPercent: '40',
  targetMaxPercent: '46',
}

const baseTaxYear = 2023
const defaultExtrapolationRate = 0.025
const combinedApproxTaxBrackets2023 = [
  [0, 45654, 20.06],
  [45654, 53359, 22.7],
  [53359, 91310, 28.2],
  [91310, 104835, 31.0],
  [104835, 106717, 32.79],
  [106717, 127299, 38.29],
  [127299, 165430, 40.7],
  [165430, 172602, 44.02],
  [172602, 235675, 46.12],
  [235675, 240716, 49.8],
  [240716, Number.POSITIVE_INFINITY, 53.5],
]
const knownTaxYearIndexFactors = {
  2017: 45916 / 53359,
  2018: 46605 / 53359,
  2019: 47630 / 53359,
  2020: 48535 / 53359,
  2021: 49020 / 53359,
  2022: 50197 / 53359,
  2023: 1,
  2024: 55867 / 53359,
  2025: 57375 / 53359,
}

function formatCurrency(value) {
  return new Intl.NumberFormat('en-CA', {
    style: 'currency',
    currency: 'CAD',
    maximumFractionDigits: 0,
  }).format(value ?? 0)
}

function formatPercent(value) {
  return `${Number(value ?? 0).toFixed(2)}%`
}

function formatSignedCurrency(value) {
  if (value > 0) {
    return `+${formatCurrency(value)}`
  }
  if (value < 0) {
    return `-${formatCurrency(Math.abs(value))}`
  }
  return formatCurrency(0)
}

function asNumber(value, fallback = 0) {
  return Number.isFinite(Number(value)) ? Number(value) : fallback
}

function resolveTaxYearIndexFactor(taxYear) {
  if (taxYear in knownTaxYearIndexFactors) {
    return knownTaxYearIndexFactors[taxYear]
  }

  const knownYears = Object.keys(knownTaxYearIndexFactors).map(Number)
  const minYear = Math.min(...knownYears)
  const maxYear = Math.max(...knownYears)

  if (taxYear < minYear) {
    const years = minYear - taxYear
    return knownTaxYearIndexFactors[minYear] / (1 + defaultExtrapolationRate) ** years
  }

  const years = taxYear - maxYear
  return knownTaxYearIndexFactors[maxYear] * (1 + defaultExtrapolationRate) ** years
}

function calculateApproxBcTax(income, taxYear) {
  const normalizedIncome = Math.max(asNumber(income), 0)
  const factor = resolveTaxYearIndexFactor(taxYear)
  let tax = 0

  for (const [lower, upper, rate] of combinedApproxTaxBrackets2023) {
    const indexedLower = lower * factor
    const indexedUpper = upper === Number.POSITIVE_INFINITY ? upper : upper * factor
    if (normalizedIncome <= indexedLower) {
      break
    }

    const taxableAmount = Math.min(normalizedIncome, indexedUpper) - indexedLower
    tax += taxableAmount * rate / 100
  }

  return Number(tax.toFixed(2))
}

async function postJson(url, payload) {
  const response = await fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })

  const data = await response.json()
  if (!response.ok) {
    throw new Error(data.error ?? 'Request failed.')
  }

  return data
}

function DetailList({ items, emphasis = false }) {
  return (
    <dl className={`detail-list${emphasis ? ' detail-list--emphasis' : ''}`}>
      {items.map((item) => (
        <div key={item.label} className="detail-list__row">
          <dt>{item.label}</dt>
          <dd>{item.value}</dd>
        </div>
      ))}
    </dl>
  )
}

function ResultTable({ caption, columns, rows }) {
  return (
    <div className="table-wrap">
      <table className="data-table">
        <caption>{caption}</caption>
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column}>{column}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row[0]}>
              {row.map((cell) => (
                <td key={cell}>{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function App() {
  const [metadata, setMetadata] = useState(null)
  const [scenario, setScenario] = useState(defaultScenario)
  const [autoRecalculate, setAutoRecalculate] = useState(true)
  const [netIncomePeriod, setNetIncomePeriod] = useState('annual')
  const [childResult, setChildResult] = useState(null)
  const [spousalResult, setSpousalResult] = useState(null)
  const [childError, setChildError] = useState('')
  const [spousalError, setSpousalError] = useState('')
  const [metadataError, setMetadataError] = useState('')
  const [isCalculating, setIsCalculating] = useState(false)
  const requestSequence = useRef(0)

  useEffect(() => {
    let active = true

    async function loadMetadata() {
      const response = await fetch('/api/metadata')
      const data = await response.json()
      if (!response.ok) {
        throw new Error(data.error ?? 'Unable to load calculator metadata.')
      }

      if (active) {
        setMetadata(data)
      }
    }

    loadMetadata().catch((error) => {
      if (active) {
        setMetadataError(error.message)
      }
    })

    return () => {
      active = false
    }
  }, [])

  async function submitScenario(activeScenario) {
    const requestId = requestSequence.current + 1
    requestSequence.current = requestId
    setIsCalculating(true)
    setChildError('')
    setSpousalError('')

    const payload = {
      jurisdiction: activeScenario.jurisdiction,
      children: Number(activeScenario.children),
      childrenUnderSix: Number(activeScenario.childrenUnderSix),
      taxYear: Number(activeScenario.taxYear),
      payorIncome: Number(activeScenario.payorIncome),
      recipientIncome: Number(activeScenario.recipientIncome),
    }

    const [childResponse, spousalResponse] = await Promise.allSettled([
      postJson('/api/calculate/child-support', payload),
      postJson('/api/calculate/spousal-support', {
        ...payload,
        targetMinPercent: Number(activeScenario.targetMinPercent),
        targetMaxPercent: Number(activeScenario.targetMaxPercent),
      }),
    ])

    if (requestId !== requestSequence.current) {
      return
    }

    if (childResponse.status === 'fulfilled') {
      setChildResult(childResponse.value)
    } else {
      setChildResult(null)
      setChildError(childResponse.reason.message)
    }

    if (spousalResponse.status === 'fulfilled') {
      setSpousalResult(spousalResponse.value)
    } else {
      setSpousalResult(null)
      setSpousalError(spousalResponse.reason.message)
    }

    setIsCalculating(false)
  }

  const submitCurrentScenario = useEffectEvent((activeScenario) => {
    const requiredFields = [
      activeScenario.children,
      activeScenario.childrenUnderSix,
      activeScenario.taxYear,
      activeScenario.payorIncome,
      activeScenario.recipientIncome,
      activeScenario.targetMinPercent,
      activeScenario.targetMaxPercent,
    ]
    if (requiredFields.some((value) => value === '')) {
      return
    }

    void submitScenario(activeScenario)
  })

  useEffect(() => {
    if (!metadata || !autoRecalculate) {
      return
    }

    submitCurrentScenario(scenario)
  }, [autoRecalculate, metadata, scenario])

  function handleScenarioChange(event) {
    const { name, value } = event.target
    setScenario((current) => {
      if (name === 'children') {
        const nextChildren = value
        const nextChildrenUnderSix = Math.min(
          Number(current.childrenUnderSix || 0),
          Number(nextChildren || 0),
        )
        return {
          ...current,
          children: nextChildren,
          childrenUnderSix: String(nextChildrenUnderSix),
        }
      }

      if (name === 'childrenUnderSix') {
        const boundedValue = Math.min(Number(value || 0), Number(current.children || 0))
        return { ...current, childrenUnderSix: String(Math.max(boundedValue, 0)) }
      }

      return { ...current, [name]: value }
    })
  }

  function handleSubmit(event) {
    event.preventDefault()
    void submitScenario(scenario)
  }

  function handleReset() {
    setScenario(defaultScenario)
  }

  const supportedChildren = metadata?.supportedChildren ?? []
  const childRows = childResult
    ? [
        ['Payor', formatCurrency(childResult.payorMonthly), formatCurrency(childResult.payorAnnual)],
        [
          'Recipient',
          formatCurrency(childResult.recipientMonthly),
          formatCurrency(childResult.recipientAnnual),
        ],
        ['Net transfer', formatCurrency(childResult.netMonthly), formatCurrency(childResult.netAnnual)],
      ]
    : []
  const spousalHistoryRows =
    spousalResult?.history.slice(-6).map((entry) => [
      `#${entry.iteration}`,
      formatCurrency(entry.spousalSupportAnnual),
      formatPercent(entry.recipientSharePercent),
    ]) ?? []
  const payorGrossIncome = spousalResult ? asNumber(spousalResult.payorIncome) : 0
  const spousalSupportAnnual = spousalResult
    ? asNumber(spousalResult.estimatedSpousalSupportAnnual)
    : 0
  const childSupportAnnual = spousalResult
    ? asNumber(spousalResult.childSupport?.netAnnual)
    : 0
  const payorNetIncome = spousalResult ? asNumber(spousalResult.ndiPayor) : 0
  const payorBenefitBreakdown = spousalResult?.benefits?.payor ?? {
    canadaChildBenefitAnnual: 0,
    gstHstCreditAnnual: 0,
    bcFamilyBenefitAnnual: 0,
    bcClimateActionCreditAnnual: 0,
    totalAnnual: 0,
  }
  const recipientBenefitBreakdown = spousalResult?.benefits?.recipient ?? {
    canadaChildBenefitAnnual: 0,
    gstHstCreditAnnual: 0,
    bcFamilyBenefitAnnual: 0,
    bcClimateActionCreditAnnual: 0,
    totalAnnual: 0,
  }
  const activeTaxYear = spousalResult ? asNumber(spousalResult.taxYear, baseTaxYear) : baseTaxYear
  const recipientGrossIncome = spousalResult ? asNumber(spousalResult.recipientIncome) : 0
  const recipientNetIncome = spousalResult ? asNumber(spousalResult.ndiRecipient) : 0
  const payorTaxAfterSupport = spousalResult
    ? asNumber(
        spousalResult.payorTax,
        calculateApproxBcTax(payorGrossIncome - spousalSupportAnnual, activeTaxYear),
      )
    : 0
  const payorTaxBeforeSupportDeduction = spousalResult
    ? asNumber(
        spousalResult.payorTaxBeforeSupportDeduction,
        calculateApproxBcTax(payorGrossIncome, activeTaxYear),
      )
    : 0
  const payorTaxDeductionBenefit = spousalResult
    ? asNumber(
        spousalResult.payorTaxDeductionBenefit,
        Math.max(payorTaxBeforeSupportDeduction - payorTaxAfterSupport, 0),
      )
    : 0
  const payorGovernmentBenefits = spousalResult
    ? asNumber(payorBenefitBreakdown.totalAnnual)
    : 0
  const recipientGovernmentBenefits = spousalResult
    ? asNumber(recipientBenefitBreakdown.totalAnnual)
    : 0
  const recipientTaxBeforeSupportInclusion = spousalResult
    ? asNumber(
        spousalResult.recipientTaxBeforeSupportInclusion,
        calculateApproxBcTax(recipientGrossIncome, activeTaxYear),
      )
    : 0
  const recipientTaxSupportCost = spousalResult
    ? asNumber(
        spousalResult.recipientTaxSupportCost,
        Math.max(
          asNumber(
            spousalResult.recipientTax,
            calculateApproxBcTax(recipientGrossIncome + spousalSupportAnnual, activeTaxYear),
          ) - recipientTaxBeforeSupportInclusion,
          0,
        ),
      )
    : 0
  const netIncomeDivisor = netIncomePeriod === 'monthly' ? 12 : 1
  const netIncomeColumnLabel = netIncomePeriod === 'monthly' ? 'Monthly amount' : 'Annual amount'
  const netIncomeRawRows = spousalResult
    ? [
        ['Gross income', payorGrossIncome, recipientGrossIncome],
        ['Child support', -childSupportAnnual, childSupportAnnual],
        ['Spousal support (pre-tax)', -spousalSupportAnnual, spousalSupportAnnual],
        ['Spousal support (tax deduction)', payorTaxDeductionBenefit, -recipientTaxSupportCost],
        ['Income tax', -payorTaxBeforeSupportDeduction, -recipientTaxBeforeSupportInclusion],
        ...((payorGovernmentBenefits > 0 || recipientGovernmentBenefits > 0)
          ? [['Government benefits', payorGovernmentBenefits, recipientGovernmentBenefits]]
          : []),
        ['Estimated net income', payorNetIncome, recipientNetIncome],
      ]
    : []
  const netIncomeDisplayRows = netIncomeRawRows.map(([label, payorValue, recipientValue]) => {
    const scale = netIncomeDivisor
    const formatter =
      label === 'Estimated net income' || label === 'Gross income'
        ? formatCurrency
        : formatSignedCurrency

    return [label, formatter(payorValue / scale), formatter(recipientValue / scale)]
  })
  const benefitRows = spousalResult
    ? [
        [
          'Canada child benefit',
          formatCurrency(payorBenefitBreakdown.canadaChildBenefitAnnual),
          formatCurrency(recipientBenefitBreakdown.canadaChildBenefitAnnual),
        ],
        [
          'GST/HST credit',
          formatCurrency(payorBenefitBreakdown.gstHstCreditAnnual),
          formatCurrency(recipientBenefitBreakdown.gstHstCreditAnnual),
        ],
        [
          'B.C. family benefit',
          formatCurrency(payorBenefitBreakdown.bcFamilyBenefitAnnual),
          formatCurrency(recipientBenefitBreakdown.bcFamilyBenefitAnnual),
        ],
        ...(payorBenefitBreakdown.bcClimateActionCreditAnnual > 0 ||
        recipientBenefitBreakdown.bcClimateActionCreditAnnual > 0
          ? [
              [
                'B.C. climate action credit',
                formatCurrency(payorBenefitBreakdown.bcClimateActionCreditAnnual),
                formatCurrency(recipientBenefitBreakdown.bcClimateActionCreditAnnual),
              ],
            ]
          : []),
        [
          'Total annual benefits',
          formatCurrency(payorGovernmentBenefits),
          formatCurrency(recipientGovernmentBenefits),
        ],
      ]
    : []

  return (
    <div className="app-shell">
      <header className="toolbar">
        <div>
          <h1>Canadian Support Calculator</h1>
          <p>British Columbia child support and spousal support estimates.</p>
        </div>
        <div className="toolbar__meta">
          <span>Flask API</span>
          <span>React client</span>
          {metadata ? <span>{metadata.jurisdictions[0].name}</span> : null}
        </div>
      </header>

      <main className="workspace">
        <aside className="sidebar-panel">
          <section className="panel-section">
            <h2>Scenario</h2>
            <form className="scenario-form" onSubmit={handleSubmit}>
              <div className="form-grid">
                <label>
                  Jurisdiction
                  <select
                    name="jurisdiction"
                    value={scenario.jurisdiction}
                    onChange={handleScenarioChange}
                  >
                    <option value="BC">British Columbia</option>
                  </select>
                </label>

                <label>
                  Children
                  <select
                    name="children"
                    value={scenario.children}
                    onChange={handleScenarioChange}
                  >
                    {supportedChildren.map((count) => (
                      <option key={count} value={count}>
                        {count}
                      </option>
                    ))}
                  </select>
                </label>

                <label>
                  Children under 6
                  <input
                    name="childrenUnderSix"
                    type="number"
                    min="0"
                    max={scenario.children}
                    step="1"
                    value={scenario.childrenUnderSix}
                    onChange={handleScenarioChange}
                  />
                </label>

                <label>
                  Tax year
                  <input
                    name="taxYear"
                    type="number"
                    min="1"
                    step="1"
                    value={scenario.taxYear}
                    onChange={handleScenarioChange}
                  />
                </label>

                <label>
                  Payor income
                  <input
                    name="payorIncome"
                    type="number"
                    min="0"
                    step="100"
                    value={scenario.payorIncome}
                    onChange={handleScenarioChange}
                  />
                </label>

                <label>
                  Recipient income
                  <input
                    name="recipientIncome"
                    type="number"
                    min="0"
                    step="100"
                    value={scenario.recipientIncome}
                    onChange={handleScenarioChange}
                  />
                </label>

                <label>
                  Target minimum %
                  <input
                    name="targetMinPercent"
                    type="number"
                    min="1"
                    max="99"
                    step="0.5"
                    value={scenario.targetMinPercent}
                    onChange={handleScenarioChange}
                  />
                </label>

                <label>
                  Target maximum %
                  <input
                    name="targetMaxPercent"
                    type="number"
                    min="1"
                    max="99"
                    step="0.5"
                    value={scenario.targetMaxPercent}
                    onChange={handleScenarioChange}
                  />
                </label>
              </div>

              <div className="form-actions">
                <label className="form-toggle">
                  <input
                    name="autoRecalculate"
                    type="checkbox"
                    checked={autoRecalculate}
                    onChange={(event) => setAutoRecalculate(event.target.checked)}
                  />
                  <span>Recalculate automatically</span>
                </label>
                <button type="submit" disabled={isCalculating || autoRecalculate}>
                  {isCalculating ? 'Calculating' : 'Recalculate'}
                </button>
                <button type="button" className="button-secondary" onClick={handleReset}>
                  Restore example
                </button>
              </div>
            </form>
          </section>

          <section className="panel-section">
            <h2>Reference</h2>
            <DetailList
              items={[
                {
                  label: 'Supported child counts',
                  value: supportedChildren.length ? supportedChildren.join(', ') : 'Loading',
                },
                {
                  label: 'Target range',
                  value: `${scenario.targetMinPercent}% to ${scenario.targetMaxPercent}% recipient NDI`,
                },
                {
                  label: 'Children under 6',
                  value: scenario.childrenUnderSix,
                },
                {
                  label: 'Tax year',
                  value: scenario.taxYear,
                },
                {
                  label: 'Data note',
                  value: metadata?.disclaimer ?? 'Loading',
                },
                {
                  label: 'Benefit assumptions',
                  value: metadata?.benefitAssumptions ?? 'Loading',
                },
                {
                  label: 'Children note',
                  value: metadata?.supportedChildrenNote ?? 'Loading',
                },
              ]}
            />
            {metadataError ? <p className="error-text">{metadataError}</p> : null}
          </section>
        </aside>

        <section className="results-panel">
          <section className="panel-section">
            <div className="section-header">
              <div>
                <h2>Net Income</h2>
                <p>Estimated annual income after tax, child support, spousal support, and benefits.</p>
              </div>
              <div className="view-toggle" role="group" aria-label="Net income period">
                <button
                  type="button"
                  className={netIncomePeriod === 'annual' ? 'is-active' : ''}
                  aria-pressed={netIncomePeriod === 'annual'}
                  onClick={() => setNetIncomePeriod('annual')}
                >
                  Annual
                </button>
                <button
                  type="button"
                  className={netIncomePeriod === 'monthly' ? 'is-active' : ''}
                  aria-pressed={netIncomePeriod === 'monthly'}
                  onClick={() => setNetIncomePeriod('monthly')}
                >
                  Monthly
                </button>
              </div>
            </div>

            {spousalError ? <p className="error-text">{spousalError}</p> : null}

            {spousalResult ? (
              <ResultTable
                caption="Net income calculation"
                columns={['Component', `Payor ${netIncomeColumnLabel}`, `Recipient ${netIncomeColumnLabel}`]}
                rows={netIncomeDisplayRows}
              />
            ) : (
              <p className="empty-state">Results will appear here after the first calculation.</p>
            )}
          </section>

          <section className="panel-section">
            <div className="section-header">
              <div>
                <h2>Child support</h2>
                <p>Monthly table amounts with offset calculation.</p>
              </div>
              {childResult ? <strong>{formatCurrency(childResult.netMonthly)}</strong> : null}
            </div>

            {childError ? <p className="error-text">{childError}</p> : null}

            {childResult ? (
              <>
                <DetailList
                  emphasis
                  items={[
                    {
                      label: 'Transfer direction',
                      value:
                        childResult.direction === 'payor_to_recipient'
                          ? 'Payor to recipient'
                          : childResult.direction === 'recipient_to_payor'
                            ? 'Recipient to payor'
                            : 'No transfer',
                    },
                    { label: 'Net monthly transfer', value: formatCurrency(childResult.netMonthly) },
                    { label: 'Net annual transfer', value: formatCurrency(childResult.netAnnual) },
                  ]}
                />
                <ResultTable
                  caption="Child support amounts"
                  columns={['Party', 'Monthly', 'Annual']}
                  rows={childRows}
                />
              </>
            ) : (
              <p className="empty-state">Results will appear here after the first calculation.</p>
            )}
          </section>

          <section className="panel-section">
            <div className="section-header">
              <div>
                <h2>Spousal support</h2>
                <p>Estimated annual payment to move the recipient into the selected NDI range.</p>
              </div>
              {spousalResult ? (
                <strong>{formatCurrency(spousalResult.estimatedSpousalSupportMonthly)}</strong>
              ) : null}
            </div>

            {spousalResult ? (
              <>
                <DetailList
                  emphasis
                  items={[
                    {
                      label: 'Estimated monthly spousal support',
                      value: formatCurrency(spousalResult.estimatedSpousalSupportMonthly),
                    },
                    {
                      label: 'Estimated annual spousal support',
                      value: formatCurrency(spousalResult.estimatedSpousalSupportAnnual),
                    },
                    {
                      label: 'Recipient share of NDI',
                      value: formatPercent(spousalResult.recipientSharePercent),
                    },
                    {
                      label: 'Iterations',
                      value: String(spousalResult.iterations),
                    },
                  ]}
                />
                <ResultTable
                  caption="Government benefits"
                  columns={['Program', 'Payor', 'Recipient']}
                  rows={benefitRows}
                />
                <ResultTable
                  caption="Net disposable income"
                  columns={['Party', 'NDI']}
                  rows={[
                    ['Payor', formatCurrency(spousalResult.ndiPayor)],
                    ['Recipient', formatCurrency(spousalResult.ndiRecipient)],
                    ['Child support annual', formatCurrency(spousalResult.childSupport.netAnnual)],
                    ['Recipient benefits annual', formatCurrency(recipientGovernmentBenefits)],
                  ]}
                />
                <ResultTable
                  caption="Recent iterations"
                  columns={['Iteration', 'Spousal support', 'Recipient NDI share']}
                  rows={spousalHistoryRows}
                />
              </>
            ) : (
              <p className="empty-state">Results will appear here after the first calculation.</p>
            )}
          </section>
        </section>
      </main>
    </div>
  )
}

export default App
