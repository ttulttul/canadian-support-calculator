import { spawn } from 'node:child_process'
import net from 'node:net'
import path from 'node:path'
import process from 'node:process'
import { setTimeout as delay } from 'node:timers/promises'

export const BACKEND_HOST = '127.0.0.1'
export const DEFAULT_BACKEND_PORT = 5001

export function resolveBackendBaseUrl(port, host = BACKEND_HOST) {
  return `http://${host}:${port}`
}

export async function findAvailablePort(startPort = DEFAULT_BACKEND_PORT, host = BACKEND_HOST) {
  let port = startPort

  while (!(await isPortAvailable(port, host))) {
    port += 1
  }

  return port
}

export function isPortAvailable(port, host = BACKEND_HOST) {
  return new Promise((resolve) => {
    const server = net.createServer()
    server.once('error', () => resolve(false))
    server.once('listening', () => {
      server.close(() => resolve(true))
    })
    server.listen(port, host)
  })
}

export function resolveBackendCommand({
  isPackaged,
  resourcesPath = process.resourcesPath,
  projectRoot = process.cwd(),
} = {}) {
  if (isPackaged) {
    return [path.join(resourcesPath, 'backend', 'support-calculator-backend')]
  }

  return ['uv', 'run', 'python', '-m', 'support_calculator']
}

export function resolveBackendCwd({
  isPackaged,
  resourcesPath = process.resourcesPath,
  projectRoot = process.cwd(),
} = {}) {
  if (isPackaged) {
    return path.join(resourcesPath, 'backend')
  }

  return projectRoot
}

export function buildBackendEnvironment({
  port,
  host = BACKEND_HOST,
  env = process.env,
} = {}) {
  return {
    ...env,
    HOST: host,
    PORT: String(port),
    FLASK_DEBUG: env.CSC_DESKTOP_DEV === '1' ? '1' : '0',
  }
}

export function launchBackend({
  port,
  host = BACKEND_HOST,
  isPackaged,
  resourcesPath = process.resourcesPath,
  projectRoot = process.cwd(),
  log = console,
} = {}) {
  const command = resolveBackendCommand({ isPackaged, resourcesPath, projectRoot })
  const cwd = resolveBackendCwd({ isPackaged, resourcesPath, projectRoot })
  const [file, ...args] = command
  const childProcess = spawn(file, args, {
    cwd,
    env: buildBackendEnvironment({ port, host }),
    stdio: ['ignore', 'pipe', 'pipe'],
  })

  childProcess.stdout?.on('data', (chunk) => {
    log.info?.(`[backend] ${String(chunk).trimEnd()}`)
  })
  childProcess.stderr?.on('data', (chunk) => {
    log.error?.(`[backend] ${String(chunk).trimEnd()}`)
  })

  return childProcess
}

export async function waitForBackend(
  backendBaseUrl,
  {
    timeoutMs = 30_000,
    intervalMs = 250,
    fetchImpl = fetch,
  } = {},
) {
  const startedAt = Date.now()
  let lastError = null

  while (Date.now() - startedAt < timeoutMs) {
    try {
      const response = await fetchImpl(`${backendBaseUrl}/api/health`)
      if (response.ok) {
        return
      }
      lastError = new Error(`Backend healthcheck returned ${response.status}.`)
    } catch (error) {
      lastError = error
    }

    await delay(intervalMs)
  }

  throw new Error(
    `Timed out waiting for backend at ${backendBaseUrl}: ${lastError?.message ?? 'unknown error'}`,
  )
}
