export function resolveApiBaseUrl() {
  const envBase = import.meta.env.VITE_FRONTEND_API_BASE_URL || import.meta.env.VITE_API_BASE
  const runtimeBase = window.__APP_CONFIG__?.FRONTEND_API_BASE_URL

  let apiBase = envBase || runtimeBase
  if (!apiBase) {
    if (typeof window !== 'undefined') {
      const host = window.location.hostname
      apiBase = `http://${host}:8001`
    } else {
      apiBase = 'http://localhost:8001'
    }
  }
  return apiBase.replace(/\/$/, '')
}

export const API_BASE = resolveApiBaseUrl()
export const API_PREFIX = '/api/v1'
