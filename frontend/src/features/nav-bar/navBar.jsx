import {useState} from 'react';
import {NavLink, useNavigate} from 'react-router';
import ClubAvatar from '../my-club/components/ClubAvatar';
import {useSession} from '../session/SessionProvider.jsx';
import './navBar.css';
import {routes} from '@/routes.js';

function ClubNavigation({signOut}) {
    const navigate = useNavigate();
    const [signingOut, setSigningOut] = useState(false);
    const [error, setError] = useState('');

    async function handleSignOut() {
        setSigningOut(true);
        setError('');
        try {
            if (await signOut()) navigate(routes.root, {replace: true});
        } catch (requestError) {
            setError(requestError.message || 'No se pudo cerrar la sesión.');
        } finally {
            setSigningOut(false);
        }
    }

    return <>
        <nav className="app-nav-links" aria-label="Navegación principal">
            <NavLink to={routes.home} className="app-nav-action">Inicio</NavLink>
            <NavLink to={routes.myClub} className="app-nav-action">Mi club</NavLink>
            <NavLink to={routes.friendlyMatches} className="app-nav-action">Amistosos</NavLink>
            <NavLink to={routes.leagues} className="app-nav-action">Ligas</NavLink>
            <NavLink to={routes.clubs} className="app-nav-action">Clubes</NavLink>
            <NavLink to={routes.globalRanking} className="app-nav-action">Ranking global</NavLink>
            <button type="button" className="app-nav-action" onClick={handleSignOut} disabled={signingOut}>
                {signingOut ? 'Cerrando sesión…' : 'Cerrar sesión'}
            </button>
        </nav>
        {error && <p className="app-nav-error" role="alert">{error}</p>}
    </>;
}

export default function NavBar() {
    const {status, club, signOut} = useSession();
    const authenticated = status === 'authenticated';
    const showPublicLinks = status === 'anonymous' || status === 'error';

    return (
        <header className="app-nav">
            <div className="app-nav-inner">
                {authenticated && <>
                    <div className="app-nav-club">
                        <ClubAvatar avatar={club.avatar} clubName={club.name} size="md" />
                        <span title={club.name}>{club.name}</span>
                    </div>
                    <ClubNavigation signOut={signOut} />
                </>}

                {showPublicLinks && (
                    <nav className="app-nav-links" aria-label="Cuenta">
                        <NavLink to={routes.root} className="app-nav-action" end>Iniciar sesión</NavLink>
                        <NavLink to={routes.register} className="app-nav-action">Registrarse</NavLink>
                    </nav>
                )}
            </div>
        </header>
    );
}
