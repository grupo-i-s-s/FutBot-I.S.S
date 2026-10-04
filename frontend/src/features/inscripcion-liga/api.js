import { request } from '@/api/http.js'

export async function getDefaultTeam(options) {
    const [identity, response] = await Promise.all([
        request('/auth/me', options),
        request('/players', options),
    ])
    const players = response.items.slice(0, 6)
    return { clubId: identity.clubId, lineUp: players.map((player) => player.id), players }
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
