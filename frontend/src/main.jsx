import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import Login from './features/login/LoginPage.jsx'
import './styles.css'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <Login />
  </StrictMode>,
)
