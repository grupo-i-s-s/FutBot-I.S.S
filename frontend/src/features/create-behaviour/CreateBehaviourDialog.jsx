import {useId, useRef, useState} from 'react';
import {CircleAlert, CircleCheck, LoaderCircle, Plus} from 'lucide-react';
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
import {Field, FieldLabel} from '@/components/ui/field';
import {Input} from '@/components/ui/input';
import BehaviourCodeEditor from '../behaviours/components/BehaviourCodeEditor';
import {DISCARD_MESSAGE, UnsavedChangesGuard} from '../behaviours/hooks/useUnsavedChanges';
import {createBehaviour} from './api.js';
import {useBehaviourCreation} from './useBehaviourCreation.js';

const PLAYER_TEMPLATE = 'def decide(observation):\n    return ir_a_pelota()\n';

export default function CreateBehaviourDialog({onCreated}) {
    const formId = useId();
    const nameId = `${formId}-name`;
    const [isOpen, setIsOpen] = useState(false);
    const errorToast = useRef(null);
    const {
        name, setName, code, changeCode, error, diagnostics, isValid, action, pending, dirty,
        reset, handleValidate, handleSubmit,
    } = useBehaviourCreation({
        kind: 'PLAYER',
        template: PLAYER_TEMPLATE,
        create: createBehaviour,
        onCreated: handleCreated,
        onRequestStart: dismissErrorToast,
        onRequestError: showRequestError,
    });
    const busy = Boolean(action);

    function dismissErrorToast() {
        if (errorToast.current !== null) {
            toast.dismiss(errorToast.current);
            errorToast.current = null;
        }
    }

    function showRequestError(message, requestAction) {
        const title = requestAction === 'validate' ? 'No se pudo validar el código' : 'No se pudo crear el comportamiento';
        errorToast.current = toast.error(title, {description: message, position: 'top-right'});
    }

    function handleCreated(behaviour) {
        reset();
        setIsOpen(false);
        onCreated?.(behaviour);
    }

    function handleOpenChange(open) {
        if (pending.current) return;

        if (!open) {
            if (dirty && !window.confirm(DISCARD_MESSAGE)) return;
            reset();
            dismissErrorToast();
        }
        setIsOpen(open);
    }

    return (
        <Dialog open={isOpen} onOpenChange={handleOpenChange}>
            {isOpen && <UnsavedChangesGuard dirty={dirty}/>}
            <DialogTrigger render={<Button type="button"/>}>
                <Plus data-icon="inline-start" aria-hidden="true"/>
                Crear nuevo comportamiento
            </DialogTrigger>

            <DialogContent showCloseButton={false} className="max-h-[90dvh] overflow-y-auto sm:max-w-5xl" aria-busy={busy}>
                <DialogHeader>
                    <DialogTitle>Crear comportamiento</DialogTitle>
                    <DialogDescription>Elegí un nombre y escribí el código que ejecutarán tus jugadores.</DialogDescription>
                </DialogHeader>

                <form id={formId} className="space-y-4" onSubmit={handleSubmit}>
                    <Field>
                        <FieldLabel htmlFor={nameId}>Nombre del comportamiento</FieldLabel>
                        <Input
                            id={nameId}
                            name="name"
                            className="h-10 bg-background"
                            maxLength={50}
                            placeholder="Ej. Presión alta"
                            value={name}
                            onChange={(event) => setName(event.target.value)}
                            disabled={busy}
                        />
                    </Field>

                    <BehaviourCodeEditor
                        value={code}
                        onChange={changeCode}
                        diagnostics={diagnostics}
                        documentId="new"
                        kind="PLAYER"
                        readOnly={busy}
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
                        {action === 'save' ? 'Guardando…' : 'Guardar comportamiento'}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
