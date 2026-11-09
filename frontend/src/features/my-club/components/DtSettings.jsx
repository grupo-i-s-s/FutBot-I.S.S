import { useEffect, useId, useState } from 'react';
import { ClipboardList, Plus } from 'lucide-react';
import { Link } from 'react-router';
import { Button, buttonVariants } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Switch } from '@/components/ui/switch';
import { listDtBehaviours, updateDtSettings } from '../api';

function errorMessage(error, fallback) {
    return Object.values(error.fields ?? {}).join(' ') || error.message || fallback;
}

export default function DtSettings({ dt }) {
    const formId = useId();
    const [behaviours, setBehaviours] = useState([]);
    const [isActive, setIsActive] = useState(dt?.isActive ?? false);
    const [selectedId, setSelectedId] = useState(String(dt?.activeBehaviourId ?? ''));
    const [attempt, setAttempt] = useState(0);
    const [loading, setLoading] = useState(true);
    const [loadError, setLoadError] = useState('');
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState('');
    const [notice, setNotice] = useState('');

    useEffect(() => {
        const controller = new AbortController();
        listDtBehaviours({ signal: controller.signal }).then(({ items }) => {
            if (!controller.signal.aborted) setBehaviours(items);
        }).catch(cause => {
            if (!controller.signal.aborted) {
                setLoadError(errorMessage(cause, 'No se pudieron cargar los comportamientos del DT.'));
            }
        }).finally(() => {
            if (!controller.signal.aborted) setLoading(false);
        });
        return () => controller.abort();
    }, [attempt]);

    const selected = behaviours.some(behaviour => String(behaviour.id) === selectedId);

    async function save(event) {
        event.preventDefault();
        if (loading || loadError || saving || (isActive && !selected)) return;
        setSaving(true);
        setError('');
        setNotice('');
        try {
            const updated = await updateDtSettings({
                isActive,
                activeBehaviourId: selected ? Number(selectedId) : null,
            });
            setIsActive(updated.isActive);
            setSelectedId(String(updated.activeBehaviourId ?? ''));
            setNotice('Configuración del DT guardada.');
        } catch (cause) {
            setError(errorMessage(cause, 'No se pudo guardar el DT.'));
        } finally {
            setSaving(false);
        }
    }

    return (
        <Card>
            <CardHeader>
                <CardTitle className="flex items-center gap-2 text-lg font-bold">
                    <ClipboardList className="size-5" aria-hidden="true" />
                    Director técnico
                </CardTitle>
                <CardDescription>
                    Cuando lo activás, el DT dirige a tu equipo desde el inicio de cada partido.
                    Puede cambiar a comportamientos predeterminados y hacer sustituciones durante las pausas.
                </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
                {loading && <p role="status">Cargando comportamientos del DT…</p>}
                {loadError && (
                    <div className="space-y-2">
                        <p role="alert" className="text-destructive">{loadError}</p>
                        <Button type="button" variant="outline" onClick={() => {
                            setLoading(true);
                            setLoadError('');
                            setAttempt(value => value + 1);
                        }}>Reintentar</Button>
                    </div>
                )}
                {!loading && !loadError && (
                    <>
                        <form aria-label="Configuración del DT" onSubmit={save}>
                            <fieldset disabled={saving} className="space-y-3">
                                <div className="flex items-center justify-between gap-4">
                                    <label htmlFor={`${formId}-active`} className="font-medium">
                                        Activar DT para próximos partidos
                                    </label>
                                    <Switch id={`${formId}-active`} checked={isActive} onCheckedChange={setIsActive} />
                                </div>
                                <div className="space-y-1">
                                    <label htmlFor={`${formId}-behaviour`} className="font-medium">Comportamiento del DT</label>
                                    <select id={`${formId}-behaviour`}
                                            className="w-full rounded-md border border-input bg-background p-2"
                                            value={selected ? selectedId : ''}
                                            onChange={event => setSelectedId(event.target.value)}>
                                        <option value="" disabled>Elegí un comportamiento</option>
                                        {behaviours.map(behaviour => (
                                            <option key={behaviour.id} value={behaviour.id}>{behaviour.name}</option>
                                        ))}
                                    </select>
                                </div>
                                <Button type="submit" disabled={isActive && !selected}>
                                    {saving ? 'Guardando…' : 'Guardar DT'}
                                </Button>
                            </fieldset>
                        </form>
                        {error && <p role="alert" className="text-destructive">{error}</p>}
                        {notice && <p role="status">{notice}</p>}
                    </>
                )}
                <Link to="/crear-comportamiento-dt" className={buttonVariants({ variant: 'outline' })}>
                    <Plus className="size-4" aria-hidden="true" />
                    Crear comportamiento del DT
                </Link>
            </CardContent>
        </Card>
    );
}
