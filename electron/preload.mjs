import { contextBridge } from 'electron'
import process from 'node:process'

contextBridge.exposeInMainWorld('electronAPI', {
  apiBaseUrl: process.env.CSC_ELECTRON_API_BASE_URL ?? '',
})
