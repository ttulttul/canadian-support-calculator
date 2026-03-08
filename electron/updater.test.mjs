import test from 'node:test'
import assert from 'node:assert/strict'

import {
  checkForUpdates,
  formatUpdateError,
  resolveAutoUpdaterModule,
  shouldEnableAutoUpdates,
  wireAutoUpdater,
} from './updater.mjs'

test('shouldEnableAutoUpdates only allows packaged macOS builds', () => {
  assert.equal(shouldEnableAutoUpdates({ isPackaged: true, platform: 'darwin' }), true)
  assert.equal(shouldEnableAutoUpdates({ isPackaged: false, platform: 'darwin' }), false)
  assert.equal(shouldEnableAutoUpdates({ isPackaged: true, platform: 'linux' }), false)
})

test('checkForUpdates skips updater calls when disabled', async () => {
  let called = false
  const result = await checkForUpdates({
    enabled: false,
    autoUpdaterImpl: {
      checkForUpdates: async () => {
        called = true
      },
    },
    log: { info() {} },
  })

  assert.equal(result, false)
  assert.equal(called, false)
})

test('resolveAutoUpdaterModule supports CommonJS-style updater exports', () => {
  const autoUpdater = { checkForUpdates() {} }

  assert.equal(resolveAutoUpdaterModule({ autoUpdater }), autoUpdater)
  assert.equal(resolveAutoUpdaterModule({ default: { autoUpdater } }), autoUpdater)
})

test('formatUpdateError prefers Error messages', () => {
  assert.equal(formatUpdateError(new Error('No published versions on GitHub')), 'No published versions on GitHub')
  assert.equal(formatUpdateError('plain failure'), 'plain failure')
})

test('checkForUpdates treats updater failures as non-fatal', async () => {
  const warnings = []

  const result = await checkForUpdates({
    enabled: true,
    autoUpdaterImpl: {
      async checkForUpdates() {
        throw new Error('No published versions on GitHub')
      },
    },
    log: {
      info() {},
      warn(message) {
        warnings.push(message)
      },
    },
  })

  assert.equal(result, false)
  assert.equal(warnings.length, 1)
  assert.match(warnings[0], /No published versions on GitHub/)
})

test('wireAutoUpdater prompts before installing a downloaded update', async () => {
  const listeners = new Map()
  let quitAndInstallCalled = false
  const updater = {
    autoDownload: false,
    autoInstallOnAppQuit: true,
    on(eventName, handler) {
      listeners.set(eventName, handler)
    },
    quitAndInstall() {
      quitAndInstallCalled = true
    },
  }

  wireAutoUpdater({
    autoUpdaterImpl: updater,
    dialogImpl: {
      async showMessageBox() {
        return { response: 0 }
      },
    },
    log: { info() {}, error() {} },
  })

  await listeners.get('update-downloaded')({ version: '1.2.3' })

  assert.equal(updater.autoDownload, true)
  assert.equal(updater.autoInstallOnAppQuit, false)
  assert.equal(quitAndInstallCalled, true)
})
