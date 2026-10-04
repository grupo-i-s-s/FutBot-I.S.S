import { Link } from 'react-router'
import { ArrowRight, Swords } from 'lucide-react'
import '../homePage.css'

const EXAMPLE_MATCHES = [
    { id: 1, club: 'Los Pibes FC', day: 'Sábado', time: '20:30' },
    { id: 2, club: 'Club Horizonte', day: 'Domingo', time: '18:00' },
    { id: 3, club: 'Atlético Bot', day: 'Domingo', time: '21:00' },
]

export default function AvaiableFriendlyMatches(){

    return(
        <aside className="home-panel home-matches" aria-labelledby="home-matches-title">           
        <div className="home-panel-heading">
                <span className="home-panel-icon home-match-icon">
                    <Swords size={22} aria-hidden="true" />
                </span>
                <div>
                    <h2 id="home-matches-title">Amistosos disponibles</h2>
                </div>
            </div>
            <ul className="home-list">
                {EXAMPLE_MATCHES.map((match) => (
                    <li key={match.id} className="home-list-card">
                        <div className="home-match-heading">
                            <span className="home-club-avatar" aria-hidden="true">
                                {match.club.charAt(0)}
                            </span>
                            <div>
                                <h3>{match.club}</h3>
                                <p className="home-item-description">
                                    {match.day} · {match.time}
                                </p>
                            </div>
                        </div>
                    </li>
                ))}
            </ul>
            <Link to="/partidos-disponibles" className="home-panel-link">
                Ver amistosos
                <ArrowRight size={17} aria-hidden="true" />
            </Link>
        </aside>
    )
}