import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import MyClubPage from '../../src/features/clubs/MyClubPage.jsx'
import '../../src/styles.css'

// Rutas de prueba: no representan pantallas implementadas de los otros módulos.
createRoot(document.getElementById('root')).render(
  <StrictMode>
    <MyClubPage
      loginHref="/test-login"
      destinations={{
        players: '/test-players',
        team: '/test-team',
        behaviours: '/test-behaviours',
        leagues: '/test-leagues',
        friendlyMatches: '/test-friendly-matches',
      }}
    />
  </StrictMode>,
)
