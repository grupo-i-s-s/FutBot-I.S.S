import { request } from '@/api/http.js'

export function join_friendly_match(idPartido, idEquipo) {
    return request('/partidos/unirse', { method: 'POST', body: { idPartido, idEquipo } })
}