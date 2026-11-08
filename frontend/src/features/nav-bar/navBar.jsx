import {Goal} from 'lucide-react';
import {useState} from 'react';
import {Link, NavLink, useNavigate} from 'react-router';
import ClubAvatar from '../my-club/components/ClubAvatar';
import {useSession} from '../session/SessionProvider.jsx';
import './navBar.css';

function ClubNavigation({signOut}) {
    const navigate = useNavigate();
    const [signingOut, setSigningOut] = useState(false);
    const [error, setError] = useState('');

    async function handleSignOut() {
        setSigningOut(true);
        setError('');
        try {
            await signOut();
            navigate('/', {replace: true});
        } catch (requestError) {
            setError(requestError.message || 'No se pudo cerrar la sesión.');
        } finally {
            setSigningOut(false);
        }
    }

    return <>
        <nav className="app-nav-links" aria-label="Navegación principal">
            <NavLink to="/mi-club" className="app-nav-action">Mi club</NavLink>
            <NavLink to="/partidos-disponibles" className="app-nav-action">Amistosos</NavLink>
            <NavLink to="/ligas-disponibles" className="app-nav-action">Ligas</NavLink>
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
                <Link to={authenticated ? '/home' : '/'} className="app-nav-brand" aria-label="FutBot, inicio">
                    <Goal size={24} aria-hidden="true" />
                    <span>FUTBOT</span>
                </Link>

                {authenticated && <>
                    <div className="app-nav-club">
                        <ClubAvatar avatar={club.avatar} clubName={club.name} size="md" />
                        <span>{club.name}</span>
                    </div>
                    <ClubNavigation signOut={signOut} />
                </>}

                {showPublicLinks && (
                    <nav className="app-nav-links" aria-label="Cuenta">
                        <NavLink to="/" className="app-nav-action" end>Iniciar sesión</NavLink>
                        <NavLink to="/registro" className="app-nav-action">Registrarse</NavLink>
                    </nav>
                )}
            </div>
        </header>
    );
}
