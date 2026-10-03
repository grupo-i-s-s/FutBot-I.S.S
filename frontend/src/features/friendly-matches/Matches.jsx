import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { createFriendlyMatch, joinFriendlyMatch, listFriendlyMatches } from './api.js'
import { useMatchConnection } from './hooks/useMatchConnection.js'
import './Matches.css'

export default function MatchesPage() {
  const [matches, setMatches] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [joiningId, setJoiningId] = useState(null)
  const [activeMatchId, setActiveMatchId] = useState(null)
  const [startDateTime, setStartDateTime] = useState('')
  const [creating, setCreating] = useState(false)
  const connectionStatus = useMatchConnection(activeMatchId)

  useEffect(() => {
    const controller = new AbortController()
    listFriendlyMatches(controller.signal)
      .then(setMatches)
      .catch((cause) => {
        if (cause.name !== 'AbortError') setError(cause.message)
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false)
      })
    return () => controller.abort()
  }, [])

  async function handleJoinMatch(matchId) {
    setError('')
    setJoiningId(matchId)
    try {
      await joinFriendlyMatch(matchId)
      setMatches((current) => current.filter((match) => match.matchId !== matchId))
      setActiveMatchId(matchId)
    } catch (cause) {
      setError(cause.message)
    } finally {
      setJoiningId(null)
    }
  }

  async function handleCreateMatch(event) {
    event.preventDefault()
    setError('')
    setCreating(true)
    try {
      const date = new Date(startDateTime)
      if (Number.isNaN(date.getTime())) throw new Error('Elegí una fecha válida.')
      const created = await createFriendlyMatch(date.toISOString())
      setActiveMatchId(created.matchId)
      setStartDateTime('')
    } catch (cause) {
      setError(cause.message)
    } finally {
      setCreating(false)
    }
  }

  return (
    <main className="Friendly-Matches">
      <Card className="main-card">
        <h1 className="page-title">Partidos amistosos</h1>
        {error && <p role="alert">{error}</p>}
        <form onSubmit={handleCreateMatch}>
          <label htmlFor="match-start">Fecha y hora del amistoso</label>
          <input
            id="match-start"
            type="datetime-local"
            required
            value={startDateTime}
            onChange={(event) => setStartDateTime(event.target.value)}
          />
          <Button type="submit" disabled={creating}>
            {creating ? 'Creando...' : 'Crear amistoso'}
          </Button>
        </form>
        {activeMatchId && <p>Partido {activeMatchId}: conexión {connectionStatus}</p>}
        {loading ? (
          <p>Cargando partidos...</p>
        ) : matches.length === 0 ? (
          <p>No hay amistosos disponibles.</p>
        ) : (
          <div className="container">
            {matches.map((match) => (
              <div key={match.matchId} className="match-box">
                <span className="match-title">{match.creatorClubName}</span>
                <span className="match-date">
                  {new Date(match.startDateTime).toLocaleString('es-AR')}
                </span>
                <Button
                  className="join-button"
                  disabled={joiningId !== null}
                  onClick={() => handleJoinMatch(match.matchId)}
                >
                  {joiningId === match.matchId ? 'Uniéndose...' : 'Unirse'}
                </Button>
              </div>
            ))}
          </div>
        )}
      </Card>
    </main>
  )
}
