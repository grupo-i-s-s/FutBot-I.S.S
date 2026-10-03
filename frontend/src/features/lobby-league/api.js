import { request } from '@/api/http.js'

export function obtenerLobby(id, signal) {
    return request(`/leagues/${id}/lobby`, { signal })
}