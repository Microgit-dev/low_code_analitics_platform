import type { AuthToken, User } from '../../domain/entities/Auth'
import { httpClient } from './httpClient'

interface TokenResponse {
  access_token: string
  token_type: string
}

export const authApi = {
  async register(email: string, password: string): Promise<AuthToken> {
    const { data } = await httpClient.post<TokenResponse>('/auth/register', { email, password })
    return { accessToken: data.access_token }
  },

  async login(email: string, password: string): Promise<AuthToken> {
    const { data } = await httpClient.post<TokenResponse>('/auth/login', { email, password })
    return { accessToken: data.access_token }
  },

  async me(token: string): Promise<User> {
    const { data } = await httpClient.get<User>('/auth/me', {
      headers: { Authorization: `Bearer ${token}` }
    })
    return data
  }
}
