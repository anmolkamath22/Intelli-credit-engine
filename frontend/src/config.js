export function resolveApiBaseUrl() {
  const envBase = import.meta.env.VITE_FRONTEND_API_BASE_URL || import.meta.env.VITE_API_BASE
  const runtimeBase = window.__APP_CONFIG__?.FRONTEND_API_BASE_URL

  let apiBase = envBase || runtimeBase
  if (!apiBase) {
    // If frontend is served by Vite dev server (5173/3000), target backend on same host:8001.
    // Otherwise use same-origin (single-container / reverse proxy deployments).
    if (typeof window !== 'undefined') {
      const host = window.location.hostname
      const port = window.location.port
      if (port === '5173' || port === '3000') {
        apiBase = `http://${host}:8001`
      } else {
        apiBase = window.location.origin
      }
    } else {
      apiBase = 'http://localhost:8001'
    }
  }
  return apiBase.replace(/\/$/, '')
}

export const API_BASE = resolveApiBaseUrl()
export const API_PREFIX = '/api/v1'
