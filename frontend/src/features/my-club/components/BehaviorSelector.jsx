import { useState } from 'react'
import { assignPlayerBehaviour } from '../api'

export function BehaviorSelector({ player, behaviours, onBehaviourAssigned }) {
    const [behaviourId, setBehaviourId] = useState('')
    const [loading, setLoading] = useState(false)
    const [error, setError] = useState('')

    async function handleSubmit(event) {
        event.preventDefault()
        if (!behaviourId) return

        setLoading(true)
        setError('')
        try {
            const updatedPlayer = await assignPlayerBehaviour(player.id, Number(behaviourId))
            onBehaviourAssigned(updatedPlayer)
            setBehaviourId('')
        } catch (requestError) {
            setError(requestError.message)
        } finally {
            setLoading(false)
        }
    }

    return (
        <form onSubmit={handleSubmit} className="mt-2 flex flex-wrap items-center gap-2">
            <label className="sr-only" htmlFor={`behaviour-${player.id}`}>
                Nuevo comportamiento para {player.name}
            </label>
            <select
                id={`behaviour-${player.id}`}
                value={behaviourId}
                onChange={(event) => setBehaviourId(event.target.value)}
                disabled={loading}
                required
                className="rounded border border-input bg-background px-2 py-1 text-sm"
            >
                <option value="">Elegir comportamiento</option>
                {behaviours.map((behaviour) => (
                    <option key={behaviour.id} value={behaviour.id}>
                        {behaviour.name}
                    </option>
                ))}
            </select>
            <button type="submit" disabled={loading || !behaviourId} className="text-sm underline disabled:opacity-50">
                {loading ? 'Guardando…' : 'Asignar'}
            </button>
            {error && <p role="alert" className="w-full text-sm text-destructive">{error}</p>}
        </form>
    )
}
