import { Navigate, Route, Routes } from 'react-router'
import LoginPage from './features/login/LoginPage.jsx'
import RegisterPage from './features/register/RegisterPage.jsx'
import FriendlyMatches from './features/friendly-matches/Matches.jsx'
import MyClubPage from './features/my-club/MyClubPage.jsx'
import NotFoundPage from './features/not-found/NotFoundPage.jsx'
import CreatePlayerPage from './features/create-players/CreatePlayersPage.jsx'

export default function App() {
    return (
        <Routes>
            <Route path="/" element={<Navigate to="/login" replace />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/registro" element={<RegisterPage />} />
            <Route path="/mi-club" element={<MyClubPage />} />
            <Route path="*" element={<NotFoundPage />} />
            <Route path = "partidos-disponibles" element={<FriendlyMatches/>}/>
            <Route path="/crear-jugador" element={<CreatePlayerPage />} />
        </Routes>
    )
}