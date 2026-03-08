import { app, BrowserWindow, Menu, dialog } from 'electron'
import { autoUpdater } from 'electron-updater'
import path from 'node:path'
import process from 'node:process'
import { fileURLToPath } from 'node:url'

import {
  DEFAULT_BACKEND_PORT,
  findAvailablePort,
  launchBackend,
  resolveBackendBaseUrl,
  waitForBackend,
} from './backend-runtime.mjs'
import { checkForUpdates, shouldEnableAutoUpdates, wireAutoUpdater } from './updater.mjs'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const projectRoot = path.resolve(__dirname, '..')
const rendererUrl = process.env.CSC_DESKTOP_RENDERER_URL ?? 'http://127.0.0.1:5173'

let mainWindow = null
let backendProcess = null
let backendBaseUrl = ''

function isDesktopDevMode() {
  return process.env.CSC_DESKTOP_DEV === '1'
}

async function stopBackend(log = console) {
  if (!backendProcess || backendProcess.killed) {
    backendProcess = null
    return
  }

  log.info?.('Stopping desktop backend process.')
  backendProcess.kill('SIGTERM')
  backendProcess = null
}

function buildApplicationMenu(updateEnabled) {
  const template = [
    {
      label: 'Canadian Support Calculator',
      submenu: [
        {
          label: 'Check for Updates',
          click: async () => {
            if (!updateEnabled) {
              await dialog.showMessageBox({
                type: 'info',
                message: 'Updates are available only in packaged macOS releases.',
              })
              return
            }

            await checkForUpdates({ enabled: true, autoUpdaterImpl: autoUpdater })
          },
        },
        { type: 'separator' },
        { role: 'quit' },
      ],
    },
    {
      label: 'Edit',
      submenu: [{ role: 'undo' }, { role: 'redo' }, { type: 'separator' }, { role: 'cut' }, { role: 'copy' }, { role: 'paste' }],
    },
    {
      label: 'View',
      submenu: [{ role: 'reload' }, { role: 'forceReload' }, { role: 'toggleDevTools' }, { type: 'separator' }, { role: 'resetZoom' }, { role: 'zoomIn' }, { role: 'zoomOut' }],
    },
    {
      label: 'Window',
      submenu: [{ role: 'minimize' }, { role: 'close' }],
    },
  ]

  Menu.setApplicationMenu(Menu.buildFromTemplate(template))
}

async function startBackend() {
  const port = await findAvailablePort(Number(process.env.CSC_BACKEND_PORT ?? DEFAULT_BACKEND_PORT))
  backendBaseUrl = resolveBackendBaseUrl(port)
  process.env.CSC_ELECTRON_API_BASE_URL = backendBaseUrl
  backendProcess = launchBackend({
    port,
    isPackaged: app.isPackaged,
    resourcesPath: process.resourcesPath,
    projectRoot,
  })

  backendProcess.once('exit', async (code, signal) => {
    if (app.isQuitting) {
      return
    }

    dialog.showErrorBox(
      'Backend exited',
      `The local calculator service stopped unexpectedly (code: ${code ?? 'n/a'}, signal: ${signal ?? 'n/a'}).`,
    )
    app.quit()
  })

  await waitForBackend(backendBaseUrl)
}

async function createMainWindow() {
  const preloadPath = path.join(__dirname, 'preload.mjs')
  mainWindow = new BrowserWindow({
    width: 1480,
    height: 980,
    minWidth: 1180,
    minHeight: 820,
    backgroundColor: '#f3ede2',
    webPreferences: {
      preload: preloadPath,
      contextIsolation: true,
      sandbox: false,
    },
  })

  const targetUrl = isDesktopDevMode() ? rendererUrl : backendBaseUrl
  await mainWindow.loadURL(targetUrl)
}

app.on('before-quit', () => {
  app.isQuitting = true
  stopBackend()
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

app.on('activate', async () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    await createMainWindow()
  }
})

app.whenReady().then(async () => {
  const updatesEnabled = shouldEnableAutoUpdates({ isPackaged: app.isPackaged })
  wireAutoUpdater({ autoUpdaterImpl: autoUpdater, dialogImpl: dialog })
  buildApplicationMenu(updatesEnabled)

  try {
    await startBackend()
    await createMainWindow()
    await checkForUpdates({ enabled: updatesEnabled, autoUpdaterImpl: autoUpdater })
  } catch (error) {
    dialog.showErrorBox('Launch failed', error.message)
    await stopBackend()
    app.quit()
  }
})
