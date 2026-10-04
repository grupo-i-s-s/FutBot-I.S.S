export function matchStreamUrl(matchId) {
  const id = Number(matchId)

  if (!Number.isSafeInteger(id) || id <= 0) {
    throw new Error('ID de partido inválido')
  }

  const url = new URL(`/api/matches/${id}/stream`, window.location.origin)
  url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'

  return url.toString()
}