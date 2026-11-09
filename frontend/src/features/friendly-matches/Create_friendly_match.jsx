import {useEffect, useRef, useState} from 'react';
import {ArrowLeft, CalendarPlus, CircleAlert, LoaderCircle, Plus} from 'lucide-react';
import {Link, parsePath, useLocation, useNavigate} from 'react-router';
import {toast} from 'sonner';
import {Alert, AlertDescription, AlertTitle} from '@/components/ui/alert';
import {Button, buttonVariants} from '@/components/ui/button';
import {Card, CardContent, CardFooter, CardHeader} from '@/components/ui/card';
import {Field, FieldDescription, FieldLabel} from '@/components/ui/field';
import {Input} from '@/components/ui/input';
import {routePath, routes} from '@/routes.js';
import {createFriendlyMatch} from './api.js';
import {friendlyMatchError} from './scheduleConflict.js';

const CREATE_MATCH_TOAST_ID = 'friendly-match-create';

function openStartTimePicker(event) {
    try {
        event.currentTarget.showPicker?.();
    } catch (error) {
        if (!(error instanceof DOMException)) throw error;
        // El navegador puede abrir el selector con su propia acción de clic.
    }
}

export default function CreateFriendlyMatch() {
    const [matchTime, setMatchTime] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [error, setError] = useState(null);
    const pending = useRef(false);
    const navigate = useNavigate();
    const {state} = useLocation();
    const source = typeof state?.returnTo === 'string' ? state.returnTo : '';
    const returnTo = parsePath(source).pathname === routes.friendlyMatches ? source : routes.friendlyMatches;
    const invalidDate = error?.code === 'MATCH_INVALID_DATE' || error?.code === 'LEAGUE_SCHEDULE_CONFLICT';

    useEffect(() => () => { pending.current = false; }, []);

    async function handleSubmit(event) {
        event.preventDefault();
        if (pending.current) return;

        const startDate = new Date(matchTime);
        if (Number.isNaN(startDate.getTime()) || startDate <= new Date()) {
            setError({code: 'MATCH_INVALID_DATE', message: 'La fecha de inicio debe ser futura.'});
            return;
        }

        pending.current = true;
        setIsSubmitting(true);
        setError(null);

        try {
            const response = await createFriendlyMatch(matchTime);
            if (pending.current) {
                toast.success('Amistoso creado', {
                    id: CREATE_MATCH_TOAST_ID,
                    description: 'El partido queda a la espera de un rival.',
                });
                navigate(routePath(routes.match, {matchId: response.matchId}), {
                    replace: true,
                    state: {returnTo},
                });
            }
        } catch (requestError) {
            if (pending.current) {
                const message = friendlyMatchError(requestError, 'No se pudo crear el partido.');
                setError({code: requestError.code, message});
                toast.error('No se pudo crear el amistoso', {id: CREATE_MATCH_TOAST_ID, description: message});
            }
        } finally {
            if (pending.current) {
                pending.current = false;
                setIsSubmitting(false);
            }
        }
    }

    return (
        <main className="mx-auto w-[calc(100%_-_32px)] max-w-2xl space-y-4 py-8 sm:py-12">
            <Link to={returnTo} className={buttonVariants({variant: 'ghost'})}>
                <ArrowLeft data-icon="inline-start" aria-hidden="true"/>
                Volver a amistosos
            </Link>

            <Card>
                <CardHeader className="border-b">
                    <div className="flex items-center gap-4">
                        <span className="grid size-12 shrink-0 place-items-center rounded-xl bg-primary/10 text-primary">
                            <CalendarPlus className="size-6" aria-hidden="true"/>
                        </span>
                        <div className="space-y-1">
                            <h1 className="text-2xl font-bold sm:text-3xl">Crear amistoso</h1>
                            <p className="text-muted-foreground">Programá un partido para que otro club se sume.</p>
                        </div>
                    </div>
                </CardHeader>

                <form className="space-y-4" onSubmit={handleSubmit} aria-busy={isSubmitting}>
                    <CardContent className="space-y-4">
                        <Field data-invalid={invalidDate || undefined} data-disabled={isSubmitting || undefined}>
                            <FieldLabel htmlFor="friendly-start-time">Fecha y hora de inicio</FieldLabel>
                            <Input
                                type="datetime-local"
                                id="friendly-start-time"
                                className="h-10 cursor-pointer bg-background"
                                value={matchTime}
                                onClick={openStartTimePicker}
                                onChange={(event) => {
                                    setMatchTime(event.target.value);
                                    setError(null);
                                }}
                                aria-describedby={invalidDate ? 'friendly-start-hint friendly-create-error' : 'friendly-start-hint'}
                                aria-invalid={invalidDate || undefined}
                                disabled={isSubmitting}
                                required
                            />
                            <FieldDescription id="friendly-start-hint">
                                Elegí un horario futuro en la zona horaria de tu dispositivo.
                            </FieldDescription>
                        </Field>

                        {error && (
                            <Alert id="friendly-create-error" variant="destructive">
                                <CircleAlert aria-hidden="true"/>
                                <AlertTitle>No se pudo crear el amistoso</AlertTitle>
                                <AlertDescription>
                                    {error.message}
                                    {error.code === 'CLUB_NOT_AVAILABLE' && (
                                        <Link to={routes.myClub} className="mt-2 block w-fit font-medium">
                                            Ir a Mi club
                                        </Link>
                                    )}
                                </AlertDescription>
                            </Alert>
                        )}
                    </CardContent>

                    <CardFooter className="justify-end">
                        <Button type="submit" size="lg" className="w-full sm:w-auto" disabled={isSubmitting || !matchTime}>
                            {isSubmitting
                                ? <LoaderCircle className="animate-spin" data-icon="inline-start" aria-hidden="true"/>
                                : <Plus data-icon="inline-start" aria-hidden="true"/>}
                            {isSubmitting ? 'Creando amistoso…' : 'Crear amistoso'}
                        </Button>
                    </CardFooter>
                </form>
            </Card>
        </main>
    );
}
