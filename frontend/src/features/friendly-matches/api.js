import { request } from '@/api/http.js'

export function join_friendly_match(idPartido, idEquipoA) {
    return request('/auth/friendly-matches', { method: 'POST', body: { idPartido, idEquipoA } })
}