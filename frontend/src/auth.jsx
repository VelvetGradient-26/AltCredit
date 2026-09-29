import { createContext, useContext, useState } from 'react'
import { api, session } from './api'

const Ctx = createContext(null)
export const useAuth = () => useContext(Ctx)

export function AuthProvider({ children }) {
  const [s, setS] = useState(session.get())
  const value = {
    session: s,
    role: s?.role,
    userId: s?.subject,
    async login(username, password, role, remember) {
      const res = await api.login(username, password, role)
      session.set(res, remember)
      setS(res)
      return res
    },
    async register(body) {
      const res = await api.register(body)
      const next = { role: 'user', subject: res.user_id }
      session.set(next, true)
      setS(next)
      return res
    },
    async registerLender(body) {
      const res = await api.registerLender(body)
      session.set(res, true)
      setS(res)
      return res
    },
    logout() { session.clear(); setS(null) },
  }
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}
