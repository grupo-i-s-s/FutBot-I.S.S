export async function updatePlayerBehaviour(playerId, behaviourId) {
  const response = await fetch(`/api/players/${playerId}/behaviour`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ behaviourId }),
  })

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    throw new Error(errorData.detail || 'No se pudo asignar el comportamiento.')
  }

  return response.json()
}