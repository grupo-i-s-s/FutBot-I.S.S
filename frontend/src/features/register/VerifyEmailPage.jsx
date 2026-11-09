import { useState } from 'react';
import { Link, useLocation } from 'react-router';
import { resendVerification, verifyEmail } from './api.js';
import './VerifyEmailPage.css';
import {routes} from '@/routes.js';

export default function VerifyEmailPage() {
    const location = useLocation();
    const email = location.state?.email ?? '';
    const [code, setCode] = useState('');
    const [error, setError] = useState('');
    const [message, setMessage] = useState('');
    const [loading, setLoading] = useState(false);
    const [verified, setVerified] = useState(false);
    const [editingRegistration, setEditingRegistration] = useState(location.state?.editRegistration === true);
    const [clubName, setClubName] = useState('');
    const [password, setPassword] = useState('');
    const [passwordConfirmation, setPasswordConfirmation] = useState('');

    async function handleVerify(event) {
        event.preventDefault();
        setError('');
        setMessage('');
        setLoading(true);

        try {
            let registration;
            if (editingRegistration && (clubName.trim() || password || passwordConfirmation)) {
                registration = {
                    clubName: clubName.trim() || undefined,
                    password: password || undefined,
                    passwordConfirmation: passwordConfirmation || undefined,
                };
            }
            await verifyEmail(email, code, registration);
            setVerified(true);
            setMessage('¡Correo verificado! Ya podés iniciar sesión.');
        } catch (err) {
            const fieldErrors = Object.values(err.fields ?? {}).join(' ');
            setError(fieldErrors || err.message || 'No se pudo verificar el correo.');
            if (err.code === 'ACCOUNT_DUPLICATE' && err.fields?.clubName) {
                setEditingRegistration(true);
            }
        } finally {
            setLoading(false);
        }
    }

    async function handleResend() {
        setError('');
        setMessage('');
        setLoading(true);

        try {
            const result = await resendVerification(email);
            setMessage(result?.message || 'Si hay una verificación pendiente, se enviará un nuevo código.');
        } catch (err) {
            setError(err.message || 'No se pudo reenviar el código.');
        } finally {
            setLoading(false);
        }
    }

    return (
        <main className="verify-email-page">
            <div className="verify-email-page__content">
                <h1 className="verify-email-page__brand">¡Bienvenido a FutBot!</h1>
                <section className="verify-email-card">

                    {verified ? (
                        <>
                            <p role="status">{message}</p>
                            <Link to={routes.signIn} className="verify-email-card__login">Ir a iniciar sesión</Link>
                        </>
                    ) : (
                        <form onSubmit={handleVerify}>
                            <h2> Verificación </h2>
                            <p>Se ha enviado un código de 6 digitos a la cuenta <strong>{email}</strong>, revisa la sección recibidos y la carpeta de spam.</p>
                            <div className="formulary-box">
                                <input
                                    id="verification-code"
                                    type="text"
                                    inputMode="numeric"
                                    autoComplete="one-time-code"
                                    pattern="[0-9]{6}"
                                    maxLength={6}
                                    value={code}
                                    placeholder="Ingrese el código"
                                    aria-label="Código de verificación"
                                    onChange={(event) => setCode(event.target.value.replace(/\D/g, ''))}
                                    required
                                />
                            </div>
                            {editingRegistration && (
                                <fieldset className="verification-corrections" disabled={loading}>
                                    <legend>Cambiar datos del registro</legend>
                                    <p>Completá solo los datos que quieras cambiar y usá el código que recibiste.</p>
                                    <div className="formulary-box">
                                        <label htmlFor="corrected-club-name">Nuevo nombre del club</label>
                                        <input
                                            id="corrected-club-name"
                                            maxLength={50}
                                            value={clubName}
                                            onChange={(event) => setClubName(event.target.value)}
                                        />
                                    </div>
                                    <div className="formulary-box">
                                        <label htmlFor="corrected-password">Nueva contraseña</label>
                                        <input
                                            id="corrected-password"
                                            type="password"
                                            autoComplete="new-password"
                                            minLength={8}
                                            maxLength={128}
                                            value={password}
                                            onChange={(event) => setPassword(event.target.value)}
                                        />
                                    </div>
                                    <div className="formulary-box">
                                        <label htmlFor="corrected-password-confirmation">Confirmar nueva contraseña</label>
                                        <input
                                            id="corrected-password-confirmation"
                                            type="password"
                                            autoComplete="new-password"
                                            minLength={8}
                                            maxLength={128}
                                            value={passwordConfirmation}
                                            onChange={(event) => setPasswordConfirmation(event.target.value)}
                                        />
                                    </div>
                                </fieldset>
                            )}
                            <div className="formulary-buttons">
                                <button className="register-button" type="submit" disabled={loading || !email}>
                                    {loading ? 'Verificando…' : 'Verificar correo'}
                                </button>

                                <button
                                    className="register-button"
                                    type="button"
                                    onClick={handleResend}
                                    disabled={loading || !email}
                                >
                                    Reenviar código
                                </button>
                            </div>


                            {error && <p role="alert">{error}</p>}
                            {message && <p role="status">{message}</p>}
                            <p className="verify-email-card__register">
                                {email && (
                                    <button
                                        type="button"
                                        className="verification-corrections-toggle"
                                        disabled={loading}
                                        onClick={() => setEditingRegistration(!editingRegistration)}
                                    >
                                        {editingRegistration ? 'Usar los datos anteriores' : 'Cambiar datos del registro'}
                                    </button>
                                )}
                                <Link to={routes.register} state={{email}}>Volver al registro</Link>
                            </p>
                        </form>
                    )}
                </section>
            </div>
        </main>
    );
}
