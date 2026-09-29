const BASE = '/api/v1'
const KEY = 'altcredit.session'

export const session = {
  get() {
    try { return JSON.parse(localStorage.getItem(KEY) || sessionStorage.getItem(KEY) || 'null') } catch { return null }
  },
  set(s, remember) {
    this.clear()
    try { (remember ? localStorage : sessionStorage).setItem(KEY, JSON.stringify(s)) } catch { /* storage blocked */ }
  },
  clear() {
    try { localStorage.removeItem(KEY); sessionStorage.removeItem(KEY) } catch { /* ignore */ }
  },
}

export class ApiError extends Error {
  constructor(status, message) { super(message); this.status = status }
}

function detailText(d) {
  if (Array.isArray(d)) return d.map((e) => `${(e.loc || []).slice(1).join('.')}: ${e.msg}`).join('; ')
  return typeof d === 'string' ? d : 'Request failed'
}

async function request(path, { method = 'GET', body, form, raw, params } = {}) {
  const headers = {}
  if (body) headers['Content-Type'] = 'application/json'
  const qs = params ? '?' + new URLSearchParams(Object.entries(params).filter(([, v]) => v !== '' && v != null)) : ''
  let res
  try {
    res = await fetch(BASE + path + qs, { method, headers, body: form || (body ? JSON.stringify(body) : undefined) })
  } catch {
    throw new ApiError(0, 'Cannot reach the ALTcredit API. Is the backend running on port 8000?')
  }
  if (!res.ok) {
    let d
    try { d = (await res.json()).detail } catch { /* not json */ }
    throw new ApiError(res.status, detailText(d))
  }
  return raw ? res : res.json()
}

export const api = {
  login: (username, password, role) => request('/auth/login', { method: 'POST', body: { username, password, role } }),
  register: (body) => request('/auth/register', { method: 'POST', body }),
  registerLender: (body) => request('/auth/register-lender', { method: 'POST', body }),
  score: (uid) => request(`/scoring/${uid}`),
  exportJson: (uid) => request(`/scoring/${uid}/export.json`),
  dashboard: (uid) => request(`/dashboard/${uid}`),
  whatIf: (uid, body) => request(`/scoring/${uid}/what-if`, { method: 'POST', body }),
  target: (uid, productId) => request(`/scoring/${uid}/target`, { params: { product_id: productId } }),
  uploadTransactions: (uid, file) => {
    const form = new FormData()
    form.append('file', file)
    return request(`/scoring/${uid}/transactions`, { method: 'POST', form })
  },
  reportPdf: async (uid) => (await request(`/scoring/${uid}/report.pdf`, { raw: true })).blob(),
  explain: (uid) => request(`/scoring/${uid}/explain`),
  exportJson: async (uid) => (await request(`/scoring/${uid}/export.json`, { raw: true })).blob(),
  products: () => request('/products'),
  recommendations: (uid) => request(`/products/${uid}/recommendations`),
  apply: (uid, product_id) => request(`/products/${uid}/apply`, { method: 'POST', body: { product_id } }),
  userOffers: (uid) => request(`/products/${uid}/offers`),
  respondOffer: (uid, id, decision) => request(`/products/${uid}/offers/${id}/respond`, { method: 'POST', body: { decision } }),
  lenderMe: (id) => request(`/lender/${id}`),
  candidates: (id, params) => request(`/lender/${id}/candidates`, { params }),
  candidate: (id, anon) => request(`/lender/${id}/candidates/${anon}`),
  pushOffers: (id, body) => request(`/lender/${id}/offers`, { method: 'POST', body }),
  lenderOffers: (id, status) => request(`/lender/${id}/offers`, { params: { status } }),
}
