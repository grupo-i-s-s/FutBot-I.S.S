import { useEffect, useState } from 'react'
import { Link } from 'react-router'
import { getLeagues } from './api'
import '../login/LoginPage.css'
import './LeagueListPage.css'

export default function LeagueListPage() {
    const [name, setName] = useState('')
    const [search, setSearch] = useState({ name: '' })
    const [leagues, setLeagues] = useState([])
    const [isLoading, setIsLoading] = useState(true)
    const [error, setError] = useState(null)

    useEffect(() => {
        const controller = new AbortController()

        async function loadLeagues() {
            setIsLoading(true)
            setError(null)

            try {
                const response = await getLeagues(
                    search.name,
                    controller.signal
                )

                if (!controller.signal.aborted) {
                    setLeagues(response.items)
                }
            } catch (error) {
                if (!controller.signal.aborted) {
                    setError(error)
                }
            } finally {
                if (!controller.signal.aborted) {
                    setIsLoading(false)
                }
            }
        }

        loadLeagues()

        return () => controller.abort()
    }, [search])

    function handleSubmit(event) {
        event.preventDefault()
        setIsLoading(true)
        setError(null)
        setSearch({ name: name.trim() })
    }

    function handleRetry() {
        setIsLoading(true)
        setError(null)
        setSearch({ name: search.name })
    }

    return (
        <main className="login-page leagues-page">
            <section className="login-card leagues-card">
                <h1 className="login-title">
                    Ligas disponibles<br />FutBot
                </h1>

                <form onSubmit={handleSubmit}>
                    <div className="form-group">
                        <label htmlFor="league-name">
                            Buscar por nombre
                        </label>

                        <input
                            id="league-name"
                            type="search"
                            placeholder="Nombre de la liga"
                            value={name}
                            onChange={(event) => setName(event.target.value)}
                        />
                    </div>

                    <button type="submit" className="login-button">
                        Buscar
                    </button>
                </form>

                <div className="leagues-results" aria-busy={isLoading}>
                    {isLoading && (
                        <p className="leagues-message" role="status">
                            Cargando ligas...
                        </p>
                    )}

                    {!isLoading && error && (
                        <div className="leagues-error" role="alert">
                            <p>
                                {error.status === 401
                                    ? 'Iniciá sesión para consultar las ligas.'
                                    : error.message || 'No se pudieron cargar las ligas.'}
                            </p>

                            {error.status === 401 ? (
                                <Link to="/login" className="leagues-link">
                                    Iniciar sesión
                                </Link>
                            ) : (
                                <button
                                    type="button"
                                    className="login-button"
                                    onClick={handleRetry}
                                >
                                    Reintentar
                                </button>
                            )}
                        </div>
                    )}

                    {!isLoading && !error && leagues.length === 0 && (
                        <p className="leagues-message" role="status">
                            {search.name
                                ? `No se encontraron ligas con el nombre "${search.name}".`
                                : 'No hay ligas disponibles.'}
                        </p>
                    )}

                    {!isLoading && !error && leagues.length > 0 && (
                        <ul className="leagues-list">
                            {leagues.map((league) => (
                                <li key={league.id} className="league-item">
                                    <h2 className="league-name">
                                        {league.name}
                                    </h2>

                                    <p>
                                        Equipos inscriptos: {league.registeredCount}
                                        {' / '}{league.maxTeams}
                                    </p>

                                    <p>
                                        Cupos disponibles: {league.availableSlots}
                                    </p>

                                    <p>
                                        Estado: {league.status === 'open'
                                            ? 'En espera'
                                            : league.status}
                                    </p>

                                    {league.isMember && (
                                        <p className="league-membership">
                                            Tu club ya está inscripto.
                                        </p>
                                    )}
                                    <Link
                                        to={league.isMember
                                            ? `/leagues/${league.id}/lobby`
                                            : `/leagues/${league.id}/join`}
                                        className="leagues-link"
                                    >
                                        {league.isMember ? 
                                            (<Link to={`/leagues/${league.id}/lobby`} className="leagues-link">Ver lobby </Link>
                                            ): league.canJoin ? 
                                            (<Link to={`/leagues/${league.id}/join`} className="leagues-link">Unirme a liga</Link>)
                                            : (<p className="leagues-message">Inscripción no disponible.</p>)}
                                    </Link>
                                </li>
                            ))}
                        </ul>
                    )}
                </div>

                <Link to="/mi-club" className="leagues-link">
                    Volver a mi club
                </Link>
            </section>
        </main>
    )
}
