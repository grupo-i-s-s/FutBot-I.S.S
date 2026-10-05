import { Navigate, Route, Routes, useLocation } from 'react-router'
import HomePage from './features/home-page/homePage.jsx'
import LoginPage from './features/login/LoginPage.jsx'
import RegisterPage from './features/register/RegisterPage.jsx'
import MatchesPage from './features/friendly-matches/Matches.jsx'
import MatchPage from './features/friendly-matches/MatchPage.jsx'
import MyClubPage from './features/my-club/MyClubPage.jsx'
import NotFoundPage from './features/not-found/NotFoundPage.jsx'
import CreateFriendlyMatch from './features/friendly-matches/Create_friendly_match.jsx'
import CreatePlayerPage from './features/create-players/CreatePlayersPage.jsx'
import CrearLiga from './features/crear-liga/CreateLeaguePage.jsx'
import CreatePrivateLeague from './features/crear-liga/CreatePrivateLeaguePage.jsx'
import { LeagueLobby } from './features/lobby-league/CreateLeagueLobby.jsx'
import ChangePasswordPage from './features/change-password/ChangePasswordPage.jsx'
import InscripcionLigaPage from './features/inscripcion-liga/InscripcionLigaPage.jsx'
import BehaviourDetailPage from './features/behaviours/BehaviourDetailPage.jsx'
import BehaviourList from './features/behaviours/components/BehaviourList.jsx'
import LeagueListPage from './features/list-leagues/LeagueListPage.jsx'
import NavBar from './features/nav-bar/navBar.jsx'

export default function App() {
    const { pathname } = useLocation()
    const mostrarNavBar = !['/', '/home', '/login', '/registro'].includes(pathname)
    
    return (
         <>
        {mostrarNavBar && <NavBar />}

        <Routes>
            <Route path="/" element={<Navigate to="/login" replace />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/home" element={<HomePage />} />
            <Route path="/registro" element={<RegisterPage />} />
            <Route path="/mi-club" element={<MyClubPage />} />
            <Route path = "/partidos-disponibles" element={<MatchesPage/>}/>
            <Route path = "/crear-partido" element={<CreateFriendlyMatch/>}/>
            <Route path="/crear-jugador" element={<CreatePlayerPage />} />
            <Route path="/partidos/:matchId" element={<MatchPage />} />
            <Route path="/cambiar-contrasena" element={<ChangePasswordPage />} />
            <Route path="/behaviours/:behaviourId" element={<BehaviourDetailPage />} />
            <Route path="/ligas-disponibles" element={<LeagueListPage />} />
            <Route path="/inscripcion-liga" element={<InscripcionLigaPage />} />
            <Route path="/leagues/:id/join" element={<InscripcionLigaPage />} />
            <Route path="/crear-liga" element={<CrearLiga />} />
            <Route path="/crear-liga-privada" element={<CreatePrivateLeague />} />
            <Route path="/leagues/:id/lobby" element={<LeagueLobby />} />
            <Route path="/behaviours" element={<BehaviourList />} />
            <Route path="*" element={<NotFoundPage />} />
        </Routes>
         </>
    )
}
