export interface AuthToken {
  accessToken: string
}

export interface User {
  id: number
  email: string
}

export interface Workspace {
  id: number
  owner_id: number
  name: string
  description: string | null
  created_at: string
}
