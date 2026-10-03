import { useState } from 'react'
import { crearLigaPrivada } from './apiPrivate.js'
import { Link } from 'react-router'


export default function CreatePrivateLeague(){
    const [name, setName] = useState('')
    const [minTeams, setMinTeams] = useState(3)
    const [maxTeams, setMaxTeams] = useState('')
    const [startDate, setstartDate] = useState('')
    const [roundInterval, setroundInterval] = useState('CONTINUOUS')
    const [password, setPassword] = useState('')
    const [repeatPassword, setRepeatPassword] = useState('')
    const [isSubmitting, setIsSubmitting] = useState(false)
    const [error, setError] = useState('')
    const [success, setSuccess] = useState('')
    const [needsLogin, setNeedsLogin] = useState(false)

    async function handleSubmit(event) {
        event.preventDefault()
        if (isSubmitting) return
        
        setError('')
        setNeedsLogin(false)
        setSuccess('')

        if(password !== repeatPassword) {
            setError('Las contraseñas no coinciden. Reintentar.')
            return
        }

        setIsSubmitting(true)
        
        try {
            const response = await crearLigaPrivada(
                name,password, minTeams, maxTeams, startDate, roundInterval
            )
            setSuccess(response.message)
        } catch (err) {
            setError(err.message || 'No se pudo crear la liga privada.')
            setNeedsLogin(err.status==401)
        } finally {
            setIsSubmitting(false)
        }
    }
    

    return(
        <main className="login-page">
            <section className="login-card">
                <h1 className="login-title">
                    Crear Liga <br></br> Privada
                </h1>

                <form onSubmit={handleSubmit}>
                    <div className="form-group">
                        <label htmlFor="league-name">
                            Nombre de la liga 
                        </label>

                        <input 
                            id="league-name"
                            type="text"
                            placeholder="Nombre de la liga"
                            value={name}
                            onChange={(event) => setName(event.target.value)}
                            required>
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
                            onChange={(event) => setPassword(event.target.value)}
                            required>
                        </input>
                    </div>

                    <div className = "formulary-box">
                        <label htmlFor="user-password-confirm">Confirmar Contraseña</label>
                        <input  
                            id="user-password-confirm"
                            type="password" 
                            placeholder="Confimar-contraseña" 
                            value = {repeatPassword} 
                            onChange = {(event) => setRepeatPassword(event.target.value)}
                            required>
                        </input>
                    </div>

                    <div className="form-group">
                        <label htmlFor="min-teams">
                            Minimo de clubes
                        </label>

                        <input
                            id="min-teams"
                            type="number"
                            min="3"
                            step="1"
                            value={minTeams}
                            onChange={(event) => setMinTeams(event.target.value)}
                            required>
                        </input>
                    </div>

                    <div className="form-group">
                        <label htmlFor="max-teams">
                            Maximo de clubes
                        </label>

                        <input
                            id="max-teams"
                            type="number"
                            min={minTeams}
                            step="1"
                            value={maxTeams}
                            onChange={(event) => setMaxTeams(event.target.value)}
                            required>
                        </input>
                    </div>

                    <div className="form-group">
                        <label htmlFor="start-date">
                            Fecha y hora de inicio 
                        </label>

                        <input
                            id="start-date"
                            type="datetime-local"
                            value={startDate}
                            onChange={(event) => setstartDate(event.target.value)}
                            required>
                        </input>
                    </div>

                    <div className="form-group">
                        <label htmlFor="round-interval">
                            Frecuencia de rondas
                        </label>

                        <select
                            id = "round-interval"
                            value={roundInterval}
                            onChange={(event) => setroundInterval(event.target.value)}
                            required>
                            <option value="CONTINUOUS">Seguidas</option>    
                            <option value="DAILY">Diarias</option>
                            <option value="WEEKLY">Semanales</option>
                            </select>
                    </div>

                    <button
                        type="submit"
                        className="login-button"
                        disabled={isSubmitting}
                    >
                        {isSubmitting ? 'Creando…' : 'Crear liga'}
                    </button>
                    {error && <p role="alert">{error}</p>}
                    {needsLogin && (
                        <Link to="/login">
                            Iniciar sesión
                        </Link>
                    )}
                    {success && <p role="status">{success}</p>}
                </form>
            </section>
            
        </main>

    )
}
