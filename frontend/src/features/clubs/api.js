import { ApiError, request } from '../../api/http.js'

function readClub(data) {
  if (!data || !Number.isInteger(data.id) || typeof data.name !== 'string'
      || typeof data.avatar !== 'string' || typeof data.friendlyAvailable !== 'boolean') {
    throw new ApiError('No pudimos interpretar los datos del club.', { code: 'INVALID_RESPONSE' })
  }
  return data
}

export async function getMyClub({ signal } = {}) {
  return readClub(await request('/club/me', { signal }))
}

export async function updateClubAvailability(friendlyAvailable, { signal } = {}) {
  return readClub(await request('/club/me', {
    method: 'PATCH',
    body: { friendlyAvailable },
    signal,
  }))
}

export async function updateClubName(name, { signal } = {}) {
  return readClub(await request('/club/me', {
    method: 'PATCH',
    body: { name },
    signal,
  }))
}
