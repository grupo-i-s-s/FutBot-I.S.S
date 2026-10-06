import { Link } from 'react-router'
import { ArrowRight, Swords } from 'lucide-react'
import '../homePage.css'
import {getFriendlyMatches} from "../api.js";
import {useEffect, useState} from "react";



export default function AvailableFriendlyMatches(){
    const [friendly_matches, setFriendlyMatches] = useState([]);
    const [matchesLoaded, setMatchesLoaded] = useState(false);
    const [error, setError] = useState('');

    useEffect(() => {
        async function cargarPartidos() {
            try {
                const partidos = await getFriendlyMatches();
                setFriendlyMatches(partidos);
                setMatchesLoaded(true);
            } catch (error) {
                setError(error.message);
                console.error('No se pudieron cargar los amistosos:', error);
            }
        }

        cargarPartidos();
    }, []);


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
            {error && <p role="alert">{error}</p>}
            {matchesLoaded && friendly_matches.length === 0 && (
                <p role="status">No hay partidos disponibles.</p>
            )}
            <ul className="home-list">
                {friendly_matches.map((match) => (
                    <li key={match.matchId} className="home-list-card">
                        <div className="home-match-heading">
                            <span className="home-club-avatar" aria-hidden="true">
                                {match.creatorClubName.charAt(0)}
                            </span>
                            <div>
                                <h3>{match.creatorClubName}</h3>
                                <p className="home-item-description">
                                    {new Date(match.startDateTime).toLocaleString('es-AR')}
                                </p>
                            </div>
                        </div>
                    </li>
                ))}
            </ul>
            <Link to="/partidos-disponibles" className="home-panel-link">
                Ver mis amistosos y los disponibles
                <ArrowRight size={17} aria-hidden="true" />
            </Link>
            <Link to="/crear-partido" className="home-panel-link">
                Crear Partido Amistoso
                <ArrowRight size={17} aria-hidden="true" />
            </Link>
        </aside>
    )
}
