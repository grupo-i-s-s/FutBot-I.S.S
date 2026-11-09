import {useEffect, useId, useRef, useState} from 'react';
import {CircleAlert, LoaderCircle, Plus} from 'lucide-react';
import {Link, useNavigate} from 'react-router';
import {toast} from 'sonner';
import {Alert, AlertDescription, AlertTitle} from '@/components/ui/alert';
import {Button} from '@/components/ui/button';
import {
    Dialog,
    DialogClose,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from '@/components/ui/dialog';
import {Field, FieldDescription, FieldLabel} from '@/components/ui/field';
import {Input} from '@/components/ui/input';
import {routePath, routes} from '@/routes.js';
import {createFriendlyMatch} from '../api.js';
import {friendlyMatchError} from '../scheduleConflict.js';

function openStartTimePicker(event) {
    try {
        event.currentTarget.showPicker?.();
    } catch (error) {
        if (!(error instanceof DOMException)) throw error;
        // El navegador puede abrir el selector con su propia acción de clic.
    }
}

export default function CreateFriendlyMatchDialog({initiallyOpen, returnTo}) {
    const formId = useId();
    const startTimeId = `${formId}-start-time`;
    const hintId = `${formId}-hint`;
    const errorId = `${formId}-error`;
    const [isOpen, setIsOpen] = useState(initiallyOpen);
    const [matchTime, setMatchTime] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [error, setError] = useState(null);
    const pending = useRef(false);
    const errorToast = useRef(null);
    const navigate = useNavigate();
    const invalidDate = error?.code === 'MATCH_INVALID_DATE' || error?.code === 'LEAGUE_SCHEDULE_CONFLICT';

    useEffect(() => () => { pending.current = false; }, []);

    function dismissErrorToast() {
        if (errorToast.current !== null) {
            toast.dismiss(errorToast.current);
            errorToast.current = null;
        }
    }

    function handleOpenChange(open) {
        if (pending.current) return;

        if (!open) {
            setMatchTime('');
            setError(null);
            dismissErrorToast();
        }
        setIsOpen(open);
    }

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
        dismissErrorToast();

        try {
            const response = await createFriendlyMatch(matchTime);
            if (pending.current) {
                toast.success('Amistoso creado', {
                    description: 'El partido queda a la espera de un rival.',
                });
                navigate(routePath(routes.match, {matchId: response.matchId}), {state: {returnTo}});
            }
        } catch (requestError) {
            if (pending.current) {
                const message = friendlyMatchError(requestError, 'No se pudo crear el partido.');
                setError({code: requestError.code, message});
                errorToast.current = toast.error('No se pudo crear el amistoso', {description: message});
            }
        } finally {
            if (pending.current) {
                pending.current = false;
                setIsSubmitting(false);
            }
        }
    }

    return (
        <Dialog open={isOpen} onOpenChange={handleOpenChange}>
            <DialogTrigger render={<Button type="button" size="lg"/>}>
                <Plus data-icon="inline-start" aria-hidden="true"/>
                Crear amistoso
            </DialogTrigger>

            <DialogContent
                showCloseButton={false}
                className="max-h-[90dvh] overflow-y-auto sm:max-w-lg"
                aria-busy={isSubmitting}
            >
                <DialogHeader>
                    <DialogTitle>Crear amistoso</DialogTitle>
                    <DialogDescription>Programá un partido para que otro club se sume.</DialogDescription>
                </DialogHeader>

                <form id={formId} className="space-y-4" onSubmit={handleSubmit}>
                    <Field data-invalid={invalidDate || undefined} data-disabled={isSubmitting || undefined}>
                        <FieldLabel htmlFor={startTimeId}>Fecha y hora de inicio</FieldLabel>
                        <Input
                            type="datetime-local"
                            id={startTimeId}
                            className="h-10 cursor-pointer bg-background"
                            value={matchTime}
                            onClick={openStartTimePicker}
                            onChange={(event) => {
                                setMatchTime(event.target.value);
                                setError(null);
                            }}
                            aria-describedby={invalidDate ? `${hintId} ${errorId}` : hintId}
                            aria-invalid={invalidDate || undefined}
                            disabled={isSubmitting}
                            required
                        />
                        <FieldDescription id={hintId}>
                            Elegí un horario futuro en la zona horaria de tu dispositivo.
                        </FieldDescription>
                    </Field>

                    {error && (
                        <Alert id={errorId} variant="destructive">
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
                </form>

                <DialogFooter>
                    <DialogClose render={<Button type="button" variant="outline" disabled={isSubmitting}/>}>
                        Cancelar
                    </DialogClose>
                    <Button type="submit" form={formId} disabled={isSubmitting || !matchTime}>
                        {isSubmitting && <LoaderCircle className="size-4 animate-spin" aria-hidden="true"/>}
                        {isSubmitting ? 'Creando amistoso…' : 'Crear amistoso'}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
