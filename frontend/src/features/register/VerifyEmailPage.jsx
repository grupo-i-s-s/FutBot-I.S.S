import { useState } from 'react';
import { Link, useLocation } from 'react-router';
import { resendVerification, verifyEmail } from './api.js';
import './RegisterPage.css';

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
        <main className="register-page">
            <h1 className="main-page-title">¡Bienvenido a FutBot!</h1>
            <section className="user_register-card">
                <h2 className="register-title">Verificar correo</h2>

                {verified ? (
                    <>
                        <p role="status">{message}</p>
                        <Link to="/login" className="Registro">Iniciar sesión</Link>
                    </>
                ) : (
                    <form onSubmit={handleVerify}>
                        <p>Enviamos un código a <strong>{email}</strong>.</p>

                        <div className="formulary-box">
                            <label htmlFor="verification-code">Código de 6 dígitos</label>
                            <input
                                id="verification-code"
                                type="text"
                                inputMode="numeric"
                                autoComplete="one-time-code"
                                pattern="[0-9]{6}"
                                maxLength={6}
                                value={code}
                                onChange={(event) => setCode(event.target.value.replace(/\D/g, ''))}
                                required
                            />
                        </div>

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

                        {error && <p role="alert">{error}</p>}
                        {message && <p role="status">{message}</p>}
                    </form>
                )}
            </section>
        </main>
    );
}