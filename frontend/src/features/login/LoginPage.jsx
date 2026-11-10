import {useState} from 'react';
import {CircleAlert, LoaderCircle, LogIn} from 'lucide-react';
import {Link, useLocation, useNavigate} from 'react-router';
import {toast} from 'sonner';
import {Alert, AlertDescription, AlertTitle} from '@/components/ui/alert';
import {Button, buttonVariants} from '@/components/ui/button';
import {Field, FieldLabel} from '@/components/ui/field';
import {Input} from '@/components/ui/input';
import AuthCard from '@/features/session/components/AuthCard.jsx';
import {useSession} from '../session/SessionProvider.jsx';
import {routes} from '@/routes.js';
import {login} from './api.js';

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
            toast.success('Sesión iniciada');
            void refreshSession();
            navigate({pathname: routes.home, search, hash}, {replace: true, state});
        } catch (err) {
            const fieldErrors = Object.values(err.fields ?? {}).join(' ');

            setError(fieldErrors || err.message || 'Intentá nuevamente.');
        } finally {
            setLoading(false);
        }
    }

    return (
        <AuthCard
            icon={LogIn}
            title="Inicio de sesión"
            description="Ingresá a FutBot para gestionar tu club."
            footer={(
                <p className="text-sm text-muted-foreground">
                    ¿Todavía no tenés cuenta?{' '}
                    <Link to={routes.register} className={buttonVariants({variant: 'link', className: 'h-auto px-0'})}>
                        Registrarme
                    </Link>
                </p>
            )}
        >
            <form className="space-y-4" onSubmit={handleSubmit} aria-busy={loading}>
                <Field data-disabled={loading || undefined}>
                    <FieldLabel htmlFor="login-email">Email</FieldLabel>
                    <Input
                        id="login-email"
                        name="email"
                        type="email"
                        autoComplete="username"
                        className="h-10 bg-background"
                        placeholder="nombre@ejemplo.com"
                        value={email}
                        onChange={(event) => setEmail(event.target.value)}
                        disabled={loading}
                        required
                    />
                </Field>

                <Field data-disabled={loading || undefined}>
                    <div className="flex flex-wrap items-center justify-between gap-2">
                        <FieldLabel htmlFor="login-password">Contraseña</FieldLabel>
                        <Link
                            to={routes.passwordReset}
                            className={buttonVariants({variant: 'link', className: 'h-auto px-0'})}
                        >
                            Olvidé mi contraseña
                        </Link>
                    </div>
                    <Input
                        id="login-password"
                        name="password"
                        type="password"
                        autoComplete="current-password"
                        className="h-10 bg-background"
                        value={password}
                        onChange={(event) => setPassword(event.target.value)}
                        disabled={loading}
                        required
                    />
                </Field>

                {error && (
                    <Alert variant="destructive">
                        <CircleAlert aria-hidden="true"/>
                        <AlertTitle>No se pudo iniciar sesión</AlertTitle>
                        <AlertDescription>{error}</AlertDescription>
                    </Alert>
                )}

                <Button type="submit" size="lg" className="h-10 w-full" disabled={loading}>
                    {loading && <LoaderCircle className="animate-spin motion-reduce:animate-none" aria-hidden="true"/>}
                    {loading ? 'Iniciando sesión…' : 'Iniciar Sesión'}
                </Button>
            </form>
        </AuthCard>
    );
}
