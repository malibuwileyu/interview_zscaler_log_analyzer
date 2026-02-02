import express from 'express'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { createProxyMiddleware } from 'http-proxy-middleware'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

const PORT = Number(process.env.PORT || 3000)

function normalizeBackendUrl(raw) {
  if (!raw) return null
  // Railway users often paste "backend-xyz.up.railway.app" without a scheme.
  if (raw.startsWith('http://') || raw.startsWith('https://')) return raw
  return `https://${raw}`
}

const BACKEND_URL = normalizeBackendUrl(process.env.BACKEND_URL || process.env.VITE_BACKEND_URL)

if (!BACKEND_URL) {
  // Railway: set BACKEND_URL (preferred) to your backend domain (e.g. https://backend-....up.railway.app)
  // Local: set BACKEND_URL=http://localhost:5000 (or wherever backend runs)
  console.error('Missing required env var: BACKEND_URL (or VITE_BACKEND_URL)')
  process.exit(1)
}

const app = express()

// Proxy API calls to backend (avoids CORS issues)
// Note: http-proxy-middleware v3 `createProxyMiddleware()` takes a single options object.
// We use `pathFilter` instead of mounting at `/api` so Express doesn't strip the `/api` prefix.
app.use(
  createProxyMiddleware({
    target: BACKEND_URL,
    changeOrigin: true,
    xfwd: true,
    pathFilter: '/api',
    logLevel: process.env.NODE_ENV === 'production' ? 'info' : 'debug',
    onProxyReq: (proxyReq, req) => {
      // Be explicit: forward auth header (some proxy/env combinations can drop it).
      const auth = req.headers['authorization']
      if (auth) proxyReq.setHeader('authorization', auth)
    },
  }),
)

// Serve built frontend
const distPath = path.join(__dirname, 'dist')
app.use(express.static(distPath))

// SPA fallback (Express 5: use regex instead of '*')
app.get(/.*/, (_req, res) => {
  res.sendFile(path.join(distPath, 'index.html'))
})

// health check to backend
app.get('/health', (_req, res) => res.json({ status: 'ok' }))

app.get('/health/backend', async (_req, res) => {
  try {
    const r = await fetch(`${BACKEND_URL}/health`)
    const text = await r.text()
    res.status(r.status).send(text)
  } catch (e) {
    res.status(502).json({ error: String(e?.message ?? e) })
  }
})

app.listen(PORT, '0.0.0.0', () => {
  console.log(`frontend listening on 0.0.0.0:${PORT}`)
  console.log(`proxying /api -> ${BACKEND_URL}`)
})


