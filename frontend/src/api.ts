export type ApiError = {
  error?: { code?: string; message?: string; [k: string]: unknown }
}

export class HttpError extends Error {
  status: number
  payload: unknown

  constructor(message: string, status: number, payload: unknown) {
    super(message)
    this.name = 'HttpError'
    this.status = status
    this.payload = payload
  }
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
    const msg = (() => {
      if (typeof payload === 'object' && payload) {
        if ('error' in payload) return (payload as ApiError).error?.message ?? res.statusText
        // flask-jwt-extended commonly returns: { "msg": "Missing Authorization Header" }
        if ('msg' in payload && typeof (payload as any).msg === 'string') return (payload as any).msg
      }
      return res.statusText
    })()
    throw new HttpError(msg, res.status, payload)
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

export type SummaryTimelineBucketDto = {
  bucketStart: string
  events: number
  bytesOut: number
  anomalies: number
  topDomains: string[]
}

export type SummaryTalkerDto = {
  clientIp: string
  events: number
  bytesOut: number
  anomalies: number
  maxRisk: number
}

export type SummaryDomainDto = {
  domain: string
  events: number
  bytesOut: number
  anomalies: number
  maxRisk: number
}

export type UploadSummaryDto = {
  uploadId: string
  bucketMinutes: number
  timeline: SummaryTimelineBucketDto[]
  topTalkers: SummaryTalkerDto[]
  topDomains: SummaryDomainDto[]
  highlights: string[]
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
  // Always send explicitly so the backend behavior is unambiguous.
  params.set('only_anomalies', onlyAnomalies ? '1' : '0')
  params.set('limit', String(limit))
  return apiRequest<{ data: { logs: LogDto[] } }>(`/api/uploads/${uploadId}/logs?${params.toString()}`, {
    token,
  })
}

export async function getUploadSummary(token: string, uploadId: string, bucketMinutes: number) {
  const params = new URLSearchParams()
  params.set('bucket_minutes', String(bucketMinutes))
  return apiRequest<{ data: { summary: UploadSummaryDto } }>(`/api/uploads/${uploadId}/summary?${params.toString()}`, {
    token,
  })
}


