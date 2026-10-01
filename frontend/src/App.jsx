import { Navigate, Route, Routes } from 'react-router'
import LoginPage from './features/login/LoginPage.jsx'
import RegisterPage from './features/register/RegisterPage.jsx'
import MyClubPage from './features/my-club/MyClubPage.jsx'
import NotFoundPage from './features/not-found/NotFoundPage.jsx'
import ChangePasswordPage from './features/change-password/ChangePasswordPage.jsx'

export default function App() {
    return (
        <Routes>
            <Route path="/" element={<Navigate to="/login" replace />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/registro" element={<RegisterPage />} />
            <Route path="/mi-club" element={<MyClubPage />} />
            <Route path="/cambiar-contrasena" element={<ChangePasswordPage />} />
            <Route path="*" element={<NotFoundPage />} />
        </Routes>
    )
}