import {ArrowRight} from 'lucide-react';
import {Link} from 'react-router';
import '../homePage.css';
import {routes} from '@/routes.js';

export default function WelcomePannel() {
    return (
        <section className="home-welcome" aria-labelledby="home-title">
            <h1 id="home-title">
                <span className="home-greeting"> Bienvenidos a</span>
                <span className="home-title">FutBot<span>.</span></span>
            </h1>
            <p className="home-club"> Arma tu equipo</p>
            <Link to={routes.myClub} className="home-teams">
                Ir a mi Club
                <ArrowRight size={20} aria-hidden="true"/>
            </Link>
        </section>
    );
}