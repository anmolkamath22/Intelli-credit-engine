export function resolveApiBaseUrl() {
  const envBase = import.meta.env.VITE_FRONTEND_API_BASE_URL || import.meta.env.VITE_API_BASE
  const runtimeBase = window.__APP_CONFIG__?.FRONTEND_API_BASE_URL

  let apiBase = envBase || runtimeBase
  if (!apiBase) {
    const host = window.location.hostname
    const port = window.location.port
    // In local Vite dev, frontend runs on 5173/3000 and backend is expected on 8001.
    if (port === '5173' || port === '3000') {
      const resolvedHost = host === '0.0.0.0' ? '127.0.0.1' : host
      apiBase = `http://${resolvedHost}:8001`
    } else {
      // Same-origin for single-container deploys (HF/docker unified app).
      apiBase = ''
    }
  }
  return apiBase.replace(/\/$/, '')
}

export const API_BASE = resolveApiBaseUrl()
export const API_PREFIX = '/api/v1'
