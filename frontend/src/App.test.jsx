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
          supportedChildren: [2, 3],
          disclaimer: 'Bundled BC table and approximate BC tax model.',
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
    expect(await screen.findByText('Bundled BC table and approximate BC tax model.')).toBeInTheDocument()
    expect(await screen.findByRole('table', { name: 'Child support amounts' })).toBeInTheDocument()
    expect(await screen.findByRole('table', { name: 'Recent iterations' })).toBeInTheDocument()
    expect(screen.getByText('Payor to recipient')).toBeInTheDocument()
  })

  it('updates and restores the shared scenario form', async () => {
    render(<App />)

    await screen.findByRole('table', { name: 'Child support amounts' })

    fireEvent.change(screen.getByLabelText('Children'), { target: { value: '3' } })
    fireEvent.change(screen.getByLabelText('Target minimum %'), { target: { value: '41' } })
    expect(screen.getByText('41% to 46% recipient NDI')).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: 'Restore example' }))

    await waitFor(() => {
      expect(screen.getByLabelText('Children')).toHaveValue('2')
    })

    expect(screen.getByLabelText('Target minimum %')).toHaveValue(40)
    expect(screen.getByText('40% to 46% recipient NDI')).toBeInTheDocument()
  })
})
