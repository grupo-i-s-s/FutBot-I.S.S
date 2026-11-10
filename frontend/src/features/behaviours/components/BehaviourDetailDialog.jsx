import {useEffect, useState} from 'react';
import {CircleAlert, LoaderCircle} from 'lucide-react';
import {Alert, AlertDescription} from '@/components/ui/alert';
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
import {getBehaviour} from '../api.js';

export default function BehaviourDetailDialog({behaviour}) {
    const [isOpen, setIsOpen] = useState(false);
    const [attempt, setAttempt] = useState(0);
    const [result, setResult] = useState(null);
    const detail = result?.id === behaviour.id ? result : null;

    useEffect(() => {
        if (!isOpen) return;

        const controller = new AbortController();
        const id = behaviour.id;

        async function load() {
            try {
                const data = await getBehaviour(id, {signal: controller.signal});
                if (!controller.signal.aborted) setResult({id, data});
            } catch (error) {
                if (controller.signal.aborted) return;
                const message = error.status === 401
                    ? 'Iniciá sesión para consultar el comportamiento.'
                    : error.message || 'No se pudo cargar el comportamiento.';
                setResult({id, error: message});
            }
        }

        load();
        return () => controller.abort();
    }, [attempt, behaviour.id, isOpen]);

    return (
        <Dialog open={isOpen} onOpenChange={(open) => {
            if (open) setResult(null);
            setIsOpen(open);
        }}>
            <DialogTrigger render={(
                <Button type="button" variant="outline" size="sm" aria-label={`Ver detalle de ${behaviour.name}`}/>
            )}>
                Ver detalle
            </DialogTrigger>

            <DialogContent showCloseButton={false} className="max-h-[90dvh] overflow-y-auto sm:max-w-3xl">
                <DialogHeader className="min-w-0">
                    <DialogTitle>Detalle de comportamiento</DialogTitle>
                    <DialogDescription className="wrap-anywhere">
                        Código de{' '}
                        <strong className="font-medium text-foreground">{detail?.data?.name ?? behaviour.name}</strong>
                        {' '}en modo de solo lectura.
                    </DialogDescription>
                </DialogHeader>

                {!detail && (
                    <p role="status" className="flex items-center gap-2 text-muted-foreground">
                        <LoaderCircle className="size-4 animate-spin" aria-hidden="true"/>
                        Cargando comportamiento…
                    </p>
                )}

                {detail?.error && (
                    <Alert variant="destructive">
                        <CircleAlert aria-hidden="true"/>
                        <AlertDescription>{detail.error}</AlertDescription>
                    </Alert>
                )}

                {detail?.data && (
                    <pre
                        role="region"
                        aria-label="Código del comportamiento"
                        tabIndex={0}
                        className="max-h-[55dvh] min-w-0 overflow-auto rounded-lg border bg-muted/50 p-4 text-sm leading-relaxed outline-none focus-visible:ring-2 focus-visible:ring-ring"
                    >
                        <code>{detail.data.code}</code>
                    </pre>
                )}

                <DialogFooter>
                    <DialogClose render={<Button type="button" variant="outline"/>}>Cerrar</DialogClose>
                    {detail?.error && (
                        <Button type="button" onClick={() => {
                            setResult(null);
                            setAttempt((current) => current + 1);
                        }}>
                            Reintentar
                        </Button>
                    )}
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}
