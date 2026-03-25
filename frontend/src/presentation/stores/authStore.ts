import { defineStore } from 'pinia'

import type { User } from '../../domain/entities/Auth'
import { AuthUseCase } from '../../application/usecases/AuthUseCase'
import { clearStoredToken, getStoredToken, setStoredToken } from '../../infrastructure/auth/tokenStorage'

const authUseCase = new AuthUseCase()

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: getStoredToken(),
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

    async changePassword(currentPassword: string, newPassword: string): Promise<void> {
      if (!this.token) {
        throw new Error('Not authenticated')
      }

      this.loading = true
      this.error = ''
      try {
        await authUseCase.changePassword(this.token, currentPassword, newPassword)
      } catch (error: unknown) {
        this.error = 'Не удалось изменить пароль'
        throw error
      } finally {
        this.loading = false
      }
    },

    setToken(token: string): void {
      this.token = token
      setStoredToken(token)
    },

    logout(): void {
      this.token = null
      this.me = null
      clearStoredToken()
    }
  }
})
