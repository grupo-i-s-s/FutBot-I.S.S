import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.jsx'
import MyClubPage from './features/clubs/MyClubPage.jsx'
import './styles.css'

// Punto de entrada provisional hasta integrar el router de Autenticación.
const RootPage = window.location.pathname.replace(/\/$/, '') === '/club' ? MyClubPage : App

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <RootPage />
  </StrictMode>,
)
