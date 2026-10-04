import { Link } from 'react-router'
import { Shield } from 'lucide-react'
import AvaiableLeagues from './components/AvaiableLeagues'
import './homePage.css'
import AvaiableFriendlyMatches from './components/AvaiableFriendlyMatches'
import WelcomePannel from './components/WelcomePannel'
import { useEffect, useState } from 'react'
import { getMyClub } from '../my-club/api'
import ClubAvatar from '../my-club/components/ClubAvatar'

export default function HomePage(){
    
    const [club, setClub] = useState(null)

    useEffect(() => {
        const controller = new AbortController()

        getMyClub({ signal: controller.signal })
            .then((data) => {
                if (!controller.signal.aborted) setClub(data)
            })
            .catch(() => {
                // Si no se pudo cargar, el avatar queda vacío.
            })

        return () => controller.abort()
    }, [])
    
    return(
        <div className='futbot-home'>
            <header className="home-nav">
                <Link to="/home" className="home-brand" aria-label="FutBot, inicio">
                        <span className="home-brand-icon">
                            {club && ( <ClubAvatar avatar={club.avatar} size="md"/>)}
                        </span>
                    <div className="home-brand-text">
                        <span>FUTBOT</span>
                        {club && (<span className="home-brand-club">{club.name}</span>)}
                    </div>
                </Link>

                <nav className="home-nav-links" aria-label="Cuenta">
                    <Link to="/login" className="home-login">
                        Iniciar sesión
                    </Link>
                    <Link to="/registro" className="home-register">
                        Crear cuenta
                    </Link>
                </nav>
            </header>
            <main className="home-layout">
                <AvaiableLeagues />
                <WelcomePannel />
                <AvaiableFriendlyMatches />
            </main>
        </div>
            
    )
}