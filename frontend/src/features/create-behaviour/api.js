import { request } from '@/api/http.js';

export function createBehaviour(name, code) {
    return request('/behaviours', {
        method: 'POST',
        body: { name, code, kind: 'PLAYER' },
    });
}

export function createDtBehaviour(name, code) {
    return request('/dt/behaviours', {
        method: 'POST',
        body: { name, code },
    });
}

export function validateBehaviour(kind, code) {
    return request('/behaviours/validate', {
        method: 'POST',
        body: { kind, code },
    });
}
