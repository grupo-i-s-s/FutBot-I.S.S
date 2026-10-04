import { Link } from 'react-router'
import { Shield } from 'lucide-react'
import AvaiableLeagues from './components/AvaiableLeagues'
import './homePage.css'
import AvaiableFriendlyMatches from './components/AvaiableFriendlyMatches'
import WelcomePannel from './components/WelcomePannel'

export default function HomePage(){

    return(
        <div className='futbot-home'>
            <header className="home-nav">
                <Link to="/home" className="home-brand" aria-label="FutBot, inicio">
                    <span className="home-brand-icon">
                        <Shield size={22} aria-hidden="true" />
                    </span>
                    FUTBOT
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