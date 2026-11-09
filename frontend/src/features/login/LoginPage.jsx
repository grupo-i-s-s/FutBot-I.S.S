import {useState} from 'react';
import {login} from './api';
import './LoginPage.css';
import {Link, useLocation, useNavigate} from 'react-router';
import {useSession} from '../session/SessionProvider.jsx';
import {routes} from '@/routes.js';

export default function LoginPage() {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    const {refreshSession} = useSession();
    const navigate = useNavigate();
    const {search, hash, state} = useLocation();

    async function handleSubmit(event) {
        event.preventDefault();
        if (loading) return;
        setError('');
        setLoading(true);

        try {
            await login(email, password);
            void refreshSession();
            navigate({pathname: routes.home, search, hash}, {replace: true, state});
        } catch (err) {
            const fieldErrors = Object.values(err.fields ?? {}).join(' ');

            setError(fieldErrors || err.message || 'No se pudo iniciar sesión.');
        } finally {
            setLoading(false);
        }
    }

    return (
        <main className="login-page">
            <section className="login-card">
                <h1 className="login-title">
                    Inicio de Sesión<br></br>FutBot
                </h1>

                <form onSubmit={handleSubmit}>
                    <div className="form-group">
                        <label htmlFor="email">
                            Email
                        </label>

                        <input
                            id="email"
                            type="email"
                            placeholder="nombre@gmail.com"
                            value={email}
                            onChange={(event) => setEmail(event.target.value)}>
                        </input>
                    </div>

                    <div className="form-group">
                        <label htmlFor="password">
                            Contraseña
                        </label>

                        <input
                            id="password"
                            type="password"
                            placeholder="Ingrese su contraseña"
                            value={password}
                            onChange={(event) => setPassword(event.target.value)}>
                        </input>
                    </div>

                    <button type="submit" className="login-button" disabled={loading}>
                        {loading ? 'Iniciando sesión…' : 'Iniciar Sesión'}
                    </button>
                    {error && <p role="alert">{error}</p>}
                    <Link to={routes.register} className="Registro">Registrarme</Link>
                </form>
            </section>

        </main>

    );
}
