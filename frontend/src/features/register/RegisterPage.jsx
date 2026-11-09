import './RegisterPage.css';
import { useState } from 'react';
import { register } from './api';
import { Link, useLocation, useNavigate } from 'react-router';
import {routes} from '@/routes.js';


export default function RegisterPage() {

    const location = useLocation();
    const [email, setEmail] = useState(location.state?.email ?? '');
    const [password, setPassword] = useState('');
    const [repeatPassword, setRepeatPassword] = useState('');
    const [clubName, setClubName] = useState('');
    const [error, setError] = useState('');
    const [pendingEmail, setPendingEmail] = useState(null);
    const [loading, setLoading] = useState(false);
    const navigate = useNavigate();

    async function handleSubmit(event) {
        event.preventDefault();
        setError('');
        setPendingEmail(null);
        setLoading(true);

        try {
            await register(email, clubName, password, repeatPassword);
            navigate(routes.verifyEmail, { state: { email } });
        } catch (err) {
            if (err.code === 'EMAIL_VERIFICATION_PENDING') setPendingEmail(email);

            const fields = Object.values(err.fields || {});
            setError(
                fields.join(' ') || err.message || 'No se pudo registrar la cuenta.'
            );
        } finally {
            setLoading(false);
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
                            onChange={(event) => {
                                setEmail(event.target.value);
                                if (pendingEmail) {
                                    setPendingEmail(null);
                                    setError('');
                                }
                            }}>
                        </input>
                    </div>

                    <div className="formulary-box">
                        <label htmlFor="user-password">Contraseña</label>
                        <input
                            id="user-password"
                            type="password"
                            placeholder="Contraseña"
                            value={password}
                            onChange={(event) => setPassword(event.target.value)}>
                        </input>
                    </div>

                    <div className="formulary-box">
                        <label htmlFor="user-password-confirm">Confirmar Contraseña</label>
                        <input
                            id="user-password-confirm"
                            type="password"
                            placeholder="Confimar-contraseña"
                            value={repeatPassword}
                            onChange={(event) => setRepeatPassword(event.target.value)}>
                        </input>
                    </div>
                    <button type="submit" className="register-button" disabled={loading}>
                        {loading ? 'Registrando…' : 'Registrar Club'}
                    </button>
                    {error && <p role="alert">{error}</p>}
                    {pendingEmail && (
                        <div className="registration-pending">
                            <p>Los datos de este formulario todavía no se guardaron.</p>
                            <Link to={routes.verifyEmail} state={{email: pendingEmail}}>
                                Continuar con los datos anteriores
                            </Link>
                            <Link to={routes.verifyEmail} state={{email: pendingEmail, editRegistration: true}}>
                                Cambiar los datos con el código
                            </Link>
                        </div>
                    )}
                    <Link to={routes.signIn} className="Registro">Iniciar Sesión</Link>

                </form>
            </section>
        </main>
    );
}
