import {useEffect, useState} from 'react';
import {Link} from 'react-router';
import {requestPasswordReset, confirmPasswordReset} from './api.js';
import '../login/LoginPage.css';

export default function PasswordResetPage() {
    const [email, setEmail] = useState('');
    const [code, setCode] = useState('');
    const [newPassword, setNewPassword] = useState('');
    const [confirmation, setConfirmation] = useState('');
    const [step, setStep] = useState('email');
    const [loading, setLoading] = useState(false);
    const [seconds, setSeconds] = useState(0);
    const [error, setError] = useState('');
    const [message, setMessage] = useState('');

    const passwordsDiffer = confirmation !== '' && newPassword !== confirmation;

    useEffect(() => {
        if (seconds <= 0) return;

        const timer = setTimeout(() => setSeconds(seconds - 1), 1000);
        return () => clearTimeout(timer);
    }, [seconds]);

    async function handleRequest() {
        if (loading || seconds > 0) return;

        setLoading(true);
        setError('');
        setMessage('');

        try {
            await requestPasswordReset(email.trim());
            setStep('confirm');
            setSeconds(60);
            setMessage(
                'Si la cuenta existe, recibirás un código para recuperar la contraseña.',
            );
        } catch (err) {
            if (err.status === 429) {
                setSeconds(Math.max(1, Number(err.retryAfter) || 60));
            }
            setError(err.message || 'No se pudo solicitar el código.');
        } finally {
            setLoading(false);
        }
    }

    async function handleSubmit(event) {
        event.preventDefault();
        if (loading || !event.currentTarget.reportValidity()) return;

        if (step === 'email') {
            await handleRequest();
            return;
        }

        if (newPassword !== confirmation) return;

        setLoading(true);
        setError('');
        setMessage('');

        try {
            await confirmPasswordReset(
                email.trim(), code, newPassword, confirmation,
            );
            setCode('');
            setNewPassword('');
            setConfirmation('');
            setEmail('');
            setSeconds(0);
            setStep('done');
        } catch (err) {
            setError(err.message || 'No se pudo restablecer la contraseña.');
        } finally {
            setLoading(false);
        }
    }

    return (
        <main className="login-page">
            <section className="login-card">
                <h1 className="login-title">Recuperar contraseña</h1>

                {step === 'done' ? (
                    <p role="status">
                        Contraseña actualizada. Ya podés iniciar sesión
                        con tu nueva contraseña.
                    </p>
                ) : (
                    <form onSubmit={handleSubmit}>
                        <fieldset disabled={loading}>
                            <div className="form-group">
                                <label htmlFor="reset-email">Email</label>
                                <input
                                    id="reset-email"
                                    type="email"
                                    autoComplete="email"
                                    maxLength={254}
                                    value={email}
                                    onChange={(event) => setEmail(event.target.value)}
                                    readOnly={step === 'confirm'}
                                    required
                                />
                            </div>

                            {step === 'confirm' && (
                                <>
                                    <div className="form-group">
                                        <label htmlFor="reset-code">
                                            Código de recuperación
                                        </label>
                                        <input
                                            id="reset-code"
                                            type="text"
                                            inputMode="numeric"
                                            autoComplete="one-time-code"
                                            pattern="[0-9]{6}"
                                            maxLength={6}
                                            value={code}
                                            onChange={(event) => setCode(event.target.value)}
                                            required
                                        />
                                    </div>

                                    <div className="form-group">
                                        <label htmlFor="reset-password">
                                            Nueva contraseña
                                        </label>
                                        <input
                                            id="reset-password"
                                            type="password"
                                            autoComplete="new-password"
                                            minLength={8}
                                            maxLength={128}
                                            value={newPassword}
                                            onChange={(event) => setNewPassword(event.target.value)}
                                            required
                                        />
                                    </div>

                                    <div className="form-group">
                                        <label htmlFor="reset-confirmation">
                                            Repetir nueva contraseña
                                        </label>
                                        <input
                                            id="reset-confirmation"
                                            type="password"
                                            autoComplete="new-password"
                                            minLength={8}
                                            maxLength={128}
                                            value={confirmation}
                                            onChange={(event) => setConfirmation(event.target.value)}
                                            aria-invalid={passwordsDiffer}
                                            aria-describedby={passwordsDiffer ? 'password-mismatch' : undefined}
                                            required
                                        />
                                        {passwordsDiffer && (
                                            <p id="password-mismatch" role="alert">
                                                Las contraseñas no coinciden.
                                            </p>
                                        )}
                                    </div>
                                </>
                            )}

                            <button
                                type="submit"
                                className="login-button"
                                disabled={
                                    loading
                                    || (step === 'email' && seconds > 0)
                                }
                            >
                                {loading
                                    ? 'Procesando...'
                                    : step === 'email'
                                        ? 'Solicitar código'
                                        : 'Restablecer contraseña'}
                            </button>

                            {step === 'confirm' && (
                                <button
                                    type="button"
                                    className="login-button"
                                    onClick={handleRequest}
                                    disabled={loading || seconds > 0}
                                >
                                    Reenviar código
                                </button>
                            )}
                        </fieldset>

                        {seconds > 0 && (
                            <p role="status">
                                Podés solicitar otro código en {seconds} segundos.
                            </p>
                        )}
                        {message && <p role="status">{message}</p>}
                        {error && <p role="alert">{error}</p>}
                    </form>
                )}

                <Link to="/login" className="Registro">
                    Volver al login
                </Link>
            </section>
        </main>
    );
}