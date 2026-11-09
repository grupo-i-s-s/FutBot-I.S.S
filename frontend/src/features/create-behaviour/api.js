import { request } from '@/api/http.js';

export function createBehaviour(name, code) {
    return request('/behaviours', {
        method: 'POST',
        body: { name, code, kind: 'PLAYER' },
    });
}