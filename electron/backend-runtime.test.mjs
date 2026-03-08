import test from 'node:test'
import assert from 'node:assert/strict'

import {
  BACKEND_HOST,
  buildBackendEnvironment,
  resolveBackendBaseUrl,
  resolveBackendCommand,
  waitForBackend,
} from './backend-runtime.mjs'

test('resolveBackendCommand uses uv in development mode', () => {
  assert.deepEqual(resolveBackendCommand({ isPackaged: false }), ['uv', 'run', 'python', '-m', 'support_calculator'])
})

test('resolveBackendCommand uses the packaged executable in packaged mode', () => {
  assert.deepEqual(resolveBackendCommand({ isPackaged: true, resourcesPath: '/tmp/resources' }), [
    '/tmp/resources/backend/support-calculator-backend',
  ])
})

test('buildBackendEnvironment sets host and port', () => {
  assert.deepEqual(buildBackendEnvironment({ port: 6134, env: { CSC_DESKTOP_DEV: '0' } }), {
    CSC_DESKTOP_DEV: '0',
    HOST: BACKEND_HOST,
    PORT: '6134',
    FLASK_DEBUG: '0',
  })
})

test('resolveBackendBaseUrl builds a local backend URL', () => {
  assert.equal(resolveBackendBaseUrl(5001), 'http://127.0.0.1:5001')
})

test('waitForBackend retries until the healthcheck succeeds', async () => {
  let attempts = 0
  await waitForBackend('http://127.0.0.1:5001', {
    intervalMs: 1,
    timeoutMs: 100,
    fetchImpl: async () => {
      attempts += 1
      if (attempts < 3) {
        throw new Error('Not ready')
      }
      return { ok: true }
    },
  })

  assert.equal(attempts, 3)
})
