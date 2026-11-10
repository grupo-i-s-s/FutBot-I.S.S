import {useState} from 'react';
import {CircleAlert, LoaderCircle, ShieldPlus} from 'lucide-react';
import {Link, useLocation, useNavigate} from 'react-router';
import {toast} from 'sonner';
import {Alert, AlertDescription, AlertTitle} from '@/components/ui/alert';
import {Button, buttonVariants} from '@/components/ui/button';
import {Field, FieldDescription, FieldGroup, FieldLabel, FieldSet} from '@/components/ui/field';
import {Input} from '@/components/ui/input';
import AuthCard from '@/features/session/components/AuthCard.jsx';
import {routes} from '@/routes.js';
import {register} from './api.js';
import './RegisterPage.css';

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
        if (loading) return;

        setError('');
        setPendingEmail(null);
        setLoading(true);

        try {
            await register(email, clubName, password, repeatPassword);
            toast.success('Código de verificación enviado', {
                description: 'Revisá tu correo para completar el registro.',
            });
            navigate(routes.verifyEmail, {state: {email}});
        } catch (err) {
            if (err.code === 'EMAIL_VERIFICATION_PENDING') setPendingEmail(email);

            const fields = Object.values(err.fields ?? {});
            setError(fields.join(' ') || err.message || 'No se pudo registrar la cuenta.');
        } finally {
            setLoading(false);
        }
    }

    return (
        <AuthCard
            icon={ShieldPlus}
            title="Registrá tu club"
            description="Creá tu cuenta para empezar a armar tu equipo."
            footer={(
                <p className="text-muted-foreground">
                    ¿Ya tenés una cuenta?{' '}
                    <Link to={routes.signIn} className={buttonVariants({variant: 'link', className: 'h-auto px-0'})}>
                        Iniciar sesión
                    </Link>
                </p>
            )}
        >
            <form onSubmit={handleSubmit} className="space-y-4" aria-busy={loading}>
                <FieldSet disabled={loading}>
                    <FieldGroup className="gap-4">
                        <Field>
                            <FieldLabel htmlFor="club-name">Nombre del Club</FieldLabel>
                            <Input
                                id="club-name"
                                name="clubName"
                                className="h-10 bg-background"
                                placeholder="Nombre del club"
                                autoComplete="organization"
                                value={clubName}
                                onChange={(event) => setClubName(event.target.value)}
                                required
                            />
                        </Field>

                        <Field>
                            <FieldLabel htmlFor="user-email">Email</FieldLabel>
                            <Input
                                id="user-email"
                                name="email"
                                type="email"
                                className="h-10 bg-background"
                                placeholder="club@ejemplo.com"
                                autoComplete="email"
                                value={email}
                                onChange={(event) => {
                                    setEmail(event.target.value);
                                    if (pendingEmail) {
                                        setPendingEmail(null);
                                        setError('');
                                    }
                                }}
                                required
                            />
                        </Field>

                        <Field>
                            <FieldLabel htmlFor="user-password">Contraseña</FieldLabel>
                            <Input
                                id="user-password"
                                name="password"
                                type="password"
                                className="h-10 bg-background"
                                autoComplete="new-password"
                                aria-describedby="registration-password-hint"
                                value={password}
                                onChange={(event) => setPassword(event.target.value)}
                                minLength={8}
                                required
                            />
                            <FieldDescription id="registration-password-hint">Usá al menos 8 caracteres.</FieldDescription>
                        </Field>

                        <Field>
                            <FieldLabel htmlFor="user-password-confirm">Confirmar contraseña</FieldLabel>
                            <Input
                                id="user-password-confirm"
                                name="passwordConfirmation"
                                type="password"
                                className="h-10 bg-background"
                                autoComplete="new-password"
                                value={repeatPassword}
                                onChange={(event) => setRepeatPassword(event.target.value)}
                                required
                            />
                        </Field>
                    </FieldGroup>
                </FieldSet>

                {error && (
                    <Alert variant="destructive">
                        <CircleAlert aria-hidden="true"/>
                        <AlertTitle>{pendingEmail ? 'Verificación pendiente' : 'No se pudo registrar el club'}</AlertTitle>
                        <AlertDescription>
                            {error}
                            {pendingEmail && (
                                <div className="mt-2 grid gap-2 text-foreground">
                                    <span>Los datos de este formulario todavía no se guardaron.</span>
                                    <Link
                                        to={routes.verifyEmail}
                                        state={{email: pendingEmail}}
                                        className="w-fit font-medium text-primary"
                                    >
                                        Continuar con los datos anteriores
                                    </Link>
                                    <Link
                                        to={routes.verifyEmail}
                                        state={{email: pendingEmail, editRegistration: true}}
                                        className="w-fit font-medium text-primary"
                                    >
                                        Cambiar los datos con el código
                                    </Link>
                                </div>
                            )}
                        </AlertDescription>
                    </Alert>
                )}

                <Button type="submit" size="lg" className="h-10 w-full" disabled={loading}>
                    {loading && <LoaderCircle className="animate-spin motion-reduce:animate-none" aria-hidden="true"/>}
                    {loading ? 'Registrando…' : 'Registrar Club'}
                </Button>
            </form>
        </AuthCard>
    );
}
