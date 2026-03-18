import { useEffect, useMemo, useState } from 'react'

const API_BASE_URL = import.meta.env?.VITE_API_BASE_URL || 'http://127.0.0.1:8080'

function toBasicAuth(username, password) {
  const raw = `${username}:${password}`
  // btoa is available in browsers
  return `Basic ${btoa(raw)}`
}

function AdminPage({ onBack }) {
  const [username, setUsername] = useState('admin')
  const [password, setPassword] = useState('')
  const [authHeader, setAuthHeader] = useState(null)

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [sessions, setSessions] = useState([])
  const [expandedKey, setExpandedKey] = useState(null)

  const grouped = useMemo(() => {
    const by = new Map()
    for (const s of sessions) {
      const key = (s?.user_email && String(s.user_email).trim().toLowerCase()) || (s?.student_id ? `student:${s.student_id}` : `session:${s?.id}`)
      if (!by.has(key)) by.set(key, [])
      by.get(key).push(s)
    }
    const groups = []
    for (const [key, items] of by.entries()) {
      items.sort((a, b) => {
        const da = a?.started_at ? String(a.started_at) : ''
        const db = b?.started_at ? String(b.started_at) : ''
        return db.localeCompare(da)
      })
      groups.push({ key, items })
    }
    groups.sort((a, b) => {
      const da = a.items?.[0]?.started_at ? String(a.items[0].started_at) : ''
      const db = b.items?.[0]?.started_at ? String(b.items[0].started_at) : ''
      return db.localeCompare(da)
    })
    return groups
  }, [sessions])

  const canAuth = useMemo(() => {
    return String(username || '').trim().length > 0 && String(password || '').trim().length > 0
  }, [username, password])

  const fetchSessions = async (hdr) => {
    setLoading(true)
    setError(null)
    try {
      const r = await fetch(`${API_BASE_URL}/api/v1/admin/sessions`, {
        headers: {
          Authorization: hdr,
        },
      })

      if (!r.ok) {
        const t = await r.text()
        throw new Error(t || `HTTP ${r.status}`)
      }

      const data = await r.json()
      setSessions(Array.isArray(data) ? data : [])
    } catch (e) {
      setError(String(e?.message || e))
      setSessions([])
    } finally {
      setLoading(false)
    }
  }

  const onLogin = async () => {
    if (!canAuth) return
    const hdr = toBasicAuth(username, password)
    setAuthHeader(hdr)
    try {
      localStorage.setItem('simco_admin_username', username)
      localStorage.setItem('simco_admin_password', password)
    } catch {
      // ignore
    }
    await fetchSessions(hdr)
  }

  const onLogout = () => {
    setAuthHeader(null)
    setSessions([])
    setError(null)
  }

  const onDelete = async (sessionId) => {
    if (!authHeader) return
    const ok = window.confirm(`Supprimer la session ${sessionId} ? Cette action est irréversible.`)
    if (!ok) return

    setLoading(true)
    setError(null)
    try {
      const r = await fetch(`${API_BASE_URL}/api/v1/admin/sessions/${sessionId}`, {
        method: 'DELETE',
        headers: { Authorization: authHeader },
      })

      if (!r.ok) {
        const t = await r.text()
        throw new Error(t || `HTTP ${r.status}`)
      }

      setSessions((prev) => prev.filter((s) => s?.id !== sessionId))
    } catch (e) {
      setError(String(e?.message || e))
    } finally {
      setLoading(false)
    }
  }

  const onDownloadPdf = async (sessionId) => {
    if (!authHeader) return
    setLoading(true)
    setError(null)
    try {
      const r = await fetch(`${API_BASE_URL}/api/v1/admin/sessions/${sessionId}/report.pdf`, {
        headers: { Authorization: authHeader },
      })

      if (!r.ok) {
        const t = await r.text()
        throw new Error(t || `HTTP ${r.status}`)
      }

      const blob = await r.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `session-${sessionId}-report.pdf`
      document.body.appendChild(a)
      a.click()
      a.remove()
      window.URL.revokeObjectURL(url)
    } catch (e) {
      setError(String(e?.message || e))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    try {
      const u = localStorage.getItem('simco_admin_username')
      const p = localStorage.getItem('simco_admin_password')
      if (u) setUsername(u)
      if (p) setPassword(p)
    } catch {
      // ignore
    }
  }, [])

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100 p-4 sm:p-6">
      <div className="max-w-6xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Administration SIMCO</h1>
            <p className="text-sm text-gray-600">Accès réservé — gestion des sessions et rapports</p>
          </div>
          <button
            onClick={onBack}
            className="bg-white hover:bg-gray-50 text-gray-800 font-semibold py-2 px-4 rounded-lg border border-gray-200"
          >
            Retour
          </button>
        </div>

        {!authHeader ? (
          <div className="bg-white rounded-xl shadow p-6 max-w-md">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">Connexion admin</h2>
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Username</label>
                <input
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                  autoComplete="username"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg"
                  autoComplete="current-password"
                />
              </div>

              {error && <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded p-2">{error}</div>}

              <button
                onClick={onLogin}
                disabled={!canAuth || loading}
                className="w-full bg-gray-900 hover:bg-black disabled:bg-gray-400 text-white font-semibold py-2 px-4 rounded-lg"
              >
                {loading ? 'Connexion...' : 'Se connecter'}
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="bg-white rounded-xl shadow p-4 flex items-center justify-between">
              <div className="text-sm text-gray-700">
                Connecté en tant que <span className="font-semibold">{username}</span>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => fetchSessions(authHeader)}
                  disabled={loading}
                  className="bg-white hover:bg-gray-50 text-gray-800 font-semibold py-2 px-4 rounded-lg border border-gray-200"
                >
                  Rafraîchir
                </button>
                <button
                  onClick={onLogout}
                  className="bg-white hover:bg-gray-50 text-gray-800 font-semibold py-2 px-4 rounded-lg border border-gray-200"
                >
                  Déconnexion
                </button>
              </div>
            </div>

            {error && <div className="text-sm text-red-700 bg-red-50 border border-red-200 rounded p-3">{error}</div>}

            <div className="bg-white rounded-xl shadow overflow-hidden">
              <div className="p-4 border-b border-gray-100 flex items-center justify-between">
                <h2 className="text-lg font-semibold text-gray-900">Sessions</h2>
                <div className="text-sm text-gray-600">{sessions.length} session(s)</div>
              </div>

              <div className="overflow-x-auto">
                <div className="divide-y divide-gray-100">
                  {grouped.map((g) => {
                    const first = g.items?.[0]
                    const displayName = first?.user_name || first?.student_id || 'Utilisateur'
                    const displayEmail = first?.user_email ? String(first.user_email) : null
                    const isOpen = expandedKey === g.key
                    return (
                      <div key={g.key} className="p-4">
                        <button
                          onClick={() => setExpandedKey(isOpen ? null : g.key)}
                          className="w-full flex items-center justify-between text-left"
                        >
                          <div>
                            <div className="font-semibold text-gray-900">{displayName}</div>
                            <div className="text-xs text-gray-600">{displayEmail || 'Email: N/A'} — {g.items.length} rapport(s)</div>
                          </div>
                          <div className="text-sm text-gray-500">{isOpen ? '▲' : '▼'}</div>
                        </button>

                        {isOpen && (
                          <div className="mt-4 overflow-x-auto">
                            <table className="min-w-full text-sm">
                              <thead className="bg-gray-50 text-gray-700">
                                <tr>
                                  <th className="text-left font-semibold px-3 py-2">Session</th>
                                  <th className="text-left font-semibold px-3 py-2">Matière</th>
                                  <th className="text-left font-semibold px-3 py-2">Niveau</th>
                                  <th className="text-left font-semibold px-3 py-2">Classe</th>
                                  <th className="text-left font-semibold px-3 py-2">Réponses</th>
                                  <th className="text-left font-semibold px-3 py-2">Captures CV</th>
                                  <th className="text-left font-semibold px-3 py-2">Début</th>
                                  <th className="text-right font-semibold px-3 py-2">Actions</th>
                                </tr>
                              </thead>
                              <tbody>
                                {g.items.map((s) => (
                                  <tr key={s.id} className="border-t border-gray-100 hover:bg-gray-50">
                                    <td className="px-3 py-2 font-semibold text-gray-900">{s.id}</td>
                                    <td className="px-3 py-2 text-gray-800">{s.subject || '-'}</td>
                                    <td className="px-3 py-2 text-gray-800">{s.level || '-'}</td>
                                    <td className="px-3 py-2 text-gray-800">{s.class_level || '-'}</td>
                                    <td className="px-3 py-2 text-gray-800">{s.answers_count}</td>
                                    <td className="px-3 py-2 text-gray-800">{s.emotion_events_count}</td>
                                    <td className="px-3 py-2 text-gray-700">{s.started_at ? String(s.started_at).replace('T', ' ').slice(0, 19) : '-'}</td>
                                    <td className="px-3 py-2">
                                      <div className="flex justify-end gap-2">
                                        <button
                                          onClick={() => onDownloadPdf(s.id)}
                                          disabled={loading}
                                          className="bg-green-600 hover:bg-green-700 disabled:bg-gray-400 text-white font-semibold py-2 px-3 rounded-lg"
                                        >
                                          PDF
                                        </button>
                                        <button
                                          onClick={() => onDelete(s.id)}
                                          disabled={loading}
                                          className="bg-red-600 hover:bg-red-700 disabled:bg-gray-400 text-white font-semibold py-2 px-3 rounded-lg"
                                        >
                                          Supprimer
                                        </button>
                                      </div>
                                    </td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        )}
                      </div>
                    )
                  })}

                  {sessions.length === 0 && !loading && (
                    <div className="px-4 py-8 text-center text-gray-600">
                      Aucune session à afficher
                    </div>
                  )}

                  {loading && (
                    <div className="px-4 py-8 text-center text-gray-600">Chargement...</div>
                  )}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default AdminPage
