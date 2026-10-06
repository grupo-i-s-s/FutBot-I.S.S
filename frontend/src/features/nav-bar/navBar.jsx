import {useEffect, useState} from 'react';
import {Link, useLocation} from 'react-router';
import ClubAvatar from '../my-club/components/ClubAvatar';
import {getMyClub} from '../my-club/api';
import '../home-page/homePage.css';

export default function NavBar() {
    const [club, setClub] = useState(null);
    const {pathname} = useLocation();

    useEffect(() => {
        const controller = new AbortController();

        getMyClub({signal: controller.signal})
            .then((data) => {
                if (!controller.signal.aborted) {
                    setClub(data);
                }
            })
            .catch(() => {
                if (!controller.signal.aborted) {
                    setClub(null);
                }
            });

        return () => controller.abort();
    }, [pathname]);

    return (
        <header className="home-nav">
            <Link
                to="/home"
                className="home-brand"
                aria-label="FutBot, inicio"
            >
                <span className="home-brand-icon">
                    {club && (
                        <ClubAvatar
                            avatar={club.avatar}
                            clubName={club.name}
                            size="md"
                        />
                    )}
                </span>

                <div className="home-brand-text">
                    <span>FUTBOT</span>
                    {club && (
                        <span className="home-brand-club">
                            {club.name}
                        </span>
                    )}
                </div>
            </Link>

            <nav className="home-nav-links" aria-label="Cuenta">
                <Link to="/home" className="home-register">
                    Inicio
                </Link>
                <Link to="/mi-club" className="home-register">
                    Mi club
                </Link>
                <Link to="/partidos-disponibles" className="home-register">
                    Amistosos Disponibles
                </Link>
            </nav>
        </header>
    );
}