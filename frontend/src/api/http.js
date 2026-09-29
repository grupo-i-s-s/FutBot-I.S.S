export class ApiError extends Error {
  constructor(message, { status = 0, code = 'NETWORK_ERROR', fields = {} } = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.fields = fields
  }
}

// Las cookies viajan por el proxy de Vite. El token de sesión nunca se lee en JS.
export async function request(path, { method = 'GET', body, signal } = {}) {
  const controller = new AbortController()
  const handleAbort = () => controller.abort()
  signal?.addEventListener('abort', handleAbort, { once: true })
  if (signal?.aborted) controller.abort()
  const timeout = setTimeout(() => controller.abort(), 10000)

  try {
    const response = await fetch(`/api${path}`, {
      method,
      credentials: 'same-origin',
      signal: controller.signal,
      headers: {
        Accept: 'application/json',
        ...(body !== undefined && { 'Content-Type': 'application/json' }),
        ...(!['GET', 'HEAD'].includes(method) && { 'X-Futbot-Request': '1' }),
      },
      ...(body !== undefined && { body: JSON.stringify(body) }),
    })

    if (response.status === 204) return null
    const data = await response.json().catch(() => null)
    if (!response.ok) {
      throw new ApiError(data?.error?.message || 'El servidor no pudo completar la solicitud.', {
        status: response.status,
        code: data?.error?.code || 'HTTP_ERROR',
        fields: data?.error?.fields || {},
      })
    }
    if (data === null) {
      throw new ApiError('El servidor devolvió una respuesta inesperada.', {
        status: response.status,
        code: 'INVALID_RESPONSE',
      })
    }
    return data
  } catch (error) {
    if (signal?.aborted || error instanceof ApiError) throw error
    if (controller.signal.aborted) {
      throw new ApiError('El servidor tardó demasiado en responder.', { code: 'REQUEST_TIMEOUT' })
    }
    throw new ApiError('No pudimos conectarnos con el servidor. Revisá tu conexión.')
  } finally {
    clearTimeout(timeout)
    signal?.removeEventListener('abort', handleAbort)
  }
}
