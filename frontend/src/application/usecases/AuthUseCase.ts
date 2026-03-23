import type { AuthToken, User } from '../../domain/entities/Auth'
import { authApi } from '../../infrastructure/api/authApi'

export class AuthUseCase {
  async register(email: string, password: string): Promise<AuthToken> {
    return authApi.register(email, password)
  }

  async login(email: string, password: string): Promise<AuthToken> {
    return authApi.login(email, password)
  }

  async me(token: string): Promise<User> {
    return authApi.me(token)
  }
}
