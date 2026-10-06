const WRITE_METHODS = ['POST', 'PUT', 'PATCH', 'DELETE'];

export class ApiError extends Error {
    constructor({status, code, message, fields = {}}) {
        super(message);
        this.name = 'ApiError';
        this.status = status;
        this.code = code;
        this.fields = fields;
    }
}

// Cliente HTTP común: usa rutas relativas con /api (proxy de Vite),
// distingue errores de red de errores funcionales y contempla respuestas 204.
export async function request(path, {method = 'GET', body, signal} = {}) {
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
        throw new ApiError({
            status: response.status,
            code: error?.code ?? 'HTTP_ERROR',
            message: error?.message ?? (typeof data?.detail === 'string' ? data.detail : null) ?? 'Ocurrió un error inesperado.',
            fields: error?.fields ?? {},
        });
    }

    return data;
}
