import process from 'node:process'

export function resolveAutoUpdaterModule(updaterModule) {
  if (updaterModule?.autoUpdater) {
    return updaterModule.autoUpdater
  }

  if (updaterModule?.default?.autoUpdater) {
    return updaterModule.default.autoUpdater
  }

  throw new Error('Unable to resolve autoUpdater from the electron-updater module.')
}

export function formatUpdateError(error) {
  if (error instanceof Error) {
    return error.message
  }

  return String(error)
}

export function shouldEnableAutoUpdates({
  isPackaged,
  platform = process.platform,
} = {}) {
  return Boolean(isPackaged && platform === 'darwin')
}

export function wireAutoUpdater({
  autoUpdaterImpl,
  dialogImpl,
  log = console,
  appName = 'Canadian Support Calculator',
} = {}) {
  if (!autoUpdaterImpl || !dialogImpl) {
    throw new Error('wireAutoUpdater requires autoUpdaterImpl and dialogImpl.')
  }

  autoUpdaterImpl.autoDownload = true
  autoUpdaterImpl.autoInstallOnAppQuit = false

  autoUpdaterImpl.on('checking-for-update', () => {
    log.info?.('Checking for desktop updates.')
  })

  autoUpdaterImpl.on('update-available', (info) => {
    log.info?.(`Desktop update available: ${info.version}`)
  })

  autoUpdaterImpl.on('update-not-available', () => {
    log.info?.('No desktop update is available.')
  })

  autoUpdaterImpl.on('error', (error) => {
    log.error?.(`Desktop update failed: ${error.message}`)
  })

  autoUpdaterImpl.on('update-downloaded', async (info) => {
    const result = await dialogImpl.showMessageBox({
      type: 'info',
      buttons: ['Install and Relaunch', 'Later'],
      defaultId: 0,
      cancelId: 1,
      title: appName,
      message: `${appName} ${info.version} is ready to install.`,
      detail: 'Restart the app to finish installing the update.',
    })

    if (result.response === 0) {
      autoUpdaterImpl.quitAndInstall()
    }
  })
}

export async function checkForUpdates({
  enabled,
  autoUpdaterImpl,
  log = console,
} = {}) {
  if (!enabled) {
    log.info?.('Desktop updates are disabled for this environment.')
    return false
  }

  if (!autoUpdaterImpl) {
    throw new Error('checkForUpdates requires autoUpdaterImpl when updates are enabled.')
  }

  try {
    await autoUpdaterImpl.checkForUpdates()
    return true
  } catch (error) {
    log.warn?.(`Desktop update check skipped: ${formatUpdateError(error)}`)
    return false
  }
}
