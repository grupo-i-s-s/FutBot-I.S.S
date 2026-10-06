import {useState} from 'react';
import {crearLiga} from './api.js';
import {useNavigate} from 'react-router';


export default function CrearLiga() {
    const [name, setName] = useState('');
    const [minTeams, setMinTeams] = useState(3);
    const [maxTeams, setMaxTeams] = useState('');
    const [startDateTime, setstartDateTime] = useState('');
    const [roundInterval, setroundInterval] = useState('CONTINUOUS');
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const navigate = useNavigate();

    async function handleSubmit(event) {
        event.preventDefault();
        if (isSubmitting) return;

        setError('');
        setSuccess('');
        setIsSubmitting(true);

        try {
            const response = await crearLiga(name, minTeams, maxTeams, startDateTime, roundInterval);
            navigate('/leagues/' + response.leagueId + '/lobby', {replace: true});
        } catch (err) {
            const fieldErrors = Object.values(err.fields ?? {}).join(' ');
            setError(fieldErrors || err.message || 'No se pudo crear la liga pública.');
        } finally {
            setIsSubmitting(false);
        }
    }


    return (
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
                            value={startDateTime}
                            onChange={(event) => setstartDateTime(event.target.value)}
                            required>
                        </input>
                    </div>

                    <div className="form-group">
                        <label htmlFor="round-interval">
                            Frecuencia de rondas
                        </label>

                        <select
                            id="round-interval"
                            value={roundInterval}
                            onChange={(event) => setroundInterval(event.target.value)}
                            required>
                            <option value="CONTINUOUS">Seguidas</option>
                            <option value="DAILY">Diarias</option>
                            <option value="WEEKLY">Semanales</option>
                        </select>
                    </div>

                    <button type="submit" className="login-button" disabled={isSubmitting}>
                        {isSubmitting ? "Creando..." : "Crear liga"}
                    </button>
                    {error && <p role="alert">{error}</p>}
                    {success && <p role="status">{success}</p>}

                </form>
            </section>

        </main>

    );
}
