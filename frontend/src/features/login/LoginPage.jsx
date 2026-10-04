import { useState } from 'react'
import { login } from './api'
import './LoginPage.css'
import { Link, useNavigate } from 'react-router'

export default function LoginPage(){
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [error, setError] = useState('')
    const navigate = useNavigate()
    
    async function handleSubmit(event) {
    event.preventDefault()
    setError('')

    try {
        await login(email, password)
        navigate('/crear-liga')
    } catch (err) {
        const fieldErrors = Object.values(err.fields ?? {}).join(' ')

        setError(fieldErrors || err.message || 'No se pudo iniciar sesión.')
    }
}

    return(
        <main className="login-page">
            <section className="login-card">
                <h1 className="login-title">
                    Inicio de Sesión<br></br>FutBot
                </h1>

                <form onSubmit={handleSubmit}>
                    <div className="form-group">
                        <label htmlFor="email">
                            Email
                        </label>

                        <input 
                            id="email"
                            type="email"
                            placeholder="nombre@gmail.com"
                            value={email}
                            onChange={(event) => setEmail(event.target.value)}>
                        </input>
                    </div>

                    <div className="form-group">
                        <label htmlFor="password">
                            Contraseña
                        </label>

                        <input
                            id="password"
                            type="password"
                            placeholder="Ingrese su contraseña"
                            value={password}
                            onChange={(event) => setPassword(event.target.value)}>
                        </input>
                    </div>

                    <button type="submit" className="login-button">
                        Iniciar Sesión
                    </button>
                    {error && <p role="alert">{error}</p>}
                    <Link to="/registro" className="Registro">Registrarme</Link>
                </form>
            </section>
            
        </main>

    )
}
