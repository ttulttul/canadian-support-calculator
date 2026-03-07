import { fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import App from './App'

function mockResponse(body, ok = true) {
  return Promise.resolve({
    ok,
    json: async () => body,
  })
}

function buildSpousalResponse(payload) {
  const usingAlternatePayorIncome = payload.payorSpousalIncome === 175000
  const payorSpousalIncome = payload.payorSpousalIncome ?? payload.payorIncome
  const recipientSpousalIncome = payload.recipientSpousalIncome ?? payload.recipientIncome

  if (usingAlternatePayorIncome) {
    return {
      estimatedSpousalSupportMonthly: 0,
      estimatedSpousalSupportAnnual: 0,
      taxYear: payload.taxYear,
      children: payload.children,
      childrenUnderSix: payload.childrenUnderSix,
      payorIncome: payload.payorIncome,
      recipientIncome: payload.recipientIncome,
      payorSpousalIncome,
      recipientSpousalIncome,
      recipientSharePercent: 41.83,
      iterations: 19,
      ndiPayor: 93248.4,
      ndiRecipient: 67212.66,
      childSupport: {
        netAnnual: 33395.52,
      },
      history: [
        {
          iteration: 16,
          spousalSupportAnnual: 1000,
          recipientSharePercent: 42.2,
          ndiPayor: 92450,
          ndiRecipient: 68011,
        },
        {
          iteration: 17,
          spousalSupportAnnual: 500,
          recipientSharePercent: 42.0,
          ndiPayor: 92840,
          ndiRecipient: 67621,
        },
        {
          iteration: 18,
          spousalSupportAnnual: 0,
          recipientSharePercent: 41.83,
          ndiPayor: 93248.4,
          ndiRecipient: 67212.66,
        },
      ],
    }
  }

  return {
    estimatedSpousalSupportMonthly: 1848.47,
    estimatedSpousalSupportAnnual: 22181.64,
    taxYear: payload.taxYear,
    children: payload.children,
    childrenUnderSix: payload.childrenUnderSix,
    payorIncome: payload.payorIncome,
    recipientIncome: payload.recipientIncome,
    payorSpousalIncome,
    recipientSpousalIncome,
    recipientSharePercent: payload.targetMinPercent,
    iterations: 27,
    ndiPayor: 113102.24,
    ndiRecipient: 75400.99,
    childSupport: {
      netAnnual: 33395.52,
    },
    history: [
      {
        iteration: 22,
        spousalSupportAnnual: 21000,
        recipientSharePercent: 39.1,
        ndiPayor: 114920.0,
        ndiRecipient: 73583.0,
      },
      {
        iteration: 23,
        spousalSupportAnnual: 21500,
        recipientSharePercent: 39.4,
        ndiPayor: 114102.0,
        ndiRecipient: 74401.0,
      },
      {
        iteration: 24,
        spousalSupportAnnual: 22000,
        recipientSharePercent: 39.7,
        ndiPayor: 113480.0,
        ndiRecipient: 75023.0,
      },
      {
        iteration: 25,
        spousalSupportAnnual: 22125,
        recipientSharePercent: 39.9,
        ndiPayor: 113230.0,
        ndiRecipient: 75273.0,
      },
      {
        iteration: 26,
        spousalSupportAnnual: 22181.64,
        recipientSharePercent: 40.0,
        ndiPayor: 113102.24,
        ndiRecipient: 75400.99,
      },
    ],
  }
}

describe('App', () => {
  beforeEach(() => {
    globalThis.fetch = vi.fn((url, options) => {
      if (url === '/api/metadata') {
        return mockResponse({
          jurisdictions: [{ code: 'BC', name: 'British Columbia' }],
          supportedChildren: [1, 2, 3, 4, 5, 6, 7],
          supportedChildrenNote: 'Six and seven children use the federal six-or-more table.',
          defaultTaxYear: 2023,
          disclaimer:
            'Child support uses the bundled 2017 BC simplified federal table. Spousal support uses annualized shared-custody family benefits and credits.',
          benefitAssumptions:
            'Benefit estimates assume both parents are single households in a shared-custody offset scenario.',
        })
      }

      if (url === '/api/calculate/child-support') {
        const payload = JSON.parse(options.body)
        return mockResponse({
          children: payload.children,
          direction: 'payor_to_recipient',
          payorMonthly: 3275.96,
          payorAnnual: 39311.52,
          recipientMonthly: 493,
          recipientAnnual: 5916,
          netMonthly: 2782.96,
          netAnnual: 33395.52,
        })
      }

      if (url === '/api/calculate/spousal-support') {
        const payload = JSON.parse(options.body)
        return mockResponse(buildSpousalResponse(payload))
      }

      return Promise.reject(new Error(`Unexpected request: ${url}`))
    })
  })

  it('renders calculation results after loading metadata', async () => {
    render(<App />)

    expect(await screen.findByText('Canadian Support Calculator')).toBeInTheDocument()
    expect(
      await screen.findByText(
        'Child support uses the bundled 2017 BC simplified federal table. Spousal support uses annualized shared-custody family benefits and credits.',
      ),
    ).toBeInTheDocument()
    expect(
      await screen.findByText(
        'Benefit estimates assume both parents are single households in a shared-custody offset scenario.',
      ),
    ).toBeInTheDocument()
    expect(
      await screen.findByText('Six and seven children use the federal six-or-more table.'),
    ).toBeInTheDocument()
    expect(await screen.findByLabelText('Children information')).toBeInTheDocument()
    expect(await screen.findByLabelText('Children under 6 information')).toBeInTheDocument()
    expect(await screen.findByLabelText('Tax year information')).toBeInTheDocument()
    expect(await screen.findByLabelText('Payor income information')).toBeInTheDocument()
    expect(await screen.findByLabelText('Recipient income information')).toBeInTheDocument()
    expect(await screen.findByLabelText('Target minimum percentage information')).toBeInTheDocument()
    expect(await screen.findByLabelText('Target maximum percentage information')).toBeInTheDocument()
    expect(
      await screen.findByLabelText('Use different incomes for spousal support only'),
    ).toBeInTheDocument()
    expect(
      screen.getByLabelText('Use different incomes for spousal support only').parentElement,
    ).toHaveClass('form-toggle')
    expect(await screen.findAllByText('When the Gross Income Amount Needs Adjustment')).toHaveLength(2)
    expect(
      await screen.findAllByText(/income for the purpose of spousal support calculations may be different/i),
    ).toHaveLength(2)
    expect(
      await screen.findByRole('table', { name: 'Net income calculation' }),
    ).toBeInTheDocument()
    expect(await screen.findByText('Canada child benefit')).toBeInTheDocument()
    expect(await screen.findByText('GST/HST credit')).toBeInTheDocument()
    expect(await screen.findByText('B.C. family benefit')).toBeInTheDocument()
    expect(await screen.findByText('-$33,396')).toBeInTheDocument()
    expect(await screen.findByText('+$10,707')).toBeInTheDocument()
    expect(await screen.findByText('-$86,685')).toBeInTheDocument()
    expect(await screen.findByText('-$4,638')).toBeInTheDocument()
    expect(await screen.findByText('+$5,471')).toBeInTheDocument()
    expect(await screen.findByText('+$308')).toBeInTheDocument()
    expect(await screen.findByText('+$1,694')).toBeInTheDocument()
    const equivalentIncomeLabel = await screen.findByText('Equivalent before-tax income')
    expect(equivalentIncomeLabel.tagName).toBe('EM')
    expect(equivalentIncomeLabel.closest('td')).toHaveClass('data-table__informational')
    const equivalentIncomeInfoIcon = screen.getByLabelText('Equivalent before-tax income explanation')
    expect(equivalentIncomeInfoIcon).not.toHaveAttribute('title')
    expect(equivalentIncomeInfoIcon).toHaveAttribute('tabindex', '0')
    expect(equivalentIncomeInfoIcon).toHaveClass('info-icon')
    expect(equivalentIncomeInfoIcon.querySelector('svg')).not.toBeNull()
    expect(
      screen.getByText(
        'The gross employment income that would leave the same after-tax income if there were no child support, spousal support, or government benefits.',
      ),
    ).toHaveClass('info-tooltip')
    expect(await screen.findByText('$161,200')).toBeInTheDocument()
    expect(await screen.findByText('$99,571')).toBeInTheDocument()
    expect(await screen.findByText('Net Income')).toBeInTheDocument()
    expect(await screen.findByText('Spousal support (tax deduction)')).toBeInTheDocument()
    expect(screen.getAllByText('Child support')[0].closest('td')).toHaveClass('data-table__emphasis')
    expect(screen.getByText('Spousal support (pre-tax)').closest('td')).toHaveClass(
      'data-table__emphasis',
    )
    expect(screen.getAllByText('$113,102')[0].closest('td')).toHaveClass('data-table__emphasis')
    expect(screen.queryByText('Flask API')).not.toBeInTheDocument()
    expect(screen.queryByText('React client')).not.toBeInTheDocument()
    expect(screen.getByRole('columnheader', { name: 'Payor Annual amount' })).toHaveClass(
      'data-table__numeric',
    )
    expect(screen.getByRole('columnheader', { name: 'Recipient Annual amount' })).toHaveClass(
      'data-table__numeric',
    )
    expect(screen.getByText('+$10,707')).toHaveClass('signed-value--positive')
    expect(screen.getByText('-$86,685')).toHaveClass('signed-value--negative')
    expect(screen.getByText('+$10,707')).toHaveClass('currency-cell')
    expect(screen.getByRole('button', { name: 'Annual' })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByRole('columnheader', { name: 'Payor Annual amount' })).toBeInTheDocument()
    expect(await screen.findByText('References')).toBeInTheDocument()
    expect(screen.getAllByText('Child support').length).toBeGreaterThan(0)
    expect(await screen.findByRole('table', { name: 'Child support amounts' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Show Details' })).toHaveAttribute(
      'aria-expanded',
      'false',
    )
    expect(screen.getByText('Spousal support calculations')).toBeInTheDocument()
    expect(screen.getByText('Calculation Details')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Monthly' }))

    expect(screen.getByRole('button', { name: 'Monthly' })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByRole('columnheader', { name: 'Payor Monthly amount' })).toBeInTheDocument()
    expect(screen.getByText('+$892')).toBeInTheDocument()
    expect(screen.getByText('$13,433')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Show Details' }))

    expect(screen.getByRole('button', { name: 'Hide Details' })).toHaveAttribute(
      'aria-expanded',
      'true',
    )
    expect(await screen.findByRole('img', { name: 'NDI convergence chart' })).toBeInTheDocument()
    expect(screen.queryByRole('table', { name: 'Recent iterations' })).not.toBeInTheDocument()
    expect(await screen.findByText('NDI convergence')).toBeInTheDocument()
    expect(await screen.findByText('Payor NDI')).toBeInTheDocument()
    expect(await screen.findByText('Recipient NDI')).toBeInTheDocument()
    expect(await screen.findByText('Payor income used for spousal support')).toBeInTheDocument()
    expect(await screen.findByText('$244,658')).toBeInTheDocument()
    expect(await screen.findByText('Spousal support calculations')).toBeInTheDocument()
    expect(screen.getByText('Payor to recipient')).toBeInTheDocument()
  })

  it('recalculates automatically and allows manual mode', async () => {
    render(<App />)

    await screen.findByRole('table', { name: 'Net income calculation' })
    const initialFetchCount = globalThis.fetch.mock.calls.length

    expect(screen.getByLabelText('Recalculate automatically')).toBeChecked()
    expect(screen.getByRole('button', { name: 'Recalculate' })).toBeDisabled()

    fireEvent.change(screen.getByLabelText('Children'), { target: { value: '7' } })
    fireEvent.change(screen.getByLabelText('Children under 6'), { target: { value: '1' } })

    await waitFor(() => {
      expect(globalThis.fetch.mock.calls.length).toBe(initialFetchCount + 4)
    })

    expect(screen.getByLabelText('Children under 6')).toHaveAttribute('max', '7')

    fireEvent.change(screen.getByLabelText('Children'), { target: { value: '2' } })
    fireEvent.change(screen.getByLabelText('Children under 6'), { target: { value: '7' } })

    await waitFor(() => {
      expect(screen.getByLabelText('Children')).toHaveValue('7')
    })
    expect(screen.getByLabelText('Children under 6')).toHaveValue(7)
    const fetchCountAfterChildrenAdjustments = globalThis.fetch.mock.calls.length

    const autoRecalculate = screen.getByLabelText('Recalculate automatically')
    expect(autoRecalculate.parentElement).toHaveClass('form-toggle')
    expect(autoRecalculate.parentElement?.firstElementChild).toBe(autoRecalculate)

    fireEvent.click(autoRecalculate)
    expect(autoRecalculate).not.toBeChecked()
    expect(screen.getByRole('button', { name: 'Recalculate' })).toBeEnabled()

    fireEvent.change(screen.getByLabelText('Tax year'), { target: { value: '2025' } })
    fireEvent.change(screen.getByLabelText('Target minimum %'), { target: { value: '41' } })
    expect(globalThis.fetch.mock.calls.length).toBe(fetchCountAfterChildrenAdjustments)
    expect(screen.getByText('41% to 46% recipient NDI')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Restore example' }))

    await waitFor(() => {
      expect(screen.getByLabelText('Children')).toHaveValue('2')
    })

    expect(screen.getByLabelText('Tax year')).toHaveValue(2023)
    expect(screen.getByLabelText('Children under 6')).toHaveValue(0)
    expect(screen.getByLabelText('Target minimum %')).toHaveValue(40)
    expect(screen.getByText('40% to 46% recipient NDI')).toBeInTheDocument()
  })

  it('allows editing gross income directly from the net income table', async () => {
    render(<App />)

    const netIncomeTable = await screen.findByRole('table', { name: 'Net income calculation' })
    const initialFetchCount = globalThis.fetch.mock.calls.length

    fireEvent.doubleClick(within(netIncomeTable).getByText('$244,658'))

    const payorGrossIncomeEditor = await screen.findByLabelText('Edit payor gross income')
    expect(payorGrossIncomeEditor).toHaveClass('data-table__input')
    expect(payorGrossIncomeEditor).toHaveAttribute('type', 'text')
    fireEvent.change(payorGrossIncomeEditor, { target: { value: '$250000.6abc-' } })

    expect(payorGrossIncomeEditor).toHaveValue('$250,000.6')

    await waitFor(() => {
      expect(globalThis.fetch.mock.calls.length).toBe(initialFetchCount + 2)
    })

    await waitFor(() => {
      expect(screen.getByLabelText('Payor income')).toHaveValue(250000.6)
    })

    fireEvent.keyDown(payorGrossIncomeEditor, { key: 'Enter', code: 'Enter' })

    await waitFor(() => {
      expect(globalThis.fetch.mock.calls.length).toBe(initialFetchCount + 4)
    })

    await waitFor(() => {
      expect(screen.getByLabelText('Payor income')).toHaveValue(250001)
    })

    expect(within(netIncomeTable).getByText('$250,001')).toBeInTheDocument()
  })

  it('uses alternate spousal-only incomes when the drawer is enabled', async () => {
    render(<App />)

    await screen.findByRole('table', { name: 'Net income calculation' })
    const initialFetchCount = globalThis.fetch.mock.calls.length

    fireEvent.change(screen.getByLabelText('Payor income'), {
      target: { value: '244000' },
    })
    fireEvent.click(screen.getByLabelText('Use different incomes for spousal support only'))
    fireEvent.change(screen.getByLabelText('Payor income for spousal support only'), {
      target: { value: '175000' },
    })

    await waitFor(() => {
      expect(globalThis.fetch.mock.calls.length).toBeGreaterThan(initialFetchCount)
    })

    const spousalSupportCalls = globalThis.fetch.mock.calls.filter(
      ([url]) => url === '/api/calculate/spousal-support',
    )
    const latestSpousalPayload = JSON.parse(spousalSupportCalls.at(-1)[1].body)

    expect(latestSpousalPayload.payorIncome).toBe(244000)
    expect(latestSpousalPayload.recipientIncome).toBe(30600)
    expect(latestSpousalPayload.payorSpousalIncome).toBe(175000)
    expect(latestSpousalPayload.recipientSpousalIncome).toBeUndefined()
    fireEvent.click(screen.getByRole('button', { name: 'Show Details' }))
    expect(await screen.findByText('Payor income used for spousal support')).toBeInTheDocument()
    expect(await screen.findAllByText('$175,000')).toHaveLength(2)
    expect(await screen.findAllByText('$0')).not.toHaveLength(0)
  })
})
