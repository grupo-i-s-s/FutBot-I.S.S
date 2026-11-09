import {useRef, useState} from 'react';
import {LoaderCircle, Trash2} from 'lucide-react';
import {Button} from '@/components/ui/button';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger} from '@/components/ui/dialog';
import {deleteBehaviour} from '../api';

export default function DeleteBehaviourButton({behaviour, onDeleted}) {
    const [isOpen, setIsOpen] = useState(false);
    const [isDeleting, setIsDeleting] = useState(false);
    const [error, setError] = useState(null);
    const pending = useRef(false);

    const isInUse =
        error?.status === 409 &&
        error?.code === 'BEHAVIOUR_IN_USE';

    const references = isInUse
        ? Object.entries(error.fields ?? {})
        : [];

    async function handleConfirm() {
        if (pending.current) return;

        pending.current = true;
        setIsDeleting(true);
        setError(null);

        try {
            await deleteBehaviour(behaviour.id);
        } catch (requestError) {
            setError(requestError);
            return;
        } finally {
            pending.current = false;
            setIsDeleting(false);
        }

        setIsOpen(false);
        onDeleted(behaviour);
    }

    return (
        <Dialog
            open={isOpen}
            onOpenChange={(open) => {
                if (pending.current) return;
                setError(null);
                setIsOpen(open);
            }}
        >
            <DialogTrigger
                render={
                    <Button
                        type="button"
                        variant="ghost"
                        size="icon"
                        aria-label={`Eliminar ${behaviour.name}`}
                        title={`Eliminar ${behaviour.name}`}
                        className="size-10 rounded-xl text-red-600 hover:bg-red-50 hover:text-red-700"
                    />
                }
            >
                <Trash2 className="size-4" aria-hidden="true"/>
            </DialogTrigger>

            <DialogContent
                showCloseButton={false}
                className="sm:max-w-md"
                aria-busy={isDeleting}
            >
                <DialogHeader>
                    <div className="mb-2 flex size-12 items-center justify-center rounded-2xl bg-red-50 text-red-600">
                        <Trash2 className="size-6" aria-hidden="true"/>
                    </div>

                    <DialogTitle className="text-lg leading-snug font-bold">
                        ¿Segur@ que desea eliminar el comportamiento?
                    </DialogTitle>

                    <DialogDescription>
                        Vas a eliminar{' '}
                        <strong className="font-semibold text-foreground">
                            “{behaviour.name}”
                        </strong>{' '}
                        del catálogo activo.
                    </DialogDescription>
                </DialogHeader>

                {error && (
                    <div
                        role="alert"
                        className="space-y-2 rounded-xl border border-red-200 bg-red-50 p-3 text-sm text-red-800"
                    >
                        <p className="font-semibold">
                            {isInUse
                                ? 'Este comportamiento está en uso.'
                                : 'No se pudo eliminar el comportamiento.'}
                        </p>

                        <p>
                            {isInUse
                                ? 'Debés reasignarlo antes de poder eliminarlo.'
                                : error.message || 'Intentá nuevamente.'}
                        </p>

                        {references.length > 0 && (
                            <>
                                <p className="font-medium">Reemplazalo en:</p>
                                <ul className="list-disc space-y-1 pl-5">
                                    {references.map(([key, description]) => (
                                        <li key={key}>{description}</li>
                                    ))}
                                </ul>
                            </>
                        )}
                    </div>
                )}

                <DialogFooter>
                    <Button
                        type="button"
                        variant="outline"
                        disabled={isDeleting}
                        onClick={() => setIsOpen(false)}
                    >
                        Cancelar
                    </Button>

                    <Button
                        type="button"
                        variant="destructive"
                        disabled={isDeleting}
                        onClick={handleConfirm}
                    >
                        {isDeleting && (
                            <LoaderCircle
                                className="size-4 animate-spin"
                                aria-hidden="true"
                            />
                        )}
                        {isDeleting ? 'Eliminando…' : 'Eliminar'}
                    </Button>
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}