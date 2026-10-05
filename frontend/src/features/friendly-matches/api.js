import { request } from '@/api/http.js'

export function listFriendlyMatches(signal) {
  return request('/friendly-matches', { signal })
}

export function createFriendlyMatch(startDateTime) {
  return request('/friendly-matches', {
    method: 'POST',
    body: { startDateTime: new Date(startDateTime).toISOString() },
  })
}

export function joinFriendlyMatch(matchId) {
  return request('/friendly-matches/join', {
    method: 'POST',
    body: { idPartido: matchId },
  })
}
