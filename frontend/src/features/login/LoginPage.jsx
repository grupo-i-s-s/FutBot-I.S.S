import { useState } from 'react'
import { login } from './api'
import './LoginPage.css'

export default function LoginPage(){
    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')

    async function handleSubmit(event) {
        event.preventDefault()
        const response = await login(email, password)
        console.log(response)
        console.log(response.status)
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
                </form>
                <p>Email escrito: {email}</p>
                <p>Password escrito: {password}</p>
            </section>
            
        </main>

    )
}