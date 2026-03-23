import { defineStore } from 'pinia'

import type { User } from '../../domain/entities/Auth'
import { AuthUseCase } from '../../application/usecases/AuthUseCase'

const authUseCase = new AuthUseCase()
const TOKEN_KEY = 'low_code_token'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem(TOKEN_KEY) as string | null,
    me: null as User | null,
    loading: false,
    error: ''
  }),

  getters: {
    isAuthenticated: (state): boolean => Boolean(state.token)
  },

  actions: {
    async register(email: string, password: string): Promise<void> {
      this.loading = true
      this.error = ''
      try {
        const tokenResponse = await authUseCase.register(email, password)
        this.setToken(tokenResponse.accessToken)
        await this.fetchMe()
      } catch (error: unknown) {
        this.error = 'Не удалось зарегистрироваться'
        throw error
      } finally {
        this.loading = false
      }
    },

    async login(email: string, password: string): Promise<void> {
      this.loading = true
      this.error = ''
      try {
        const tokenResponse = await authUseCase.login(email, password)
        this.setToken(tokenResponse.accessToken)
        await this.fetchMe()
      } catch (error: unknown) {
        this.error = 'Неверный email или пароль'
        throw error
      } finally {
        this.loading = false
      }
    },

    async fetchMe(): Promise<void> {
      if (!this.token) {
        this.me = null
        return
      }
      try {
        this.me = await authUseCase.me(this.token)
      } catch {
        this.logout()
      }
    },

    setToken(token: string): void {
      this.token = token
      localStorage.setItem(TOKEN_KEY, token)
    },

    logout(): void {
      this.token = null
      this.me = null
      localStorage.removeItem(TOKEN_KEY)
    }
  }
})
