import axios from 'axios'

const DEFAULT_API_BASE_URL = 'http://localhost:8000/api/v1'

function stripTrailingSlash(value: string): string {
  return value.endsWith('/') ? value.slice(0, -1) : value
}

function resolveApiBaseUrl(): string {
  const configuredBaseUrlRaw = import.meta.env.VITE_API_BASE_URL as string | undefined
  const configuredBaseUrl = configuredBaseUrlRaw?.trim()

  if (!configuredBaseUrl) {
    if (typeof window !== 'undefined' && window.location?.hostname) {
      return `${window.location.protocol}//${window.location.hostname}:8000/api/v1`
    }
    return DEFAULT_API_BASE_URL
  }

  try {
    const parsed = new URL(configuredBaseUrl)
    if (
      typeof window !== 'undefined' &&
      window.location?.hostname &&
      (parsed.hostname === 'localhost' || parsed.hostname === '127.0.0.1')
    ) {
      parsed.hostname = window.location.hostname
      return stripTrailingSlash(parsed.toString())
    }
    return stripTrailingSlash(parsed.toString())
  } catch {
    return stripTrailingSlash(configuredBaseUrl)
  }
}

export const httpClient = axios.create({
  baseURL: resolveApiBaseUrl()
})
