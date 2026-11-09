import { useState } from 'react';
import { Link, useLocation } from 'react-router';
import { resendVerification, verifyEmail } from './api.js';
import './VerifyEmailPage.css';
import {routes} from '@/routes.js';

export default function VerifyEmailPage() {
    const location = useLocation();
    const [email, setEmail] = useState(location.state?.email ?? '');
    const [code, setCode] = useState('');
    const [error, setError] = useState('');
    const [message, setMessage] = useState('');
    const [loading, setLoading] = useState(false);
    const [verified, setVerified] = useState(false);

    async function handleVerify(event) {
        event.preventDefault();
        setError('');
        setMessage('');
        setLoading(true);

        try {
            await verifyEmail(email, code);
            setVerified(true);
            setMessage('¡Correo verificado! Ya podés iniciar sesión.');
        } catch (err) {
            const fieldErrors = Object.values(err.fields ?? {}).join(' ');
            setError(fieldErrors || err.message || 'No se pudo verificar el correo.');
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
                                    onChange={(event) => setCode(event.target.value.replace(/\D/g, ''))}
                                    required
                                />
                            </div>
                            <div className="formulary-buttons">
                                <button className="register-button" type="submit" disabled={loading}>
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
                                <Link to="/registro">Volver al registro</Link>
                            </p>
                        </form>
                    )}
                </section>
            </div>
        </main>
    );
}