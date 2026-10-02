import { request } from '@/api/http.js'

export function getDefaultTeam(options) {
    return request('/team/default', options)
}

export function joinLeague(leagueId, clubId, lineUp, accessCode) {
    return request(`/leagues/${leagueId}/join`, {
        method: 'POST',
        body: {
            clubId,
            lineUp,
            ...(accessCode ? { accessCode } : {}),
        },
    })
}

export function getLeagueLobby(leagueId, options) {
    return request(`/leagues/${leagueId}/lobby`, options)
}
