import axios from 'axios'

import { clearStoredToken, getStoredToken, setStoredToken } from '../auth/tokenStorage'

interface TokenRefreshResponse {
  access_token: string
}

type RetryableRequestConfig = {
  _retry?: boolean
  headers?: Record<string, string>
  url?: string
}

export const httpClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1'
})

const refreshClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1'
})

let refreshPromise: Promise<string | null> | null = null

const isAuthEndpoint = (url?: string): boolean => {
  const normalized = url ?? ''
  return normalized.includes('/auth/login') || normalized.includes('/auth/register') || normalized.includes('/auth/refresh')
}

const refreshAccessToken = async (): Promise<string | null> => {
  const currentToken = getStoredToken()
  if (!currentToken) {
    return null
  }

  if (!refreshPromise) {
    refreshPromise = refreshClient
      .post<TokenRefreshResponse>('/auth/refresh', undefined, {
        headers: { Authorization: `Bearer ${currentToken}` }
      })
      .then(({ data }) => {
        setStoredToken(data.access_token)
        return data.access_token
      })
      .catch(() => {
        clearStoredToken()
        return null
      })
      .finally(() => {
        refreshPromise = null
      })
  }

  return refreshPromise
}

httpClient.interceptors.request.use((config) => {
  const token = getStoredToken()
  const requestUrl = config.url ?? ''

  if (!token || isAuthEndpoint(requestUrl)) {
    return config
  }

  const nextHeaders = { ...(config.headers as Record<string, string> | undefined) }
  nextHeaders.Authorization = `Bearer ${token}`
  config.headers = nextHeaders

  return config
})

httpClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const status = error?.response?.status as number | undefined
    const originalConfig = error?.config as RetryableRequestConfig | undefined

    if (!status || status !== 401 || !originalConfig) {
      return Promise.reject(error)
    }

    if (originalConfig._retry || isAuthEndpoint(originalConfig.url)) {
      return Promise.reject(error)
    }

    originalConfig._retry = true

    const nextToken = await refreshAccessToken()
    if (!nextToken) {
      return Promise.reject(error)
    }

    originalConfig.headers = {
      ...(originalConfig.headers ?? {}),
      Authorization: `Bearer ${nextToken}`
    }

    return httpClient(originalConfig)
  }
)
