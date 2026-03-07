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
          payorTaxBeforeSupportDeduction: 86141.98,
          payorTaxDeductionBenefit: 10163.38,
          recipientSharePercent: payload.targetMinPercent,
          iterations: 27,
          ndiPayor: 113102.24,
          ndiRecipient: 75400.99,
          childSupport: {
            netAnnual: 33395.52,
          },
          benefits: {
            payor: {
              canadaChildBenefitAnnual: 0,
              gstHstCreditAnnual: 0,
              bcFamilyBenefitAnnual: 0,
              bcClimateActionCreditAnnual: 0,
              totalAnnual: 0,
            },
            recipient: {
              canadaChildBenefitAnnual: 3920.0,
              gstHstCreditAnnual: 520.0,
              bcFamilyBenefitAnnual: 2400.0,
              bcClimateActionCreditAnnual: 441.0,
              totalAnnual: 7281.0,
            },
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
      await screen.findByRole('table', { name: 'Payor net income calculation' }),
    ).toBeInTheDocument()
    expect(await screen.findByRole('table', { name: 'Child support amounts' })).toBeInTheDocument()
    expect(await screen.findByRole('table', { name: 'Government benefits' })).toBeInTheDocument()
    expect(await screen.findByRole('table', { name: 'Recent iterations' })).toBeInTheDocument()
    expect(await screen.findByText('-$33,396')).toBeInTheDocument()
    expect(await screen.findByText('+$10,163')).toBeInTheDocument()
    expect(await screen.findByText('-$86,142')).toBeInTheDocument()
    expect(await screen.findByText(/month gross/)).toBeInTheDocument()
    expect(await screen.findByText('Spousal support (tax deduction)')).toBeInTheDocument()
    expect(screen.getByText('Payor to recipient')).toBeInTheDocument()
  })

  it('recalculates automatically and allows manual mode', async () => {
    render(<App />)

    await screen.findByRole('table', { name: 'Child support amounts' })
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
