import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
//import Login from './features/login/LoginPage.jsx'
import RegisterPage from './features/register/RegisterPage.jsx'
import './styles.css'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    {/*<Login />*/}
    <RegisterPage />
  </StrictMode>,
)
