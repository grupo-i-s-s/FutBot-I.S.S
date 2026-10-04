import { request } from '@/api/http.js'

export function join_friendly_match(idPartido, idEquipo) {
    return request('/partidos/unirse', { method: 'POST', body: { idPartido, idEquipo } })
}

export function create_friendly_match(matchTime){
    return request('/friendly-matches', { method : 'POST', body: {startDateTime: matchTime}})
}