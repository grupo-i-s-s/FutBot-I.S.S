import './CreatePlayersPage.css';
import {useState} from 'react';
import {createPlayer} from './api';
import {useNavigate} from 'react-router';

export default function CreatePlayerPage() {
    const [name, setName] = useState('');
    const [power, setPower] = useState(60);
    const [agility, setAgility] = useState(60);
    const [control, setControl] = useState(60);
    const [speed, setSpeed] = useState(60);
    const [strength, setStrength] = useState(60);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const navigate = useNavigate();

    const totalPoints = power + agility + control + speed + strength;

    const isValid = name.trim() !== '' && totalPoints === 300;

    async function handleSubmit(event) {
        event.preventDefault();
        if (isSubmitting) return;

        setError('');
        setSuccess('');

        if (!isValid) {
            setError(
                !name.trim()
                    ? 'Ingresá el nombre del jugador.'
                    : `Los atributos deben sumar 300 puntos. Actualmente suman ${totalPoints}.`
            );
            return;
        }

        setIsSubmitting(true);

        try {
            const player = await createPlayer(
                name.trim(),
                power,
                agility,
                control,
                speed,
                strength
            );

            setSuccess(`¡El jugador ${player.name} se creó correctamente!`);
            navigate('/mi-club', {replace: true});
        } catch (err) {
            if (err.status === 401) {
                setError('Tu sesión venció. Iniciá sesión nuevamente.');
            } else {
                const fieldErrors = Object.values(err.fields ?? {}).join(' ');

                setError(
                    fieldErrors ||
                    err.message ||
                    'No se pudo crear el jugador. Intentá nuevamente.'
                );
            }
        } finally {
            setIsSubmitting(false);
        }
    }

    return (
        <main className="create-players-page">
            <h1 className="main-page-title">Crear Jugador</h1>
            <section className="name-card">
                <form onSubmit={handleSubmit}>
                    <div className="formulary-box">
                        <input
                            id="user-name"
                            type="text"
                            placeholder="Nombre"
                            value={name}
                            onChange={(event) => setName(event.target.value)}/>
                    </div>

                    <div className="attribute-header">
                        <label htmlFor="power-range">Potencia</label>
                        <span className="attribute-value">{power}</span>
                    </div>
                    <input
                        id="power"
                        className="slider"
                        type="range"
                        min="20"
                        max="100"
                        value={power}
                        onChange={(event) => setPower(Number(event.target.value))}/>

                    <div className="attribute-header">
                        <label htmlFor="power-range">Agilidad</label>
                        <span className="attribute-value">{agility}</span>
                    </div>
                    <input
                        id="agility"
                        className="slider"
                        type="range"
                        min="20"
                        max="100"
                        value={agility}
                        onChange={(event) => setAgility(Number(event.target.value))}/>

                    <div className="attribute-header">
                        <label htmlFor="power-range">Control</label>
                        <span className="attribute-value">{control}</span>
                    </div>
                    <input
                        id="control"
                        className="slider"
                        type="range"
                        min="20"
                        max="100"
                        value={control}
                        onChange={(event) => setControl(Number(event.target.value))}/>

                    <div className="attribute-header">
                        <label htmlFor="power-range">Velocidad</label>
                        <span className="attribute-value">{speed}</span>
                    </div>
                    <input
                        id="speed"
                        className="slider"
                        type="range"
                        min="20"
                        max="100"
                        value={speed}
                        onChange={(event) => setSpeed(Number(event.target.value))}/>

                    <div className="attribute-header">
                        <label htmlFor="power-range">Fuerza</label>
                        <span className="attribute-value">{strength}</span>
                    </div>
                    <input
                        id="strength"
                        className="slider"
                        type="range"
                        min="20"
                        max="100"
                        value={strength}
                        onChange={(event) => setStrength(Number(event.target.value))}/>

                    <div className="total-box">
                        <span className="total-label">Puntos Totales:</span>
                        <span className="total-value">{totalPoints}</span>
                    </div>

                    <button
                        type="submit"
                        className="login-button"
                        disabled={isSubmitting}
                    >
                        {isSubmitting ? 'Creando…' : 'Crear jugador'}
                    </button>

                    {error && (
                        <p role="alert">
                            {error}
                        </p>
                    )}

                    {success && (
                        <p role="status">
                            {success}
                        </p>
                    )}
                </form>
            </section>
        </main>
    );
}