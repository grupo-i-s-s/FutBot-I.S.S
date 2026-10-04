import { Navigate, Route, Routes } from 'react-router'
import LoginPage from './features/login/LoginPage.jsx'
import RegisterPage from './features/register/RegisterPage.jsx'
import FriendlyMatches from './features/friendly-matches/Matches.jsx'
import MyClubPage from './features/my-club/MyClubPage.jsx'
import NotFoundPage from './features/not-found/NotFoundPage.jsx'
import CreateFriendlyMatch from './features/friendly-matches/Create_friendly_match.jsx'

export default function App() {
    return (
        <Routes>
            <Route path="/" element={<Navigate to="/login" replace />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/registro" element={<RegisterPage />} />
            <Route path="/mi-club" element={<MyClubPage />} />
            <Route path = "/partidos-disponibles" element={<FriendlyMatches/>}/>
            <Route path = "/crear-partido" element={<CreateFriendlyMatch/>}/>
            <Route path="*" element={<NotFoundPage />} />
        </Routes>
    )
}