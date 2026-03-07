import { useEffect, useEffectEvent, useState } from 'react'
import './App.css'

const defaultScenario = {
  jurisdiction: 'BC',
  children: '2',
  payorIncome: '244658',
  recipientIncome: '30600',
  targetMinPercent: '40',
  targetMaxPercent: '46',
}

function formatCurrency(value) {
  return new Intl.NumberFormat('en-CA', {
    style: 'currency',
    currency: 'CAD',
    maximumFractionDigits: 2,
  }).format(value ?? 0)
}

function formatPercent(value) {
  return `${Number(value ?? 0).toFixed(2)}%`
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
  const [childResult, setChildResult] = useState(null)
  const [spousalResult, setSpousalResult] = useState(null)
  const [childError, setChildError] = useState('')
  const [spousalError, setSpousalError] = useState('')
  const [metadataError, setMetadataError] = useState('')
  const [isCalculating, setIsCalculating] = useState(false)

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
    setIsCalculating(true)
    setChildError('')
    setSpousalError('')

    const payload = {
      jurisdiction: activeScenario.jurisdiction,
      children: Number(activeScenario.children),
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

  const hydrateScenario = useEffectEvent(() => {
    void submitScenario(scenario)
  })

  useEffect(() => {
    if (!metadata) {
      return
    }

    hydrateScenario()
  }, [metadata])

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
                <button type="submit" disabled={isCalculating}>
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
                  label: 'Data note',
                  value: metadata?.disclaimer ?? 'Loading',
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

            {spousalError ? <p className="error-text">{spousalError}</p> : null}

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
