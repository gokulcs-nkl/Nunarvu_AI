import { BrowserRouter, Link, Navigate, Route, Routes } from 'react-router-dom'

import { Layout } from './components/Layout'
import { EmptyState, Spinner } from './components/ui'
import { useAuth } from './lib/auth'
import { Login } from './pages/Login'
import { Overview } from './pages/Overview'
import { PeriodSettings } from './pages/PeriodSettings'

function Protected() {
  const { user, loading } = useAuth()
  if (loading) {
    return (
      <div className="flex min-h-full items-center justify-center">
        <Spinner label="Checking sign-in" />
      </div>
    )
  }
  return user ? <Layout /> : <Navigate to="/login" replace />
}

function NotFound() {
  return (
    <EmptyState
      title="Page not found"
      action={
        <Link to="/" className="text-sm font-medium text-brand hover:underline">
          Back to overview
        </Link>
      }
    />
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route element={<Protected />}>
          <Route index element={<Overview />} />
          <Route path="settings/periods" element={<PeriodSettings />} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
