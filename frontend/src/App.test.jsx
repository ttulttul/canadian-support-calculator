import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import App from './App'

function mockResponse(body, ok = true) {
  return Promise.resolve({
    ok,
    json: async () => body,
  })
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
        return mockResponse({
          estimatedSpousalSupportMonthly: 1848.47,
          estimatedSpousalSupportAnnual: 22181.64,
          taxYear: payload.taxYear,
          childrenUnderSix: payload.childrenUnderSix,
          payorIncome: payload.payorIncome,
          recipientIncome: payload.recipientIncome,
          recipientSharePercent: payload.targetMinPercent,
          iterations: 27,
          ndiPayor: 113102.24,
          ndiRecipient: 75400.99,
          childSupport: {
            netAnnual: 33395.52,
          },
          history: [
            { iteration: 24, spousalSupportAnnual: 22000, recipientSharePercent: 39.7 },
            { iteration: 25, spousalSupportAnnual: 22125, recipientSharePercent: 39.9 },
            { iteration: 26, spousalSupportAnnual: 22181.64, recipientSharePercent: 40.0 },
          ],
        })
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
    expect(await screen.findByText('Net Income')).toBeInTheDocument()
    expect(await screen.findByText('Spousal support (tax deduction)')).toBeInTheDocument()
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

    fireEvent.click(screen.getByRole('button', { name: 'Show Details' }))

    expect(screen.getByRole('button', { name: 'Hide Details' })).toHaveAttribute(
      'aria-expanded',
      'true',
    )
    expect(await screen.findByRole('table', { name: 'Recent iterations' })).toBeInTheDocument()
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

    fireEvent.click(screen.getByLabelText('Recalculate automatically'))
    expect(screen.getByLabelText('Recalculate automatically')).not.toBeChecked()
    expect(screen.getByRole('button', { name: 'Recalculate' })).toBeEnabled()

    fireEvent.change(screen.getByLabelText('Tax year'), { target: { value: '2025' } })
    fireEvent.change(screen.getByLabelText('Target minimum %'), { target: { value: '41' } })
    expect(globalThis.fetch.mock.calls.length).toBe(initialFetchCount + 4)
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
})
