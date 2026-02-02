import './App.css'
import { useEffect, useMemo, useState } from 'react'
import {
  aiReviewUpload,
  createUpload,
  getUploadSummary,
  HttpError,
  listLogs,
  listUploads,
  login,
  register,
  type LogDto,
  type UploadDto,
  type UploadSummaryDto,
  type UserDto,
  type AiReviewResponseDto,
} from './api'
import { clearToken, loadToken, saveToken } from './storage'

function App() {
  const [token, setToken] = useState<string | null>(() => loadToken())
  const [user, setUser] = useState<UserDto | null>(null)

  const [authMode, setAuthMode] = useState<'login' | 'register'>('login')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')

  const [file, setFile] = useState<File | null>(null)
  const [uploads, setUploads] = useState<UploadDto[]>([])
  const [selectedUploadId, setSelectedUploadId] = useState<string | null>(null)
  const [logs, setLogs] = useState<LogDto[]>([])
  const [onlyAnomalies, setOnlyAnomalies] = useState(true)
  const [limit, setLimit] = useState(200)

  const [bucketMinutes, setBucketMinutes] = useState(5)
  const [summary, setSummary] = useState<UploadSummaryDto | null>(null)

  const [aiOnlyAnomalies, setAiOnlyAnomalies] = useState(false)
  const [aiLimit, setAiLimit] = useState(25)
  const [aiChunkSize, setAiChunkSize] = useState(25)
  const [aiReview, setAiReview] = useState<AiReviewResponseDto | null>(null)
  const [aiLoading, setAiLoading] = useState(false)

  const [status, setStatus] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const isAuthed = Boolean(token)

  function forceLogout(message: string) {
    clearToken()
    setToken(null)
    setUser(null)
    setUploads([])
    setSelectedUploadId(null)
    setLogs([])
    setSummary(null)
    setAiReview(null)
    setAiLoading(false)
    setStatus(null)
    setError(message)
  }

  const selectedUpload = useMemo(
    () => uploads.find((u) => u.id === selectedUploadId) ?? null,
    [uploads, selectedUploadId],
  )

  async function refreshUploads() {
    if (!token) return
    const res = await listUploads(token)
    setUploads(res.data.uploads)
  }

  async function refreshLogs(uploadId: string) {
    if (!token) return
    const res = await listLogs(token, uploadId, onlyAnomalies, limit)
    setLogs(res.data.logs)
  }

  async function refreshSummary(uploadId: string) {
    if (!token) return
    const res = await getUploadSummary(token, uploadId, bucketMinutes)
    setSummary(res.data.summary)
  }

  useEffect(() => {
    if (!token) return
    refreshUploads().catch((e) => {
      if (e instanceof HttpError && e.status === 401) return forceLogout('Session expired. Please log in again.')
      setError(String((e as Error)?.message ?? e))
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  useEffect(() => {
    if (!token || !selectedUploadId) return
    refreshLogs(selectedUploadId).catch((e) => {
      if (e instanceof HttpError && e.status === 401) return forceLogout('Session expired. Please log in again.')
      setError(String((e as Error)?.message ?? e))
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, selectedUploadId, onlyAnomalies, limit])

  useEffect(() => {
    if (!token || !selectedUploadId) return
    refreshSummary(selectedUploadId).catch((e) => {
      if (e instanceof HttpError && e.status === 401) return forceLogout('Session expired. Please log in again.')
      setError(String((e as Error)?.message ?? e))
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, selectedUploadId, bucketMinutes])

  return (
    <>
      <div className="page">
        <header className="header">
          <div>
            <div className="title">Log Analyzer</div>
            <div className="subtitle">Upload Zscaler CSV logs, flag anomalies, and inspect results.</div>
          </div>

          <div className="headerRight">
            {isAuthed ? (
              <>
                <button
                  className="secondary"
                  onClick={() => {
                    forceLogout('Logged out.')
                  }}
                >
                  Logout
                </button>
              </>
            ) : (
              <span className="pill">Not logged in</span>
            )}
          </div>
        </header>

        {status ? <div className="banner ok">{status}</div> : null}
        {error ? <div className="banner err">{error}</div> : null}

        {!isAuthed ? (
          <section className="card">
            <div className="cardTitle">Authentication</div>
            <div className="row">
              <button
                className={authMode === 'login' ? 'primary' : 'secondary'}
                onClick={() => setAuthMode('login')}
              >
                Login
              </button>
              <button
                className={authMode === 'register' ? 'primary' : 'secondary'}
                onClick={() => setAuthMode('register')}
              >
                Register
              </button>
            </div>

            <form
              className="form"
              onSubmit={async (e) => {
                e.preventDefault()
                setError(null)
                setStatus(null)
                try {
                  if (authMode === 'register') {
                    await register(username, password)
                    setStatus('Registered successfully. You can log in now.')
                    setAuthMode('login')
                    return
                  }

                  const res = await login(username, password)
                  saveToken(res.data.access_token)
                  setToken(res.data.access_token)
                  setUser(res.data.user)
                  setStatus(`Logged in as ${res.data.user.username}`)
                } catch (err: unknown) {
                  if (err instanceof HttpError && err.status === 401) return setError(err.message)
                  setError(String((err as Error)?.message ?? err))
                }
              }}
            >
              <label>
                <div className="label">Username</div>
                <input value={username} onChange={(e) => setUsername(e.target.value)} autoComplete="username" />
              </label>
              <label>
                <div className="label">Password</div>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete={authMode === 'register' ? 'new-password' : 'current-password'}
                />
              </label>
              <button className="primary" type="submit">
                {authMode === 'register' ? 'Create account' : 'Login'}
              </button>
            </form>
          </section>
        ) : (
          <div className="grid">
            <section className="card">
              <div className="cardTitle">Upload CSV</div>
              <div className="muted">Upload a Zscaler CSV export. The backend will parse and flag anomalies.</div>

              <div className="row">
                <input
                  type="file"
                  accept=".csv,text/csv"
                  onChange={(e) => setFile(e.target.files?.[0] ?? null)}
                />
                <button
                  className="primary"
                  disabled={!file || !token}
                  onClick={async () => {
                    if (!file || !token) return
                    setError(null)
                    setStatus(null)
                    try {
                      const res = await createUpload(token, file)
                      setStatus(`Uploaded: ${res.data.upload.filename}`)
                      setFile(null)
                      await refreshUploads()
                      setSelectedUploadId(res.data.upload.id)
                      await refreshLogs(res.data.upload.id)
                      await refreshSummary(res.data.upload.id)
                    } catch (err: unknown) {
                      if (err instanceof HttpError && err.status === 401) return forceLogout('Session expired. Please log in again.')
                      setError(String((err as Error)?.message ?? err))
                    }
                  }}
                >
                  Upload
                </button>
              </div>
            </section>

            <section className="card">
              <div className="cardTitle">Your uploads</div>
              <div className="row">
                <button className="secondary" onClick={() => refreshUploads().catch((e) => setError(String(e)))}>
                  Refresh
                </button>
                {user ? <span className="pill">User: {user.username}</span> : null}
              </div>

              <div className="list">
                {uploads.length === 0 ? (
                  <div className="muted">No uploads yet.</div>
                ) : (
                  uploads.map((u) => (
                    <button
                      key={u.id}
                      className={`listItem ${u.id === selectedUploadId ? 'active' : ''}`}
                      onClick={async () => {
                        setSelectedUploadId(u.id)
                        setSummary(null)
                        setError(null)
                        setStatus(null)
                        try {
                          await refreshLogs(u.id)
                          await refreshSummary(u.id)
                        } catch (err: unknown) {
                          if (err instanceof HttpError && err.status === 401) return forceLogout('Session expired. Please log in again.')
                          setError(String((err as Error)?.message ?? err))
                        }
                      }}
                    >
                      <div className="listItemTitle">{u.filename}</div>
                      <div className="listItemMeta">
                        <span className="pill">{u.status}</span>
                        <span className="mono">{u.id.slice(0, 8)}…</span>
                      </div>
                    </button>
                  ))
                )}
              </div>
            </section>

            <section className="card span2">
              <div className="cardTitle">Summary {selectedUpload ? `for ${selectedUpload.filename}` : ''}</div>
              <div className="row">
                <label className="row">
                  <span className="muted">Bucket</span>
                  <input
                    className="small"
                    type="number"
                    min={1}
                    max={60}
                    value={bucketMinutes}
                    onChange={(e) => setBucketMinutes(Number(e.target.value))}
                  />
                  <span className="muted">min</span>
                </label>
                <button
                  className="secondary"
                  disabled={!selectedUploadId}
                  onClick={async () => {
                    if (!selectedUploadId) return
                    setError(null)
                    setStatus(null)
                    try {
                      await refreshSummary(selectedUploadId)
                    } catch (err: unknown) {
                      if (err instanceof HttpError && err.status === 401) return forceLogout('Session expired. Please log in again.')
                      setError(String((err as Error)?.message ?? err))
                    }
                  }}
                >
                  Refresh summary
                </button>
              </div>

              {!selectedUploadId ? (
                <div className="muted">Select an upload to view its summary.</div>
              ) : !summary ? (
                <div className="muted">Loading summary…</div>
              ) : (
                <div className="summaryGrid">
                  <div className="summaryBlock">
                    <div className="cardTitle">Highlights</div>
                    {summary.highlights.length === 0 ? (
                      <div className="muted">No highlights for this upload.</div>
                    ) : (
                      <ul className="summaryList">
                        {summary.highlights.map((h, idx) => (
                          <li key={idx}>{h}</li>
                        ))}
                      </ul>
                    )}
                  </div>

                  <div className="summaryBlock">
                    <div className="cardTitle">Top talkers</div>
                    {summary.topTalkers.length === 0 ? (
                      <div className="muted">No data.</div>
                    ) : (
                      <div className="tableWrap">
                        <table className="table">
                          <thead>
                            <tr>
                              <th>Client IP</th>
                              <th>Events</th>
                              <th>Bytes out</th>
                              <th>Anomalies</th>
                              <th>Max risk</th>
                            </tr>
                          </thead>
                          <tbody>
                            {summary.topTalkers.map((t) => (
                              <tr key={t.clientIp}>
                                <td className="mono">{t.clientIp}</td>
                                <td className="mono">{t.events}</td>
                                <td className="mono">{t.bytesOut}</td>
                                <td className="mono">{t.anomalies}</td>
                                <td className="mono">{t.maxRisk}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>

                  <div className="summaryBlock">
                    <div className="cardTitle">Top domains</div>
                    {summary.topDomains.length === 0 ? (
                      <div className="muted">No data.</div>
                    ) : (
                      <div className="tableWrap">
                        <table className="table">
                          <thead>
                            <tr>
                              <th>Domain</th>
                              <th>Events</th>
                              <th>Bytes out</th>
                              <th>Anomalies</th>
                              <th>Max risk</th>
                            </tr>
                          </thead>
                          <tbody>
                            {summary.topDomains.map((d) => (
                              <tr key={d.domain}>
                                <td className="mono">{d.domain}</td>
                                <td className="mono">{d.events}</td>
                                <td className="mono">{d.bytesOut}</td>
                                <td className="mono">{d.anomalies}</td>
                                <td className="mono">{d.maxRisk}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>

                  <div className="summaryBlock span2">
                    <div className="cardTitle">Timeline</div>
                    {summary.timeline.length === 0 ? (
                      <div className="muted">No data.</div>
                    ) : (
                      <div className="tableWrap">
                        <table className="table">
                          <thead>
                            <tr>
                              <th>Bucket start</th>
                              <th>Events</th>
                              <th>Bytes out</th>
                              <th>Anomalies</th>
                              <th>Top domains</th>
                            </tr>
                          </thead>
                          <tbody>
                            {summary.timeline.map((b) => (
                              <tr key={b.bucketStart}>
                                <td className="mono">{b.bucketStart}</td>
                                <td className="mono">{b.events}</td>
                                <td className="mono">{b.bytesOut}</td>
                                <td className="mono">{b.anomalies}</td>
                                <td className="mono">{b.topDomains.join(', ')}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </section>

            <section className="card span2">
              <div className="cardTitle">Logs {selectedUpload ? `for ${selectedUpload.filename}` : ''}</div>
              <div className="row">
                <label className="row">
                  <input
                    type="checkbox"
                    checked={onlyAnomalies}
                    onChange={(e) => setOnlyAnomalies(e.target.checked)}
                  />
                  <span>Only anomalies</span>
                </label>
                <label className="row">
                  <span className="muted">Limit</span>
                  <input
                    className="small"
                    type="number"
                    min={1}
                    max={5000}
                    value={limit}
                    onChange={(e) => setLimit(Number(e.target.value))}
                  />
                </label>
                <button
                  className="secondary"
                  disabled={!selectedUploadId}
                  onClick={async () => {
                    if (!selectedUploadId) return
                    setError(null)
                    setStatus(null)
                    try {
                      await refreshLogs(selectedUploadId)
                    } catch (err: unknown) {
                      if (err instanceof HttpError && err.status === 401) return forceLogout('Session expired. Please log in again.')
                      setError(String((err as Error)?.message ?? err))
                    }
                  }}
                >
                  Refresh logs
                </button>
              </div>

              {!selectedUploadId ? (
                <div className="muted">Select an upload to view its logs.</div>
              ) : (
                <div className="tableWrap">
                  <table className="table">
                    <thead>
                      <tr>
                        <th>Time</th>
                        <th>Client IP</th>
                        <th>Action</th>
                        <th>URL</th>
                        <th>Bytes</th>
                        <th>Risk</th>
                        <th>Confidence</th>
                        <th>Anomaly</th>
                      </tr>
                    </thead>
                    <tbody>
                      {logs.map((l) => (
                        <tr key={l.id} className={l.is_anomaly ? 'anomaly' : ''}>
                          <td className="mono">{l.timestamp}</td>
                          <td className="mono">{l.client_ip}</td>
                          <td>{l.action}</td>
                          <td className="truncate" title={l.url}>
                            {l.url}
                          </td>
                          <td className="mono">{l.bytes_sent}</td>
                          <td className="mono">{l.risk_score ?? ''}</td>
                          <td className="mono">
                            {typeof l.confidence_score === 'number' ? l.confidence_score.toFixed(2) : ''}
                          </td>
                          <td>{l.is_anomaly ? l.anomaly_note ?? 'flagged' : ''}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </section>

            <section className="card span2">
              <div className="cardTitle">AI Review (chunked)</div>
              <div className="muted">
                Sends a small batch of logs to the AI to classify anomalies with a short reason + confidence. Requires{' '}
                <span className="mono">OPENAI_API_KEY</span> on the backend.
              </div>

              <div className="row">
                <label className="row">
                  <input type="checkbox" checked={aiOnlyAnomalies} onChange={(e) => setAiOnlyAnomalies(e.target.checked)} />
                  <span>Only anomalies</span>
                </label>
                <label className="row">
                  <span className="muted">Limit</span>
                  <input
                    className="small"
                    type="number"
                    min={1}
                    max={200}
                    value={aiLimit}
                    onChange={(e) => setAiLimit(Number(e.target.value))}
                  />
                </label>
                <label className="row">
                  <span className="muted">Chunk</span>
                  <input
                    className="small"
                    type="number"
                    min={1}
                    max={50}
                    value={aiChunkSize}
                    onChange={(e) => setAiChunkSize(Number(e.target.value))}
                  />
                </label>
                <button
                  className="primary"
                  disabled={!selectedUploadId || !token || aiLoading}
                  onClick={async () => {
                    if (!selectedUploadId || !token) return
                    setError(null)
                    setStatus(null)
                    setAiReview(null)
                    setAiLoading(true)
                    try {
                      const res = await aiReviewUpload(token, {
                        uploadId: selectedUploadId,
                        limit: aiLimit,
                        chunkSize: aiChunkSize,
                        onlyAnomalies: aiOnlyAnomalies,
                      })
                      setAiReview(res.data)
                      setStatus(`AI reviewed ${res.data.analyzed_count} logs (${res.data.model ?? 'model unknown'})`)
                    } catch (err: unknown) {
                      if (err instanceof HttpError && err.status === 401) return forceLogout('Session expired. Please log in again.')
                      setError(String((err as Error)?.message ?? err))
                    } finally {
                      setAiLoading(false)
                    }
                  }}
                >
                  {aiLoading ? 'Reviewing…' : 'Run AI review'}
                </button>
              </div>

              {!selectedUploadId ? (
                <div className="muted" style={{ marginTop: 12 }}>
                  Select an upload first.
                </div>
              ) : !aiReview ? (
                <div className="muted" style={{ marginTop: 12 }}>
                  No AI review results yet.
                </div>
              ) : (
                <div style={{ marginTop: 12 }}>
                  <div className="row">
                    <span className="pill">Model: {aiReview.model ?? 'unknown'}</span>
                    <span className="pill">Analyzed: {aiReview.analyzed_count}</span>
                    <span className="pill">Chunk: {aiReview.chunk_size}</span>
                    {typeof aiReview.elapsed_ms === 'number' ? <span className="pill">Time: {aiReview.elapsed_ms}ms</span> : null}
                  </div>

                  <div className="tableWrap">
                    <table className="table">
                      <thead>
                        <tr>
                          <th>Time</th>
                          <th>Client IP</th>
                          <th>URL</th>
                          <th>AI anomaly</th>
                          <th>AI conf</th>
                          <th>AI reason</th>
                        </tr>
                      </thead>
                      <tbody>
                        {aiReview.results.map((r) => (
                          <tr key={r.id} className={r.is_anomalous ? 'anomaly' : ''}>
                            <td className="mono">{r.event?.timestamp ?? ''}</td>
                            <td className="mono">{r.event?.client_ip ?? ''}</td>
                            <td className="truncate" title={r.event?.url ?? ''}>
                              {r.event?.url ?? ''}
                            </td>
                            <td className="mono">{r.is_anomalous ? 'yes' : 'no'}</td>
                            <td className="mono">{typeof r.confidence === 'number' ? r.confidence.toFixed(2) : ''}</td>
                            <td>{r.reason}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </section>
          </div>
        )}
      </div>
    </>
  )
}

export default App
