import { useState } from 'react'
import { crearLiga } from './api.js'


export default function CrearLiga(){
    const [name, setName] = useState('')
    const [minTeams, setMinTeams] = useState(3)
    const [maxTeams, setMaxTeams] = useState('')
    const [startDate, setstartDate] = useState('')
    const [roundInterval, setroundInterval] = useState('CONTINUOUS')
    
    async function handleSubmit(event) {
        event.preventDefault()
        const response = await crearLiga(name, minTeams, maxTeams, startDate, roundInterval)
        console.log(response)
        console.log(response.message)
    }
    

    return(
        <main className="login-page">
            <section className="login-card">
                <h1 className="login-title">
                    Crear Liga <br></br> Pública
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

                    <button type="submit" className="login-button">
                        Crear Liga
                    </button>

                </form>
            </section>
            
        </main>

    )
}
