export type ApiError = {
  error?: { code?: string; message?: string; [k: string]: unknown }
}

async function readJsonSafely(res: Response) {
  const text = await res.text()
  if (!text) return null
  try {
    return JSON.parse(text)
  } catch {
    return text
  }
}

export async function apiRequest<T>(
  path: string,
  opts: {
    method?: string
    token?: string | null
    body?: BodyInit | null
    headers?: Record<string, string>
  } = {},
): Promise<T> {
  const headers: Record<string, string> = {
    ...(opts.headers ?? {}),
  }
  if (opts.token) headers.Authorization = `Bearer ${opts.token}`

  const res = await fetch(path, {
    method: opts.method ?? 'GET',
    headers,
    body: opts.body ?? null,
  })

  const payload = await readJsonSafely(res)
  if (!res.ok) {
    const msg =
      typeof payload === 'object' && payload && 'error' in payload
        ? (payload as ApiError).error?.message ?? res.statusText
        : res.statusText
    throw new Error(msg)
  }

  return payload as T
}

export type UserDto = { id: string; username: string }
export type UploadDto = { id: string; user_id: string; filename: string; status: string }
export type LogDto = {
  id: string
  upload_id: string
  timestamp: string
  client_ip: string
  url: string
  action: string
  bytes_sent: number
  risk_score: number | null
  is_anomaly: boolean
  anomaly_note: string | null
}

export async function register(username: string, password: string) {
  return apiRequest<{ data: { user: UserDto } }>('/api/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })
}

export async function login(username: string, password: string) {
  return apiRequest<{ data: { access_token: string; user: UserDto } }>('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  })
}

export async function listUploads(token: string) {
  return apiRequest<{ data: { uploads: UploadDto[] } }>('/api/uploads/', {
    token,
  })
}

export async function createUpload(token: string, file: File) {
  const fd = new FormData()
  fd.append('file', file)
  return apiRequest<{ data: { upload: UploadDto } }>('/api/uploads/', {
    method: 'POST',
    token,
    body: fd,
  })
}

export async function listLogs(token: string, uploadId: string, onlyAnomalies: boolean, limit: number) {
  const params = new URLSearchParams()
  if (onlyAnomalies) params.set('only_anomalies', '1')
  params.set('limit', String(limit))
  return apiRequest<{ data: { logs: LogDto[] } }>(`/api/uploads/${uploadId}/logs?${params.toString()}`, {
    token,
  })
}


