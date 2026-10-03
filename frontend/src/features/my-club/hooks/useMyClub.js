import { useCallback, useEffect, useState } from 'react'
import { getMyClub, listBehaviours, listMyLeagues, listPlayers } from '../api'

function withBehaviourName(players, behaviours) {
    const behaviourNames = new Map(behaviours.map((behaviour) => [behaviour.id, behaviour.name]))

    return players.map((player) => ({
        ...player,
        behaviourName:
            player.behaviour?.name ?? behaviourNames.get(player.behaviorId) ?? 'Sin comportamiento',
    }))
}

export function useMyClub() {
    const [status, setStatus] = useState('loading')
    const [error, setError] = useState(null)
    const [club, setClub] = useState(null)
    const [players, setPlayers] = useState([])
    const [behaviours, setBehaviours] = useState([])
    const [attempt, setAttempt] = useState(0)
    const [leagues, setLeagues] = useState([])

    useEffect(() => {
        const controller = new AbortController()
        const options = { signal: controller.signal }

        async function loadClub() {
            setStatus('loading')
            setError(null)
            try {
                const [clubData, playerData, behaviourData, leagueData] = await Promise.all([
                    getMyClub(options),
                    listPlayers(options),
                    listBehaviours(options),
                    listMyLeagues(options),
                ])
                if (controller.signal.aborted) return
                    setClub(clubData)
                    setBehaviours(behaviourData.items)
                    setPlayers(withBehaviourName(playerData.items, behaviourData.items))
                    setLeagues(leagueData.items)
                    setStatus('ready')
            } catch (loadError) {
                // Una petición cancelada al desmontar no es un error para mostrar.
               if (controller.signal.aborted || loadError.name === 'AbortError') return
                setError(loadError)
                setStatus('error')
            }
        }

        loadClub()
        return () => controller.abort()
    }, [attempt])

    const reload = useCallback(() => setAttempt((value) => value + 1), [])

    function updatePlayer(updatedPlayer) {
        const [namedPlayer] = withBehaviourName([updatedPlayer], behaviours)
        setPlayers((current) => current.map((player) =>
            player.id === namedPlayer.id ? namedPlayer : player
        ))
    }

    return { status, error, club, players, behaviours, leagues, reload, setClub, updatePlayer }
}
