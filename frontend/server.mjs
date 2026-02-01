import express from 'express'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { createProxyMiddleware } from 'http-proxy-middleware'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

const PORT = Number(process.env.PORT || 3000)
const BACKEND_URL = process.env.BACKEND_URL

if (!BACKEND_URL) {
  // Railway: set BACKEND_URL to your backend public domain (e.g. https://backend-....up.railway.app)
  // Local: set BACKEND_URL=http://localhost:5000 (or wherever backend runs)
  console.error('Missing required env var: BACKEND_URL')
  process.exit(1)
}

const app = express()

// Proxy API calls to backend (avoids CORS issues)
app.use(
  '/api',
  createProxyMiddleware({
    target: BACKEND_URL,
    changeOrigin: true,
    xfwd: true,
    // Keep backend paths as-is (/api/...)
    pathRewrite: undefined,
    logLevel: process.env.NODE_ENV === 'production' ? 'info' : 'debug',
  }),
)

// Serve built frontend
const distPath = path.join(__dirname, 'dist')
app.use(express.static(distPath))

// SPA fallback (Express 5: use regex instead of '*')
app.get(/.*/, (_req, res) => {
  res.sendFile(path.join(distPath, 'index.html'))
})

app.listen(PORT, '0.0.0.0', () => {
  console.log(`frontend listening on 0.0.0.0:${PORT}`)
  console.log(`proxying /api -> ${BACKEND_URL}`)
})


