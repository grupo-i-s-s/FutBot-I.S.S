import {Link} from 'react-router';
import {ArrowRight, Trophy} from 'lucide-react';
import '../homePage.css';
import {buttonVariants} from '@/components/ui/button';
import {routes} from '@/routes.js';

const linkClassName = buttonVariants({
    variant: 'secondary',
    className: 'home-panel-link h-auto w-full whitespace-normal',
});

export default function AvaiableLeagues() {
    return (
        <aside className="home-panel home-leagues" aria-labelledby="home-leagues-title">
            <div className="home-panel-heading">
                <span className="home-panel-icon">
                    <Trophy size={22} aria-hidden="true"/>
                </span>
                <div>
                    <h2 id="home-leagues-title">Ligas Disponibles</h2>
                </div>
            </div>

            <Link to={routes.leagues} className={linkClassName}>
                Ver todas las ligas
            </Link>

            <Link to={routes.createLeague} className={linkClassName}>
                Crear una liga Publica
                <ArrowRight size={17} aria-hidden="true"/>
            </Link>

            <Link to={routes.createPrivateLeague} className={linkClassName}>
                Crear una liga Privada
                <ArrowRight size={17} aria-hidden="true"/>
            </Link>
        </aside>
    );
}
