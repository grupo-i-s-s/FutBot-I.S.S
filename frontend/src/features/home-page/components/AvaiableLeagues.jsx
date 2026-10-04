import { Link } from 'react-router'
import { Trophy, ArrowRight } from 'lucide-react'
import '../homePage.css'

const EXAMPLE_LEAGUES = [
    { id: 1, name: 'Liga Apertura', teams: 4, maxTeams: 8, type: 'Pública' },
    { id: 2, name: 'Copa FutBot', teams: 5, maxTeams: 8, type: 'Pública' },
    { id: 3, name: 'Liga de los Viernes', teams: 3, maxTeams: 6, type: 'Privada' },
]

export default function AvaiableLeagues(){

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

                    <ul className="home-list">
                        {EXAMPLE_LEAGUES.map((league) => (
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
                            </li>
                        ))}
                    </ul>

                    <Link to="/crear-liga" className="home-panel-link">
                        Crear una liga
                        <ArrowRight size={17} aria-hidden="true" />
                    </Link>

                    <Link to="/crear-liga-privada" className="home-secondary-link">
                        Prefiero una liga privada
                    </Link>
            </aside>
    )
}