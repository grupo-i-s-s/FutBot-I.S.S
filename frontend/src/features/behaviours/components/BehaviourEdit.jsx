import {useEffect, useId, useRef, useState} from 'react';
import {LoaderCircle, Pencil, PencilOff} from 'lucide-react';
import {Button} from '@/components/ui/button';
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogTitle,
    DialogTrigger,
} from '@/components/ui/dialog';
import {
    getBehaviour,
    getBehaviourUsage,
    updateBehaviour,
} from '../api';
import BehaviourCodeEditor from './BehaviourCodeEditor';
import {
    DISCARD_MESSAGE,
    UnsavedChangesGuard,
} from '../hooks/useUnsavedChanges';

export default function BehaviourEdit({behaviour, onUpdated}) {
    const formId = useId();
    const pending = useRef(false);
    const loadController = useRef(null);

    const [usage, setUsage] = useState(null);
    const [usageError, setUsageError] = useState(null);
    const [attempt, setAttempt] = useState(0);
    const [isOpen, setIsOpen] = useState(false);
    const [loading, setLoading] = useState(false);
    const [saving, setSaving] = useState(false);
    const [document, setDocument] = useState(null);
    const [draft, setDraft] = useState({name: '', code: ''});
    const [error, setError] = useState(null);
    const [latest, setLatest] = useState(null);

    const isInUse = usage?.inUse === true;
    const checkingUsage = usage === null && !usageError;
    const dirty = Boolean(document && (
        draft.name !== document.name ||
        draft.code !== document.code
    ));

    useEffect(() => {
        const controller = new AbortController();

        async function loadUsage() {
            setUsage(null);
            setUsageError(null);

            try {
                const data = await getBehaviourUsage(behaviour.id, {
                    signal: controller.signal,
                });

                if (!controller.signal.aborted) setUsage(data);
            } catch (requestError) {
                if (!controller.signal.aborted) {
                    setUsageError(requestError);
                }
            }
        }

        loadUsage();
        return () => controller.abort();
    }, [behaviour.id, behaviour.version, attempt]);

    useEffect(() => {
        return () => loadController.current?.abort();
    }, []);

    async function openEditor() {
        if (usageError) {
            setAttempt((value) => value + 1);
            return;
        }
        if (checkingUsage || isInUse || pending.current) return;

        loadController.current?.abort();
        const controller = new AbortController();
        loadController.current = controller;

        setIsOpen(true);
        setLoading(true);
        setDocument(null);
        setError(null);
        setLatest(null);

        try {
            const [data, currentUsage] = await Promise.all([
                getBehaviour(behaviour.id, {signal: controller.signal}),
                getBehaviourUsage(behaviour.id, {
                    signal: controller.signal,
                }),
            ]);

            if (controller.signal.aborted) return;

            setDocument(data);
            setDraft({name: data.name, code: data.code});
            setUsage(currentUsage);
        } catch (requestError) {
            if (!controller.signal.aborted) setError(requestError);
        } finally {
            if (!controller.signal.aborted) setLoading(false);
        }
    }

    function closeEditor() {
        if (pending.current) return;
        if (dirty && !window.confirm(DISCARD_MESSAGE)) return;

        loadController.current?.abort();
        setIsOpen(false);
        setError(null);
        setLatest(null);
    }

    function changeDraft(field, value) {
        setDraft((current) => ({...current, [field]: value}));
        setError(null);
    }

    async function save(event) {
        event.preventDefault();

        if (pending.current || !document || isInUse) return;

        if (!draft.name.trim() || !draft.code.trim()) {
            setError(new Error('Completá el nombre y el código.'));
            return;
        }

        pending.current = true;
        setSaving(true);
        setError(null);

        let updated;

        try {
            updated = await updateBehaviour(behaviour.id, {
                name: draft.name,
                code: draft.code,
                expectedVersion: document.version,
            });
        } catch (requestError) {
            setError(requestError);

            if (requestError.code === 'BEHAVIOUR_IN_USE') {
                setUsage({
                    inUse: true,
                    references: requestError.fields ?? {},
                });
            }
            return;
        } finally {
            pending.current = false;
            setSaving(false);
        }

        setDocument(updated);
        setDraft({name: updated.name, code: updated.code});
        setIsOpen(false);
        onUpdated?.(updated);
    }

    async function consultLatest() {
        try {
            const data = await getBehaviour(behaviour.id);
            setLatest(data);
        } catch (requestError) {
            setError(requestError);
        }
    }

    function replaceDraft() {
        if (dirty && !window.confirm(DISCARD_MESSAGE)) return;

        setDocument(latest);
        setDraft({name: latest.name, code: latest.code});
        setLatest(null);
        setError(null);
    }

    async function checkUsageAgain() {
        try {
            const data = await getBehaviourUsage(behaviour.id);
            setUsage(data);
            setError(null);
        } catch (requestError) {
            setError(requestError);
        }
    }

    const referenceDescriptions = Object.values(
        usage?.references ?? {}
    );

    const title = isInUse
        ? `No se puede editar ${behaviour.name}: está en uso. ${
            referenceDescriptions.join('. ')
        }`
        : usageError
            ? 'No se pudo comprobar el uso. Reintentar.'
            : checkingUsage
                ? `Comprobando si se puede editar ${behaviour.name}`
                : `Editar ${behaviour.name}`;

    return (
        <Dialog
            open={isOpen}
            onOpenChange={(open) => {
                if (open) openEditor();
                else closeEditor();
            }}
        >
            {isOpen && <UnsavedChangesGuard dirty={dirty}/>}

            <span title={title}>
                <DialogTrigger
                    render={
                        <Button
                            type="button"
                            variant="ghost"
                            size="icon"
                            disabled={checkingUsage || isInUse}
                            aria-label={title}
                            className="size-10 rounded-xl text-blue-700 hover:bg-blue-50 disabled:text-gray-400"
                        />
                    }
                >
                    {checkingUsage ? (
                        <LoaderCircle
                            className="size-4 animate-spin"
                            aria-hidden="true"
                        />
                    ) : isInUse ? (
                        <PencilOff className="size-4" aria-hidden="true"/>
                    ) : (
                        <Pencil className="size-4" aria-hidden="true"/>
                    )}
                </DialogTrigger>
            </span>

            <DialogContent
                showCloseButton={false}
                className="max-h-[90dvh] overflow-y-auto sm:max-w-5xl"
                aria-busy={loading || saving}
            >
                <DialogHeader>
                    <DialogTitle>Editar comportamiento</DialogTitle>
                    <DialogDescription>
                        Modificá el nombre o el código y guardá los cambios.
                    </DialogDescription>
                </DialogHeader>

                {loading && (
                    <p role="status">Cargando comportamiento…</p>
                )}

                {error && (
                    <div
                        role="alert"
                        className="space-y-2 rounded-lg border border-red-200 bg-red-50 p-3 text-red-800"
                    >
                        <p>
                            {error.status === 401
                                ? 'Iniciá sesión para editar el comportamiento.'
                                : error.message || 'No se pudieron guardar los cambios.'}
                        </p>

                        {error.code !== 'BEHAVIOUR_IN_USE' &&
                            Object.values(error.fields ?? {}).map((message, index) => (
                                <p key={index}>{message}</p>
                            ))
                        }

                        {error.code === 'VERSION_CONFLICT' && (
                            <Button
                                type="button"
                                variant="outline"
                                onClick={consultLatest}
                            >
                                Consultar versión vigente
                            </Button>
                        )}

                        {!document && !loading && (
                            <Button
                                type="button"
                                variant="outline"
                                onClick={openEditor}
                            >
                                Reintentar carga
                            </Button>
                        )}
                    </div>
                )}

                {isInUse && document && (
                    <div className="space-y-2 rounded-lg border bg-amber-50 p-3">
                        <p className="flex items-center gap-2 font-semibold">
                            <PencilOff className="size-4" aria-hidden="true"/>
                            Este comportamiento está en uso.
                        </p>

                        <p>Reemplazalo en sus asignaciones antes de editarlo:</p>

                        <ul className="list-disc pl-5">
                            {Object.entries(usage.references ?? {}).map(
                                ([key, description]) => (
                                    <li key={key}>{description}</li>
                                )
                            )}
                        </ul>

                        <Button
                            type="button"
                            variant="outline"
                            onClick={checkUsageAgain}
                        >
                            Comprobar nuevamente
                        </Button>
                    </div>
                )}

                {document && !loading && (
                    <form
                        id={formId}
                        onSubmit={save}
                        className="space-y-4"
                    >
                        <p className="text-sm text-gray-600">
                            Versión {document.version}
                        </p>

                        <div className="space-y-2">
                            <label htmlFor={`${formId}-name`}>
                                Nombre del comportamiento
                            </label>
                            <input
                                id={`${formId}-name`}
                                value={draft.name}
                                maxLength={50}
                                required
                                readOnly={saving || isInUse}
                                onChange={(event) => {
                                    changeDraft('name', event.target.value);
                                }}
                                className="w-full rounded-lg border p-3"
                            />
                        </div>

                        <BehaviourCodeEditor
                            value={draft.code}
                            onChange={(code) => changeDraft('code', code)}
                            diagnostics={error?.diagnostics ?? []}
                            documentId={behaviour.id}
                            kind={document.kind}
                            readOnly={saving || isInUse}
                        />
                    </form>
                )}

                {latest && (
                    <aside
                        aria-label="Versión vigente del servidor"
                        className="space-y-3 rounded-lg border bg-gray-50 p-3"
                    >
                        <h3 className="font-semibold">
                            {latest.name} — versión {latest.version}
                        </h3>

                        <pre className="max-h-48 overflow-auto whitespace-pre text-sm">
                            <code>{latest.code}</code>
                        </pre>

                        <Button
                            type="button"
                            variant="outline"
                            onClick={replaceDraft}
                        >
                            Reemplazar mi borrador con esta versión
                        </Button>
                    </aside>
                )}

                <DialogFooter>
                    <Button
                        type="button"
                        variant="outline"
                        disabled={saving}
                        onClick={closeEditor}
                    >
                        Cancelar
                    </Button>

                    {document && (
                        <Button
                            type="submit"
                            form={formId}
                            disabled={loading || saving || isInUse}
                        >
                            {saving && (
                                <LoaderCircle
                                    className="size-4 animate-spin"
                                    aria-hidden="true"
                                />
                            )}
                            {saving ? 'Guardando…' : 'Guardar cambios'}
                        </Button>
                    )}
                </DialogFooter>
            </DialogContent>
        </Dialog>
    );
}