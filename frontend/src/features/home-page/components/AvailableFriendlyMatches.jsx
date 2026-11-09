import {Link, useLocation} from 'react-router';
import {ArrowRight, Swords} from 'lucide-react';
import {Button} from '@/components/ui/button';
import {useFriendlyMatches} from '../../friendly-matches/hooks/useFriendlyMatches.js';
import FriendlyMatchSearch from '../../friendly-matches/components/FriendlyMatchSearch.jsx';
import '../homePage.css';
import {routes} from '@/routes.js';


export default function AvailableFriendlyMatches() {
    const search = useFriendlyMatches();
    const location = useLocation();


    return (
        <aside className="home-panel home-matches" aria-labelledby="home-matches-title">
            <div className="home-panel-heading">
                <span className="home-panel-icon home-match-icon">
                    <Swords size={22} aria-hidden="true"/>
                </span>
                <div>
                    <h2 id="home-matches-title">Amistosos disponibles</h2>
                </div>
            </div>
            <Link to={{pathname: routes.friendlyMatches, search: location.search, hash: location.hash}} className="home-panel-link">
                Ver mis amistosos y los disponibles
                <ArrowRight size={17} aria-hidden="true"/>
            </Link>
            <Link to={routes.createMatch} className="home-panel-link">
                Crear Partido Amistoso
                <ArrowRight size={17} aria-hidden="true"/>
            </Link>
            <FriendlyMatchSearch search={search}/>
            {search.loading && <p role="status">Buscando amistosos…</p>}
            {search.error && <p role="alert">{search.error}
                <Button variant="outline" onClick={search.reload}>Reintentar búsqueda</Button>
            </p>}
            {!search.loading && !search.error && search.result.items.length === 0 && (
                <p role="status">{search.result.total > 0 ? 'No hay partidos en esta página.'
                    : search.creatorName ? `No se encontraron amistosos para "${search.creatorName}".`
                        : 'No hay partidos disponibles.'}</p>
            )}
            <ul className="home-list" tabIndex={0} aria-label="Resultados de amistosos">
                {!search.loading && !search.error && search.result.items.map((match) => (
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
        </aside>
    );
}
