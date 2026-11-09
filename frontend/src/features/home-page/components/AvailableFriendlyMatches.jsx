import {Link, useLocation} from 'react-router';
import {ArrowRight, Swords} from 'lucide-react';
import {Button} from '@/components/ui/button';
import {useFriendlyMatches} from '../../friendly-matches/hooks/useFriendlyMatches.js';
import {FriendlyMatchPagination} from '../../friendly-matches/components/FriendlyMatchSearch.jsx';
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
                Ver amistosos disponibles
                <ArrowRight size={17} aria-hidden="true"/>
            </Link>
            <Link to={routes.createMatch} className="home-panel-link">
                Crear Partido Amistoso
                <ArrowRight size={17} aria-hidden="true"/>
            </Link>
            {search.loading && <p role="status">Buscando amistosos…</p>}
            {search.error && <p role="alert">{search.error}
                <Button variant="outline" onClick={search.reload}>Reintentar búsqueda</Button>
            </p>}
            {!search.loading && !search.error && search.result.items.length > 0 && (
                <ul className="home-list" tabIndex={0} aria-label="Resultados de amistosos">
                    {search.result.items.map((match) => (
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
            )}
            {!search.error && search.result.total > 0 && (
                <div className="mt-3"><FriendlyMatchPagination search={search}/></div>
            )}
        </aside>
    );
}
