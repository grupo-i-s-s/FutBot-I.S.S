import {Link, useLocation} from 'react-router';
import {ArrowRight, Swords} from 'lucide-react';
import '../homePage.css';
import {routes} from '@/routes.js';


export default function AvailableFriendlyMatches() {
    const location = useLocation();
    const availableMatches = {pathname: routes.friendlyMatches, search: location.search, hash: location.hash};


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
            <Link to={availableMatches} className="home-panel-link">
                Ver amistosos disponibles
                <ArrowRight size={17} aria-hidden="true"/>
            </Link>
            <Link to={availableMatches} state={{openCreateMatch: true}} className="home-panel-link">
                Crear Partido Amistoso
                <ArrowRight size={17} aria-hidden="true"/>
            </Link>
        </aside>
    );
}
