import {useEffect, useId, useRef, useState} from 'react';
import {CircleAlert, LoaderCircle, Plus} from 'lucide-react';
import {toast} from 'sonner';
import {Alert, AlertDescription, AlertTitle} from '@/components/ui/alert';
import {Badge} from '@/components/ui/badge';
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
import {Field, FieldLabel} from '@/components/ui/field';
import {Input} from '@/components/ui/input';
import {Slider} from '@/components/ui/slider';
import {createPlayer} from './api.js';

const POINT_BUDGET = 300;
const ATTRIBUTES = [
    ['power', 'Potencia'],
    ['agility', 'Agilidad'],
    ['control', 'Control'],
    ['speed', 'Velocidad'],
    ['strength', 'Fuerza'],
];
const INITIAL_ATTRIBUTES = Object.fromEntries(ATTRIBUTES.map(([key]) => [key, 60]));

export default function CreatePlayerDialog({onCreated}) {
    const formId = useId();
    const nameId = `${formId}-name`;
    const [isOpen, setIsOpen] = useState(false);
    const [name, setName] = useState('');
    const [attributes, setAttributes] = useState(INITIAL_ATTRIBUTES);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [error, setError] = useState('');
    const pending = useRef(false);
    const errorToast = useRef(null);

    const totalPoints = Object.values(attributes).reduce((total, points) => total + points, 0);
    const remainingPoints = POINT_BUDGET - totalPoints;

    useEffect(() => () => { pending.current = false; }, []);

    function dismissErrorToast() {
        if (errorToast.current !== null) {
            toast.dismiss(errorToast.current);
            errorToast.current = null;
        }
    }

    function resetDraft() {
        setName('');
        setAttributes(INITIAL_ATTRIBUTES);
        setError('');
        dismissErrorToast();
    }

    function handleOpenChange(open) {
        if (pending.current) return;

        if (!open) resetDraft();
        setIsOpen(open);
    }

    async function handleSubmit(event) {
        event.preventDefault();
        if (pending.current || !name.trim() || remainingPoints !== 0) return;

        setError('');
        dismissErrorToast();
        pending.current = true;
        setIsSubmitting(true);

        try {
            const {power, agility, control, speed, strength} = attributes;
            const player = await createPlayer(name.trim(), power, agility, control, speed, strength);
            if (!pending.current) return;

            resetDraft();
            setIsOpen(false);
            toast.success('Jugador creado', {description: `${player.name} se agregó al plantel.`});
            onCreated?.(player);
        } catch (err) {
            if (!pending.current) return;

            const fieldErrors = Object.values(err.fields ?? {}).join(' ');
            const message = err.status === 401
                ? 'Tu sesión venció. Iniciá sesión nuevamente.'
                : fieldErrors || err.message || 'Intentá nuevamente.';
            setError(message);
            errorToast.current = toast.error('No se pudo crear el jugador', {description: message});
        } finally {
            if (pending.current) {
                pending.current = false;
                setIsSubmitting(false);
            }
        }
    }

    return (
        <Dialog open={isOpen} onOpenChange={handleOpenChange}>
            <DialogTrigger render={<Button type="button" size="sm"/>}>
                <Plus data-icon="inline-start" aria-hidden="true"/>
                Crear jugador
            </DialogTrigger>

            <DialogContent
                showCloseButton={false}
                className="max-h-[90dvh] overflow-y-auto sm:max-w-lg"
                aria-busy={isSubmitting}
            >
                <DialogHeader>
                    <DialogTitle>Crear jugador</DialogTitle>
                    <DialogDescription>Elegí un nombre y repartí 300 puntos entre los atributos.</DialogDescription>
                </DialogHeader>

                <form id={formId} className="space-y-4" onSubmit={handleSubmit}>
                    <Field>
                        <FieldLabel htmlFor={nameId}>Nombre del jugador</FieldLabel>
                        <Input
                            id={nameId}
                            name="name"
                            className="h-10 bg-background"
                            value={name}
                            onChange={(event) => setName(event.target.value)}
                            disabled={isSubmitting}
                            required
                        />
                    </Field>

                    <fieldset className="space-y-2" disabled={isSubmitting}>
                        <legend className="mb-2 text-sm font-semibold">Atributos</legend>
                        {ATTRIBUTES.map(([key, label]) => {
                            const labelId = `${formId}-${key}`;
                            return (
                                <div key={key}>
                                    <div className="flex items-center justify-between gap-2">
                                        <span id={labelId} className="text-sm font-medium">{label}</span>
                                        <span className="text-sm font-medium text-primary tabular-nums" aria-hidden="true">
                                            {attributes[key]}
                                        </span>
                                    </div>
                                    <Slider
                                        aria-labelledby={labelId}
                                        min={20}
                                        max={100}
                                        step={1}
                                        value={attributes[key]}
                                        onValueChange={(value) => setAttributes(current => ({...current, [key]: value}))}
                                        disabled={isSubmitting}
                                    />
                                </div>
                            );
                        })}
                    </fieldset>

                    <div role="status" className="flex flex-wrap items-center justify-between gap-2 rounded-lg border bg-muted/40 p-3">
                        <div>
                            <p className="font-medium">Puntos asignados</p>
                            <p className="text-xs text-muted-foreground">
                                {remainingPoints === 0
                                    ? 'Distribución completa'
                                    : `${Math.abs(remainingPoints)} ${remainingPoints > 0 ? 'por asignar' : 'por quitar'}`}
                            </p>
                        </div>
                        <Badge variant={remainingPoints === 0 ? 'default' : 'outline'} className="tabular-nums">
                            {totalPoints} / {POINT_BUDGET}
                        </Badge>
                    </div>

                    {error && (
                        <Alert variant="destructive">
                            <CircleAlert aria-hidden="true"/>
                            <AlertTitle>No se pudo crear el jugador</AlertTitle>
                            <AlertDescription>{error}</AlertDescription>
                        </Alert>
                    )}
                </form>

                <DialogFooter>
                    <DialogClose render={<Button type="button" variant="outline" disabled={isSubmitting}/>}>
                        Cancelar
                    </DialogClose>
                    <Button type="submit" form={formId} disabled={isSubmitting || !name.trim() || remainingPoints !== 0}>
                        {isSubmitting && <LoaderCircle className="size-4 animate-spin motion-reduce:animate-none" aria-hidden="true"/>}
                        {isSubmitting ? 'Creando…' : 'Crear jugador'}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
