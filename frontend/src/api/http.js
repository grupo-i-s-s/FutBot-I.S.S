const WRITE_METHODS = ['POST', 'PUT', 'PATCH', 'DELETE'];
const SESSION_INVALIDATED = 'futbot:session-invalidated';
let sessionRevision = 0;

export function getSessionRevision() {
    return sessionRevision;
}

export function advanceSessionRevision() {
    sessionRevision += 1;
}

export function subscribeToSessionInvalidation(listener) {
    window.addEventListener(SESSION_INVALIDATED, listener);
    return () => window.removeEventListener(SESSION_INVALIDATED, listener);
}

export class ApiError extends Error {
    constructor({status, code, message, fields = {}, diagnostics, retryAfter}) {
        super(message);
        this.name = 'ApiError';
        this.status = status;
        this.code = code;
        this.fields = fields;
        this.diagnostics = diagnostics;
        this.retryAfter = retryAfter;
    }
}

// Cliente HTTP común: usa rutas relativas con /api (proxy de Vite),
// distingue errores de red de errores funcionales y contempla respuestas 204.
export async function request(path, {method = 'GET', body, signal} = {}) {
    const revision = getSessionRevision();
    const headers = {Accept: 'application/json'};
    if (body !== undefined) headers['Content-Type'] = 'application/json';
    if (WRITE_METHODS.includes(method)) headers['X-FutBot-Request'] = '1';

    let response;
    try {
        response = await fetch(`/api${path}`, {
            method,
            headers,
            body: body === undefined ? undefined : JSON.stringify(body),
            credentials: 'same-origin',
            signal,
        });
    } catch (error) {
        if (error.name === 'AbortError') throw error;
        throw new ApiError({
            status: 0,
            code: 'NETWORK_ERROR',
            message: 'No se pudo conectar con el servidor.',
        });
    }

    if (response.status === 204) return null;

    const data = await response.json().catch(() => null);

    if (!response.ok) {
        const error = data?.error;
        // Una respuesta anterior al último cambio de sesión puede llegar tarde.
        if (response.status === 401 && error?.code === 'SESSION_INVALID'
            && revision === getSessionRevision() && !signal?.aborted) {
            window.dispatchEvent(new Event(SESSION_INVALIDATED));
        }
        throw new ApiError({
            status: response.status,
            code: error?.code ?? 'HTTP_ERROR',
            message: error?.message ?? (typeof data?.detail === 'string' ? data.detail : null) ?? 'Ocurrió un error inesperado.',
            fields: error?.fields ?? {},
            diagnostics: error?.diagnostics,
            retryAfter: response.headers?.get('Retry-After') ?? error?.fields?.retryAfter,
        });
    }

    return data;
}
