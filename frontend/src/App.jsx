import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './auth'
import Layout from './components/Layout'
import Landing from './pages/Landing'
import SignIn from './pages/SignIn'
import Signup from './pages/Signup'
import Dashboard from './pages/Dashboard'
import Simulator from './pages/Simulator'
import Recommendations from './pages/Recommendations'
import Lender from './pages/Lender'
import LenderSignup from './pages/LenderSignup'

function Guard({ role, children }) {
  const { role: current } = useAuth()
  if (!current) return <Navigate to="/login" replace />
  if (current !== role) return <Navigate to={current === 'lender' ? '/lender' : '/dashboard'} replace />
  return children
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Landing />} />
      <Route path="/login" element={<SignIn />} />
      <Route path="/signup" element={<Signup />} />
      <Route path="/lender/signup" element={<LenderSignup />} />
      <Route element={<Guard role="user"><Layout /></Guard>}>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/simulator" element={<Simulator />} />
        <Route path="/recommendations" element={<Recommendations />} />
      </Route>
      <Route path="/lender" element={<Guard role="lender"><Lender /></Guard>} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
