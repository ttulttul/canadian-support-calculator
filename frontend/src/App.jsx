import { useEffect, useEffectEvent, useRef, useState } from 'react'
import './App.css'

const defaultScenario = {
  jurisdiction: 'BC',
  children: '2',
  taxYear: '2023',
  payorIncome: '244658',
  recipientIncome: '30600',
  targetMinPercent: '40',
  targetMaxPercent: '46',
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

function asNumber(value, fallback = 0) {
  return Number.isFinite(Number(value)) ? Number(value) : fallback
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
    setScenario((current) => ({ ...current, [name]: value }))
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
  const payorTaxableIncome = spousalResult
    ? asNumber(spousalResult.payorTaxableIncome, payorGrossIncome - spousalSupportAnnual)
    : 0
  const payorTax = spousalResult
    ? asNumber(
        spousalResult.payorTax,
        payorGrossIncome - childSupportAnnual - spousalSupportAnnual - payorNetIncome,
      )
    : 0
  const payorGrossMonthly = payorGrossIncome / 12
  const payorTaxMonthly = payorTax / 12
  const childSupportMonthly = childSupportAnnual / 12
  const spousalSupportMonthly = spousalSupportAnnual / 12
  const payorNetMonthly = payorNetIncome / 12
  const payorNetIncomeRows = spousalResult
    ? [
        ['Gross income', formatCurrency(payorGrossIncome)],
        ['Taxable income after spousal support', formatCurrency(payorTaxableIncome)],
        ['Estimated tax', formatCurrency(payorTax)],
        ['Child support annual', formatCurrency(childSupportAnnual)],
        ['Spousal support annual', formatCurrency(spousalSupportAnnual)],
        ['Estimated net income', formatCurrency(payorNetIncome)],
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
                  label: 'Tax year',
                  value: scenario.taxYear,
                },
                {
                  label: 'Data note',
                  value: metadata?.disclaimer ?? 'Loading',
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
                <h2>Payor net income</h2>
                <p>Estimated annual income after tax, child support, and spousal support.</p>
              </div>
              {spousalResult ? <strong>{formatCurrency(spousalResult.ndiPayor)}</strong> : null}
            </div>

            {spousalError ? <p className="error-text">{spousalError}</p> : null}

            {spousalResult ? (
              <>
                <p className="summary-expression">
                  {formatCurrency(payorGrossIncome)} gross - {formatCurrency(payorTax)} tax -{' '}
                  {formatCurrency(childSupportAnnual)} child support -{' '}
                  {formatCurrency(spousalSupportAnnual)} spousal support ={' '}
                  {formatCurrency(payorNetIncome)} net
                </p>
                <p className="summary-expression summary-expression--secondary">
                  {formatCurrency(payorGrossMonthly)}/month gross -{' '}
                  {formatCurrency(payorTaxMonthly)}/month tax -{' '}
                  {formatCurrency(childSupportMonthly)}/month child support -{' '}
                  {formatCurrency(spousalSupportMonthly)}/month spousal support ={' '}
                  {formatCurrency(payorNetMonthly)}/month net
                </p>
                <ResultTable
                  caption="Payor net income calculation"
                  columns={['Component', 'Annual amount']}
                  rows={payorNetIncomeRows}
                />
              </>
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
                  caption="Net disposable income"
                  columns={['Party', 'NDI']}
                  rows={[
                    ['Payor', formatCurrency(spousalResult.ndiPayor)],
                    ['Recipient', formatCurrency(spousalResult.ndiRecipient)],
                    ['Child support annual', formatCurrency(spousalResult.childSupport.netAnnual)],
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
