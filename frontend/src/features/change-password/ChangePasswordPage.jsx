import {useState} from 'react';
import {useNavigate} from 'react-router';
import {changePassword} from './api';
import '../login/LoginPage.css';

export default function ChangePasswordPage() {
    const navigate = useNavigate();
    const [oldPassword, setOldPassword] = useState('');
    const [newPassword, setNewPassword] = useState('');
    const [confirmation, setConfirmation] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);

    async function handleSubmit(event) {
        event.preventDefault();
        setError('');

        if (newPassword !== confirmation) {
            setError('Las contraseñas nuevas no coinciden.');
            return;
        }

        setLoading(true);
        try {
            await changePassword(oldPassword, newPassword);
            navigate('/login', {replace: true});
        } catch (requestError) {
            setError(requestError.message);
        } finally {
            setLoading(false);
        }
    }

    return (
        <main className="login-page">
            <section className="login-card">
                <h1 className="login-title">Cambiar contraseña</h1>

                <form onSubmit={handleSubmit}>
                    <div className="form-group">
                        <label htmlFor="old-password">Contraseña actual</label>
                        <input
                            id="old-password"
                            type="password"
                            value={oldPassword}
                            onChange={(event) => setOldPassword(event.target.value)}
                            required
                        />
                    </div>

                    <div className="form-group">
                        <label htmlFor="new-password">Contraseña nueva</label>
                        <input
                            id="new-password"
                            type="password"
                            value={newPassword}
                            onChange={(event) => setNewPassword(event.target.value)}
                            minLength={8}
                            maxLength={128}
                            required
                        />
                    </div>

                    <div className="form-group">
                        <label htmlFor="confirmation">Repetir contraseña nueva</label>
                        <input
                            id="confirmation"
                            type="password"
                            value={confirmation}
                            onChange={(event) => setConfirmation(event.target.value)}
                            required
                        />
                    </div>

                    {error && <p role="alert">{error}</p>}

                    <button className="login-button" type="submit" disabled={loading}>
                        {loading ? 'Guardando...' : 'Cambiar contraseña'}
                    </button>
                </form>
            </section>
        </main>
    );
}