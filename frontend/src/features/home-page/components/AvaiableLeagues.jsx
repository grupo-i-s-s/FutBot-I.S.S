import { Link } from 'react-router'
import { Trophy, ArrowRight } from 'lucide-react'
import '../homePage.css'
import { useEffect, useState } from 'react'
import { getLeagues } from '../../list-leagues/api'


export default function AvaiableLeagues(){

    const [leagues, setLeagues] = useState([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState('')

    useEffect(() => {
        const controller = new AbortController()

        getLeagues('', controller.signal)
            .then((data) => {
                if (controller.signal.aborted) return

                setLeagues(
                    data.items.map((league) => ({
                        ...league,
                        teams: league.registeredCount,
                        type: league.isPrivate ? 'Privada' : 'Pública',
                    }))
                )
            })
            .catch((err) => {
                if (!controller.signal.aborted) {
                    setError(
                        err.status === 401
                            ? 'Iniciá sesión para ver las ligas.'
                            : err.message
                    )
                }
            })
            .finally(() => {
                if (!controller.signal.aborted) {
                    setLoading(false)
                }
            })

        return () => controller.abort()
    }, [])

    return(
    <aside className="home-panel home-leagues" aria-labelledby="home-leagues-title"
                >
                    <div className="home-panel-heading">
                        <span className="home-panel-icon">
                            <Trophy size={22} aria-hidden="true" />
                        </span>
                        <div>
                            <h2 id="home-leagues-title">Ligas disponibles</h2>
                        </div>
                    </div>
                    
                    <Link to="/ligas-disponibles" className="home-panel-link">
                        Ver todas las ligas
                    </Link>

                    <Link to="/crear-liga" className="home-panel-link">
                        Crear una liga Publica
                        <ArrowRight size={17} aria-hidden="true" />
                    </Link>

                    <Link to="/crear-liga-privada" className="home-panel-link">
                        Crear una liga Privada
                        <ArrowRight size={17} aria-hidden="true" />
                    </Link>

                    {loading && <p role="status">Cargando ligas…</p>}
                    {error && <p role="alert">{error}</p>}

                    {!loading && !error && leagues.length === 0 && (
                        <p>No hay ligas disponibles.</p>
                    )}
                    
                    <ul className="home-list">
                        {leagues.slice(0, 3).map((league) => (
                            <li key={league.id} className="home-list-card">
                                <div className="home-item-heading">
                                    <h3>{league.name}</h3>
                                    <span
                                        className={`home-tag ${
                                            league.type === 'Privada'
                                                ? 'home-tag-private'
                                                : ''
                                        }`}
                                    >
                                        {league.type}
                                    </span>
                                </div>

                                <p className="home-item-description">
                                    {league.teams} de {league.maxTeams} clubes
                                </p>

                                <div
                                    className="home-progress"
                                    role="progressbar"
                                    aria-label={`Inscripciones en ${league.name}`}
                                    aria-valuemin={0}
                                    aria-valuemax={league.maxTeams}
                                    aria-valuenow={league.teams}
                                >
                                    <span
                                        style={{
                                            width: `${league.teams / league.maxTeams * 100}%`,
                                        }}
                                    />
                                </div>
                                <Link
                                    to={league.isMember
                                        ? `/leagues/${league.id}/lobby`
                                        : `/leagues/${league.id}/join`}
                                    className="home-panel-link"
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
            </aside>
    )
}