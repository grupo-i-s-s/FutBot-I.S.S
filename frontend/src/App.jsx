import { Navigate, Route, Routes } from 'react-router'
import LoginPage from './features/login/LoginPage.jsx'
import RegisterPage from './features/register/RegisterPage.jsx'
import FriendlyMatches from './features/friendly-matches/Matches.jsx'
import MyClubPage from './features/my-club/MyClubPage.jsx'
import NotFoundPage from './features/not-found/NotFoundPage.jsx'
import CreatePlayerPage from './features/create-players/CreatePlayersPage.jsx'
import CrearLiga from './features/crear-liga/CreateLeaguePage.jsx'
import CreatePrivateLeague from './features/crear-liga/CreatePrivateLeaguePage.jsx'
import ChangePasswordPage from './features/change-password/ChangePasswordPage.jsx'
import LeagueListPage from './features/list-leagues/LeagueListPage.jsx'

export default function App() {
    return (
        <Routes>
            <Route path="/" element={<Navigate to="/login" replace />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/registro" element={<RegisterPage />} />
            <Route path="/mi-club" element={<MyClubPage />} />
            <Route path="/crear-jugador" element={<CreatePlayerPage />} />
            <Route path = "partidos-disponibles" element={<FriendlyMatches/>}/>
            <Route path="/cambiar-contrasena" element={<ChangePasswordPage />} />
            <Route path="/ligas-disponibles" element={<LeagueListPage />} />
            <Route path="*" element={<NotFoundPage />} />
            <Route path="/crear-liga" element={<CrearLiga />} />
            <Route path="/crear-liga-privada" element={<CreatePrivateLeague />} />
        </Routes>
    )
}