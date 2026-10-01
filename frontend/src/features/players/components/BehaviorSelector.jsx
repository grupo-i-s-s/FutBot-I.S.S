import { useState } from 'react'
import { updatePlayerBehaviour } from '../api'

export function BehaviorSelector({ player, onBehaviourAssigned }) {
  const [behaviourId, setBehaviourId] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      const updatedPlayer = await updatePlayerBehaviour(
        player.id,
        Number(behaviourId),
      )

      onBehaviourAssigned(updatedPlayer)
      setBehaviourId('')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      <div className="flex flex-col gap-1.5">
        <label className="text-sm font-semibold text-ink">
          Seleccionar Nuevo Comportamiento (ID):
        </label>

        <input
          type="number"
          value={behaviourId}
          onChange={(e) => setBehaviourId(e.target.value)}
          placeholder="Ej. 1, 2, 3..."
          className="rounded-lg border border-frame p-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-brand"
          required
        />
      </div>

      {error && (
        <p className="rounded bg-red-50 p-2 text-sm text-red-600">
          {error}
        </p>
      )}

      <button
        type="submit"
        disabled={loading}
        className="cursor-pointer rounded-lg bg-brand px-4 py-2.5 text-sm font-semibold text-white transition-opacity hover:opacity-90 disabled:opacity-50"
      >
        {loading ? 'Guardando...' : 'Asignar Comportamiento'}
      </button>
    </form>
  )
}
