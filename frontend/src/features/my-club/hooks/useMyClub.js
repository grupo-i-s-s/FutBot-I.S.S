import { useCallback, useEffect, useState } from 'react'
import { getMyClub, listBehaviours, listPlayers } from '../api'

function withBehaviourName(players, behaviours) {
    const behaviourNames = new Map(behaviours.map((behaviour) => [behaviour.id, behaviour.name]))

    return players.map((player) => ({
        ...player,
        behaviourName:
            player.behaviour?.name ?? behaviourNames.get(player.behaviourId) ?? 'Sin comportamiento',
    }))
}

export function useMyClub() {
    const [status, setStatus] = useState('loading')
    const [error, setError] = useState(null)
    const [club, setClub] = useState(null)
    const [players, setPlayers] = useState([])
    const [attempt, setAttempt] = useState(0)

    useEffect(() => {
        const controller = new AbortController()
        const options = { signal: controller.signal }

        async function loadClub() {
            setStatus('loading')
            setError(null)
            try {
                const [clubData, playerData, behaviourData] = await Promise.all([
                    getMyClub(options),
                    listPlayers(options),
                    listBehaviours(options),
                ])
                setClub(clubData)
                setPlayers(withBehaviourName(playerData?.items ?? [], behaviourData?.items ?? []))
                setStatus('ready')
            } catch (loadError) {
                // Una petición cancelada al desmontar no es un error para mostrar.
                if (loadError.name === 'AbortError') return
                setError(loadError)
                setStatus('error')
            }
        }

        loadClub()
        return () => controller.abort()
    }, [attempt])

    const reload = useCallback(() => setAttempt((value) => value + 1), [])

    return { status, error, club, players, reload, setClub }
}