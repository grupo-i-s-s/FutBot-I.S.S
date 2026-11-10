import {useState} from 'react';
import {ArrowLeft, ArrowRight, CircleAlert, CircleCheck, Info, LoaderCircle, MailCheck} from 'lucide-react';
import {Link, useLocation} from 'react-router';
import {toast} from 'sonner';
import {Alert, AlertDescription} from '@/components/ui/alert';
import {Button, buttonVariants} from '@/components/ui/button';
import {Field, FieldDescription, FieldLabel, FieldLegend, FieldSet} from '@/components/ui/field';
import {Input} from '@/components/ui/input';
import AuthCard from '@/features/session/components/AuthCard.jsx';
import {routes} from '@/routes.js';
import {resendVerification, verifyEmail} from './api.js';

export default function VerifyEmailPage() {
    const location = useLocation();
    const email = location.state?.email ?? '';
    const [code, setCode] = useState('');
    const [error, setError] = useState('');
    const [message, setMessage] = useState('');
    const [pendingAction, setPendingAction] = useState(null);
    const [verified, setVerified] = useState(false);
    const [editingRegistration, setEditingRegistration] = useState(location.state?.editRegistration === true);
    const [clubName, setClubName] = useState('');
    const [password, setPassword] = useState('');
    const [passwordConfirmation, setPasswordConfirmation] = useState('');
    const loading = pendingAction !== null;

    async function handleVerify(event) {
        event.preventDefault();
        if (!email || loading) return;

        setError('');
        setMessage('');
        setPendingAction('verify');

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
            toast.success('Correo verificado');
        } catch (err) {
            const fieldErrors = Object.values(err.fields ?? {}).join(' ');
            setError(fieldErrors || err.message || 'No se pudo verificar el correo.');
            if (err.code === 'ACCOUNT_DUPLICATE' && err.fields?.clubName) {
                setEditingRegistration(true);
            }
        } finally {
            setPendingAction(null);
        }
    }

    async function handleResend() {
        if (!email || loading) return;

        setError('');
        setMessage('');
        setPendingAction('resend');

        try {
            const result = await resendVerification(email);
            setMessage(result?.message || 'Si hay una verificación pendiente, se enviará un nuevo código.');
        } catch (err) {
            setError(err.message || 'No se pudo reenviar el código.');
        } finally {
            setPendingAction(null);
        }
    }

    const description = email ? (
        <>
            Ingresá el código de 6 dígitos que enviamos a{' '}
            <strong className="font-medium text-foreground">{email}</strong>.
            Si no lo encontrás, revisá la carpeta de spam.
        </>
    ) : 'Volvé al registro para continuar con la verificación.';

    return (
        <AuthCard
            icon={verified ? CircleCheck : MailCheck}
            title={verified ? 'Tu cuenta está lista' : 'Verificá tu correo'}
            description={verified ? undefined : description}
            footer={!verified && (
                <Link
                    to={routes.register}
                    state={{email}}
                    className={buttonVariants({variant: 'link'})}
                >
                    <ArrowLeft aria-hidden="true"/>
                    Volver al registro
                </Link>
            )}
        >
            {verified ? (
                <div className="grid gap-4">
                    <Alert role="status" className="border-primary/20 bg-primary/5">
                        <CircleCheck aria-hidden="true"/>
                        <AlertDescription className="text-foreground">
                            ¡Correo verificado! Ya podés iniciar sesión.
                        </AlertDescription>
                    </Alert>
                    <Link
                        to={routes.signIn}
                        className={buttonVariants({size: 'lg', className: 'h-10 w-full'})}
                    >
                        Ir a iniciar sesión
                        <ArrowRight aria-hidden="true"/>
                    </Link>
                </div>
            ) : email && (
                <form className="grid gap-4" onSubmit={handleVerify} aria-busy={loading}>
                    <Field>
                        <FieldLabel htmlFor="verification-code">Código de verificación</FieldLabel>
                        <Input
                            id="verification-code"
                            type="text"
                            inputMode="numeric"
                            autoComplete="one-time-code"
                            pattern="[0-9]{6}"
                            maxLength={6}
                            className="h-10 bg-background text-center font-mono tracking-widest placeholder:font-sans placeholder:tracking-normal"
                            value={code}
                            placeholder="Ingrese el código"
                            disabled={loading}
                            onChange={(event) => setCode(event.target.value.replace(/\D/g, ''))}
                            required
                        />
                    </Field>

                    {error && (
                        <Alert variant="destructive">
                            <CircleAlert aria-hidden="true"/>
                            <AlertDescription>{error}</AlertDescription>
                        </Alert>
                    )}
                    {message && (
                        <Alert role="status">
                            <Info aria-hidden="true"/>
                            <AlertDescription>{message}</AlertDescription>
                        </Alert>
                    )}

                    {editingRegistration && (
                        <FieldSet className="rounded-lg border p-4" disabled={loading}>
                            <FieldLegend variant="label" className="px-1">Cambiar datos del registro</FieldLegend>
                            <FieldDescription>
                                Completá solo los datos que quieras cambiar y usá el código que recibiste.
                            </FieldDescription>
                            <Field>
                                <FieldLabel htmlFor="corrected-club-name">Nuevo nombre del club</FieldLabel>
                                <Input
                                    id="corrected-club-name"
                                    className="h-10 bg-background"
                                    maxLength={50}
                                    value={clubName}
                                    onChange={(event) => setClubName(event.target.value)}
                                />
                            </Field>
                            <Field>
                                <FieldLabel htmlFor="corrected-password">Nueva contraseña</FieldLabel>
                                <Input
                                    id="corrected-password"
                                    type="password"
                                    className="h-10 bg-background"
                                    autoComplete="new-password"
                                    minLength={8}
                                    maxLength={128}
                                    value={password}
                                    onChange={(event) => setPassword(event.target.value)}
                                />
                            </Field>
                            <Field>
                                <FieldLabel htmlFor="corrected-password-confirmation">Confirmar nueva contraseña</FieldLabel>
                                <Input
                                    id="corrected-password-confirmation"
                                    type="password"
                                    className="h-10 bg-background"
                                    autoComplete="new-password"
                                    minLength={8}
                                    maxLength={128}
                                    value={passwordConfirmation}
                                    onChange={(event) => setPasswordConfirmation(event.target.value)}
                                />
                            </Field>
                        </FieldSet>
                    )}

                    <div className="grid gap-2">
                        <Button type="submit" size="lg" className="h-10 w-full" disabled={loading}>
                            {pendingAction === 'verify' && <LoaderCircle className="animate-spin motion-reduce:animate-none" aria-hidden="true"/>}
                            {pendingAction === 'verify' ? 'Verificando…' : 'Verificar correo'}
                        </Button>
                        <Button
                            type="button"
                            variant="outline"
                            size="lg"
                            className="h-10 w-full"
                            disabled={loading}
                            onClick={handleResend}
                        >
                            {pendingAction === 'resend' && <LoaderCircle className="animate-spin motion-reduce:animate-none" aria-hidden="true"/>}
                            {pendingAction === 'resend' ? 'Reenviando…' : 'Reenviar código'}
                        </Button>
                        <Button
                            type="button"
                            variant="link"
                            className="justify-self-center"
                            aria-expanded={editingRegistration}
                            disabled={loading}
                            onClick={() => setEditingRegistration((editing) => !editing)}
                        >
                            {editingRegistration ? 'Usar los datos anteriores' : 'Cambiar datos del registro'}
                        </Button>
                    </div>
                </form>
            )}
        </AuthCard>
    );
}
