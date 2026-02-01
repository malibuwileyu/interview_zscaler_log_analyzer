# Log Analyzer Frontend

Minimal React UI (Vite) plus an Express server for production that serves the built app and proxies `/api/*` to the backend.

## Local dev

1) Start the backend (separately).

2) (Optional) create `env.local` from `env.example`:

```bash
cp env.example env.local
```

3) Run the Vite dev server:

```bash
npm run dev
```

In dev, the UI calls `/api/*` and Vite proxies to `VITE_BACKEND_URL` (defaults to `http://localhost:5000`).

## Production / Railway

This repo is a monorepo. Deploy the **frontend** as its own Railway service with root directory set to `frontend/`.

- **Build command**: `npm run build`
- **Start command**: `npm start`
- **Env vars**:
  - `BACKEND_URL=https://<your-backend-domain>` (required)

The Express server will listen on Railway’s assigned `$PORT` automatically and proxy `/api/*` to `BACKEND_URL`.
