import { useEffect, useEffectEvent, useState } from 'react'
import './App.css'

const defaultChildForm = {
  jurisdiction: 'BC',
  children: '2',
  payorIncome: '244658',
  recipientIncome: '30600',
}

const defaultSpousalForm = {
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

function MetricCard({ label, value, tone = 'default' }) {
  return (
    <article className={`metric-card metric-card--${tone}`}>
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
  )
}

function App() {
  const [metadata, setMetadata] = useState(null)
  const [childForm, setChildForm] = useState(defaultChildForm)
  const [spousalForm, setSpousalForm] = useState(defaultSpousalForm)
  const [childResult, setChildResult] = useState(null)
  const [spousalResult, setSpousalResult] = useState(null)
  const [childError, setChildError] = useState('')
  const [spousalError, setSpousalError] = useState('')
  const [childLoading, setChildLoading] = useState(false)
  const [spousalLoading, setSpousalLoading] = useState(false)

  useEffect(() => {
    let active = true

    async function loadMetadata() {
      const response = await fetch('/api/metadata')
      const data = await response.json()
      if (active) {
        setMetadata(data)
      }
    }

    loadMetadata().catch((error) => {
      if (active) {
        setChildError(error.message)
        setSpousalError(error.message)
      }
    })

    return () => {
      active = false
    }
  }, [])

  const supportedChildren = metadata?.supportedChildren ?? [1, 2, 3, 4, 5, 6]

  function updateForm(setter) {
    return (event) => {
      const { name, value } = event.target
      setter((current) => ({ ...current, [name]: value }))
    }
  }

  async function calculateChildSupport(event) {
    event?.preventDefault()
    setChildLoading(true)
    setChildError('')

    try {
      const result = await postJson('/api/calculate/child-support', {
        jurisdiction: childForm.jurisdiction,
        children: Number(childForm.children),
        payorIncome: Number(childForm.payorIncome),
        recipientIncome: Number(childForm.recipientIncome),
      })
      setChildResult(result)
    } catch (error) {
      setChildError(error.message)
    } finally {
      setChildLoading(false)
    }
  }

  async function calculateSpousalSupport(event) {
    event?.preventDefault()
    setSpousalLoading(true)
    setSpousalError('')

    try {
      const result = await postJson('/api/calculate/spousal-support', {
        jurisdiction: spousalForm.jurisdiction,
        children: Number(spousalForm.children),
        payorIncome: Number(spousalForm.payorIncome),
        recipientIncome: Number(spousalForm.recipientIncome),
        targetMinPercent: Number(spousalForm.targetMinPercent),
        targetMaxPercent: Number(spousalForm.targetMaxPercent),
      })
      setSpousalResult(result)
    } catch (error) {
      setSpousalError(error.message)
    } finally {
      setSpousalLoading(false)
    }
  }

  const hydrateExamples = useEffectEvent(() => {
    calculateChildSupport()
    calculateSpousalSupport()
  })

  useEffect(() => {
    if (!metadata) {
      return
    }

    hydrateExamples()
  }, [metadata])

  return (
    <main className="page-shell">
      <section className="hero">
        <p className="eyebrow">Guideline-driven support modelling</p>
        <h1>Canadian Support Calculator</h1>
        <p className="hero-copy">
          Explore monthly offset child support and SSAG-style spousal support
          estimates with a React client backed by a Flask API.
        </p>
        <p className="disclaimer">
          {metadata?.disclaimer ??
            'Loading BC child support table metadata and spousal support assumptions.'}
        </p>
      </section>

      <section className="content-grid">
        <section className="panel">
          <div className="panel-header">
            <div>
              <p className="panel-kicker">Calculator one</p>
              <h2>Child support</h2>
            </div>
            <span className="tag">Monthly table amount</span>
          </div>

          <form className="calculator-form" onSubmit={calculateChildSupport}>
            <label>
              Jurisdiction
              <select
                name="jurisdiction"
                value={childForm.jurisdiction}
                onChange={updateForm(setChildForm)}
              >
                <option value="BC">British Columbia</option>
              </select>
            </label>

            <label>
              Children
              <select
                name="children"
                value={childForm.children}
                onChange={updateForm(setChildForm)}
              >
                {supportedChildren.map((children) => (
                  <option key={children} value={children}>
                    {children}
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
                value={childForm.payorIncome}
                onChange={updateForm(setChildForm)}
              />
            </label>

            <label>
              Recipient income
              <input
                name="recipientIncome"
                type="number"
                min="0"
                step="100"
                value={childForm.recipientIncome}
                onChange={updateForm(setChildForm)}
              />
            </label>

            <button type="submit" disabled={childLoading}>
              {childLoading ? 'Calculating…' : 'Calculate child support'}
            </button>
          </form>

          {childError ? <p className="error">{childError}</p> : null}

          {childResult ? (
            <div className="results-grid">
              <MetricCard
                label="Payor monthly table amount"
                value={formatCurrency(childResult.payorMonthly)}
                tone="warm"
              />
              <MetricCard
                label="Recipient monthly table amount"
                value={formatCurrency(childResult.recipientMonthly)}
              />
              <MetricCard
                label="Net monthly transfer"
                value={formatCurrency(Math.abs(childResult.netMonthly))}
                tone="cool"
              />
              <MetricCard
                label="Net annual transfer"
                value={formatCurrency(Math.abs(childResult.netAnnual))}
              />
            </div>
          ) : null}

          {childResult ? (
            <p className="result-note">
              Direction:{' '}
              {childResult.direction === 'payor_to_recipient'
                ? 'payor to recipient'
                : childResult.direction === 'recipient_to_payor'
                  ? 'recipient to payor'
                  : 'no transfer'}.
            </p>
          ) : null}
        </section>

        <section className="panel panel--accent">
          <div className="panel-header">
            <div>
              <p className="panel-kicker">Calculator two</p>
              <h2>Spousal support</h2>
            </div>
            <span className="tag">Annual estimate</span>
          </div>

          <form className="calculator-form" onSubmit={calculateSpousalSupport}>
            <label>
              Jurisdiction
              <select
                name="jurisdiction"
                value={spousalForm.jurisdiction}
                onChange={updateForm(setSpousalForm)}
              >
                <option value="BC">British Columbia</option>
              </select>
            </label>

            <label>
              Children
              <select
                name="children"
                value={spousalForm.children}
                onChange={updateForm(setSpousalForm)}
              >
                {supportedChildren.map((children) => (
                  <option key={children} value={children}>
                    {children}
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
                value={spousalForm.payorIncome}
                onChange={updateForm(setSpousalForm)}
              />
            </label>

            <label>
              Recipient income
              <input
                name="recipientIncome"
                type="number"
                min="0"
                step="100"
                value={spousalForm.recipientIncome}
                onChange={updateForm(setSpousalForm)}
              />
            </label>

            <label>
              Target min percent
              <input
                name="targetMinPercent"
                type="number"
                min="1"
                max="99"
                step="0.5"
                value={spousalForm.targetMinPercent}
                onChange={updateForm(setSpousalForm)}
              />
            </label>

            <label>
              Target max percent
              <input
                name="targetMaxPercent"
                type="number"
                min="1"
                max="99"
                step="0.5"
                value={spousalForm.targetMaxPercent}
                onChange={updateForm(setSpousalForm)}
              />
            </label>

            <button type="submit" disabled={spousalLoading}>
              {spousalLoading ? 'Calculating…' : 'Estimate spousal support'}
            </button>
          </form>

          {spousalError ? <p className="error">{spousalError}</p> : null}

          {spousalResult ? (
            <>
              <div className="results-grid">
                <MetricCard
                  label="Estimated monthly spousal support"
                  value={formatCurrency(spousalResult.estimatedSpousalSupportMonthly)}
                  tone="warm"
                />
                <MetricCard
                  label="Estimated annual spousal support"
                  value={formatCurrency(spousalResult.estimatedSpousalSupportAnnual)}
                  tone="cool"
                />
                <MetricCard
                  label="Recipient share of NDI"
                  value={formatPercent(spousalResult.recipientSharePercent)}
                />
                <MetricCard
                  label="Iterations"
                  value={String(spousalResult.iterations)}
                />
              </div>

              <div className="split-bar" aria-hidden="true">
                <div
                  className="split-bar__recipient"
                  style={{ width: `${spousalResult.recipientSharePercent}%` }}
                />
              </div>

              <div className="ndi-grid">
                <MetricCard
                  label="Payor NDI"
                  value={formatCurrency(spousalResult.ndiPayor)}
                />
                <MetricCard
                  label="Recipient NDI"
                  value={formatCurrency(spousalResult.ndiRecipient)}
                />
                <MetricCard
                  label="Net annual child support"
                  value={formatCurrency(spousalResult.childSupport.netAnnual)}
                />
              </div>

              <div className="history-table">
                <div className="history-table__header">
                  <span>Iteration</span>
                  <span>Spousal support</span>
                  <span>Recipient NDI share</span>
                </div>
                {spousalResult.history.slice(-6).map((entry) => (
                  <div className="history-table__row" key={entry.iteration}>
                    <span>{entry.iteration}</span>
                    <span>{formatCurrency(entry.spousalSupportAnnual)}</span>
                    <span>{formatPercent(entry.recipientSharePercent)}</span>
                  </div>
                ))}
              </div>
            </>
          ) : null}
        </section>
      </section>
    </main>
  )
}

export default App
