import AvaiableLeagues from './components/AvaiableLeagues';
import './homePage.css';
import AvailableFriendlyMatches from './components/AvailableFriendlyMatches.jsx';
import WelcomePannel from './components/WelcomePannel';

export default function HomePage() {
    return (
        <div className="futbot-home">
            <main className="home-layout">
                <AvaiableLeagues/>
                <WelcomePannel/>
                <AvailableFriendlyMatches/>
            </main>
        </div>
    );
}
