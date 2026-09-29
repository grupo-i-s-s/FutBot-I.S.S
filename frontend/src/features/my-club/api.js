import { request } from '../../api/http'

// Endpoints según docs/api_endpoints.md.
export function getMyClub(options) {
    return request('/club/me', options)
}

export function listPlayers(options) {
    return request('/players', options)
}

export function listBehaviours(options) {
    return request('/behaviours', options)
}