import {useId} from 'react';
import {useNavigate} from 'react-router';
import {CircleAlert, CircleCheck, LoaderCircle} from 'lucide-react';
import {Alert, AlertDescription, AlertTitle} from '@/components/ui/alert';
import {Button} from '@/components/ui/button';
import {Dialog, DialogClose, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle} from '@/components/ui/dialog';
import {Field, FieldLabel} from '@/components/ui/field';
import {Input} from '@/components/ui/input';
import {routes} from '@/routes.js';
import BehaviourCodeEditor from '../behaviours/components/BehaviourCodeEditor';
import {useUnsavedChanges} from '../behaviours/hooks/useUnsavedChanges';
import {createDtBehaviour} from './api.js';
import {useBehaviourCreation} from './useBehaviourCreation.js';

const DT_TEMPLATE = [
    'from primitives.dt_behaviour import DtAction',
    'from primitives.behaviours import BehaviourMode',
    '',
    'def decide(obs):',
    '    cambios = [',
    '        cambiar_comportamiento(jugador, BehaviourMode.DEFENSIVE)',
    '        for jugador in obs.players_id',
    '    ]',
    '    if obs.can_substitute:',
    '        cambio = sustituir(obs.players_id[0], obs.substitutes_id[0])',
    '        return DtAction(cambios, [cambio])',
    '    return DtAction(cambios)',
].join('\n');

const dtApiFunctions = [
    {name: 'obs.time_played', description: 'Tiempo de juego transcurrido en segundos.'},
    {name: 'obs.my_goals / obs.rival_goals', description: 'Goles de tu equipo y del rival.'},
    {name: 'obs.players_id / obs.substitutes_id', description: 'Identificadores de los jugadores en cancha y del banco.'},
    {name: 'obs.can_substitute', description: 'Indica que el DT puede pedir una sustitución en la pausa actual.'},
    {name: 'obs.pause_index', description: 'Vale 1, 2 o 3 durante una pausa. El 2 corresponde al entretiempo.'},
    {name: 'cambiar_comportamiento(jugador, modo)', description: 'Acepta BehaviourMode.BALANCED, BehaviourMode.OFFENSIVE y BehaviourMode.DEFENSIVE.'},
    {name: 'sustituir(titular, suplente)', description: 'Pide un cambio durante una pausa con cuota disponible.'},
    {name: 'DtAction(cambios, sustituciones)', description: 'Devuelve las órdenes que evaluará el motor. La lista de sustituciones es opcional.'},
];

export default function CreateBehaviourPage() {
    const navigate = useNavigate();
    const formId = useId();
    const {
        name, setName, code, changeCode, error, diagnostics, isValid, action, pending, dirty, handleValidate, handleSubmit,
    } = useBehaviourCreation({
        kind: 'COACH', template: DT_TEMPLATE, create: createDtBehaviour, onCreated: handleCreated,
    });
    const allowNavigation = useUnsavedChanges(dirty);
    const busy = Boolean(action);

    function handleClose() {
        if (pending.current) return;
        navigate(routes.myClub, {replace: true, state: {tab: 'dt'}});
    }

    function handleCreated() {
        allowNavigation();
        navigate(routes.myClub, {
            replace: true,
            state: {tab: 'dt', notice: 'Comportamiento del DT creado. Ya podés seleccionarlo y guardar el DT.'},
        });
    }

    return (
        <Dialog open onOpenChange={open => { if (!open) handleClose(); }}>
            <DialogContent showCloseButton={false} className="max-h-[90dvh] overflow-y-auto sm:max-w-5xl" aria-busy={busy}>
                <DialogHeader>
                    <DialogTitle>Crear comportamiento del DT</DialogTitle>
                    <DialogDescription>Elegí un nombre y escribí el código que dirigirá a tu equipo.</DialogDescription>
                </DialogHeader>
                <form id={formId} onSubmit={handleSubmit} className="space-y-4">
                    <Field>
                        <FieldLabel htmlFor={`${formId}-name`}>Nombre del comportamiento</FieldLabel>
                        <Input
                            id={`${formId}-name`}
                            placeholder="Ej. Presión alta"
                            maxLength={30}
                            value={name}
                            disabled={busy}
                            className="h-10 bg-background"
                            onChange={(event) => setName(event.target.value)}
                        />
                    </Field>
                    <BehaviourCodeEditor
                        value={code}
                        onChange={changeCode}
                        diagnostics={diagnostics}
                        documentId="new"
                        kind="COACH"
                        readOnly={busy}
                        functions={dtApiFunctions}
                        helpDescription="Escribí una función decide(obs) que devuelva DtAction con los cambios tácticos y las sustituciones del equipo."
                    />
                    {error && (
                        <Alert variant="destructive">
                            <CircleAlert aria-hidden="true"/>
                            <AlertTitle>Revisá el comportamiento</AlertTitle>
                            <AlertDescription>{error}</AlertDescription>
                        </Alert>
                    )}
                    {isValid && (
                        <Alert role="status" className="border-primary/20 bg-primary/5">
                            <CircleCheck aria-hidden="true"/>
                            <AlertDescription>El código es válido.</AlertDescription>
                        </Alert>
                    )}
                </form>
                <DialogFooter>
                    <DialogClose render={<Button type="button" variant="outline" disabled={busy}/>}>Cancelar</DialogClose>
                    <Button type="button" variant="outline" onClick={handleValidate} disabled={busy || !code.trim()}>
                        {action === 'validate' && <LoaderCircle className="animate-spin motion-reduce:animate-none" aria-hidden="true"/>}
                        {action === 'validate' ? 'Validando…' : 'Validar código'}
                    </Button>
                    <Button type="submit" form={formId} disabled={busy}>
                        {action === 'save' && <LoaderCircle className="animate-spin motion-reduce:animate-none" aria-hidden="true"/>}
                        {action === 'save' ? 'Guardando…' : 'Guardar Comportamiento'}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
