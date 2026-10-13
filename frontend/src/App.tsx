import { BrowserRouter, Link, Navigate, Route, Routes, useLocation } from 'react-router-dom'

import { Layout } from './components/Layout'
import { EmptyState, Spinner } from './components/ui'
import { useAuth } from './lib/auth'
import { Cameras } from './pages/Cameras'
import { Landing } from './pages/Landing'
import { Login } from './pages/Login'
import { Overview } from './pages/Overview'
import { PeriodSettings } from './pages/PeriodSettings'
import { Reports } from './pages/Reports'
import { SessionDetail } from './pages/SessionDetail'
import { Sessions } from './pages/Sessions'
import { Setup } from './pages/Setup'
import { Students } from './pages/Students'

function Protected() {
  const { user, loading } = useAuth()
  const location = useLocation()
  if (loading) {
    return (
      <div className="flex min-h-full items-center justify-center">
        <Spinner label="Checking sign-in" />
      </div>
    )
  }
  if (user) return <Layout />
  // Signed-out visitors see the landing page at the root and the sign-in page everywhere else.
  return location.pathname === '/' ? <Landing /> : <Navigate to="/login" replace />
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
        <Route path="/about" element={<Landing />} />
        <Route element={<Protected />}>
          <Route index element={<Overview />} />
          <Route path="sessions" element={<Sessions />} />
          <Route path="sessions/:id" element={<SessionDetail />} />
          <Route path="students" element={<Students />} />
          <Route path="reports" element={<Reports />} />
          <Route path="cameras" element={<Cameras />} />
          <Route path="setup" element={<Setup />} />
          <Route path="settings/periods" element={<PeriodSettings />} />
          <Route path="*" element={<NotFound />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
