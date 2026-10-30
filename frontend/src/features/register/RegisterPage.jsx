import './RegisterPage.css';
import {useState} from 'react';
import {register} from './api';
import {Link} from 'react-router';


export default function RegisterPage() {

    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [repeatPassword, setRepeatPassword] = useState('');
    const [avatar, setAvatar] = useState('.');
    const [clubName, setClubName] = useState('');
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');

    async function handleSubmit(event) {
        event.preventDefault();
        setError('');
        setSuccess('');

        try {
            await register(email, clubName, password, repeatPassword, avatar);
            setSuccess('Cuenta registrada. Ya podés iniciar sesión.');
        } catch (err) {
            const fields = Object.values(err.fields || {});
            setError(
                fields.join(' ') || err.message || 'No se pudo registrar la cuenta.'
            );
        }
    }


    return (
        <main className="register-page">
            <h1 className="main-page-title">¡Bienvenido a FutBot!</h1>
            <section className="user_register-card">
                <h1 className="register-title">Registro Usuario</h1>
                <form onSubmit={handleSubmit}>
                    <div className="formulary-box">
                        <label htmlFor="club-name">Nombre del Club</label>
                        <input
                            id="club-name"
                            type="text"
                            placeholder="Nombre del club"
                            value={clubName}
                            onChange={(event) => setClubName(event.target.value)}>
                        </input>
                    </div>

                    <div className="formulary-box">
                        <label htmlFor="user-email">Email</label>
                        <input
                            id="user-email"
                            type="email"
                            placeholder="pepeArgento@gmail.com"
                            value={email}
                            onChange={(event) => setEmail(event.target.value)}>
                        </input>
                    </div>

                    <div className="formulary-box">
                        <label htmlFor="user-password">Contraseña</label>
                        <input
                            id="password"
                            type="password"
                            placeholder="Contraseña"
                            value={password}
                            onChange={(event) => setPassword(event.target.value)}>
                        </input>
                    </div>

                    <div className="formulary-box">
                        <label htmlFor="user-password-confirm">Confirmar Contraseña</label>
                        <input
                            id="password"
                            type="password"
                            placeholder="Confimar-contraseña"
                            value={repeatPassword}
                            onChange={(event) => setRepeatPassword(event.target.value)}>
                        </input>
                    </div>
                    <button type="submit" className="register-button">
                        Registrar Club
                    </button>
                    {error && <p role="alert">{error}</p>}
                    {success && <p role="status">{success}</p>}
                    <Link to="/login" className="Registro">Iniciar Sesión</Link>

                </form>
            </section>
        </main>
    );
}