import { useQuery, useQueryClient } from '@tanstack/react-query'
import { createContext, useCallback, useContext, useMemo } from 'react'
import type { ReactNode } from 'react'

import { api, ApiError } from './api'
import type { User } from './types'

interface AuthState {
  user: User | null
  loading: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()

  const me = useQuery({
    queryKey: ['me'],
    queryFn: async () => {
      try {
        return await api<User>('/me/')
      } catch (error) {
        // Not signed in is an expected state, not a failure.
        if (error instanceof ApiError && (error.status === 401 || error.status === 403)) return null
        throw error
      }
    },
    retry: false,
    staleTime: 5 * 60 * 1000,
  })

  const login = useCallback(
    async (username: string, password: string) => {
      const user = await api<User>('/auth/login/', { method: 'POST', body: { username, password } })
      queryClient.setQueryData(['me'], user)
    },
    [queryClient],
  )

  const logout = useCallback(async () => {
    await api<void>('/auth/logout/', { method: 'POST' })
    queryClient.clear()
    queryClient.setQueryData(['me'], null)
  }, [queryClient])

  const value = useMemo<AuthState>(
    () => ({ user: me.data ?? null, loading: me.isLoading, login, logout }),
    [me.data, me.isLoading, login, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthState {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used inside AuthProvider')
  return context
}
