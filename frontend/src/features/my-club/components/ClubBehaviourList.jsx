import {useEffect, useRef, useState} from 'react';
import {useNavigate} from 'react-router';
import {LoaderCircle, Play} from 'lucide-react';
import {toast} from 'sonner';
import {Button} from '@/components/ui/button';
import {Card, CardContent, CardDescription, CardHeader, CardTitle} from '@/components/ui/card';
import {Empty, EmptyDescription, EmptyHeader, EmptyTitle} from '@/components/ui/empty';
import {routePath, routes} from '@/routes.js';
import {createBehaviourTestMatch} from '../../behaviours/api.js';
import BehaviourDetailDialog from '../../behaviours/components/BehaviourDetailDialog.jsx';
import BehaviourEdit from '../../behaviours/components/BehaviourEdit.jsx';
import DeleteBehaviourButton from '../../behaviours/components/DeleteBehaviourButton.jsx';
import CreateBehaviourDialog from '../../create-behaviour/CreateBehaviourDialog.jsx';

export default function ClubBehaviourList({behaviours, onCreated, onUpdated, onDeleted}) {
    const navigate = useNavigate();
    const testRequest = useRef(null);
    const [creatingTest, setCreatingTest] = useState(false);

    useEffect(() => () => testRequest.current?.abort(), []);

    function handleCreated(behaviour) {
        onCreated(behaviour);
        toast.success('Comportamiento creado', {description: behaviour.name});
    }

    function handleUpdated(behaviour) {
        onUpdated(behaviour);
        toast.success('Comportamiento actualizado', {description: behaviour.name});
    }

    function handleDeleted(behaviour) {
        onDeleted(behaviour.id);
        toast.success('Comportamiento eliminado', {description: behaviour.name});
    }

    async function handleTest() {
        if (testRequest.current) return;
        const controller = new AbortController();
        testRequest.current = controller;
        setCreatingTest(true);

        try {
            const {matchId} = await createBehaviourTestMatch({signal: controller.signal});
            if (controller.signal.aborted) return;
            toast.success('Partido de prueba creado');
            navigate(routePath(routes.match, {matchId}), {state: {behaviourTest: true}});
        } catch (error) {
            if (!controller.signal.aborted) {
                toast.error('No se pudo iniciar la prueba', {description: error.message});
            }
        } finally {
            testRequest.current = null;
            if (!controller.signal.aborted) setCreatingTest(false);
        }
    }

    return (
        <Card>
            <CardHeader className="flex flex-wrap items-start justify-between gap-3">
                <div className="space-y-1">
                    <CardTitle className="text-lg font-bold">Comportamientos</CardTitle>
                    <CardDescription>Catálogo de comportamientos de tu club.</CardDescription>
                </div>
                <div className="grid w-full gap-2 sm:flex sm:w-auto sm:flex-wrap">
                    <CreateBehaviourDialog onCreated={handleCreated}/>
                    <Button type="button" variant="outline" onClick={handleTest} disabled={creatingTest}>
                        {creatingTest
                            ? <LoaderCircle data-icon="inline-start" className="animate-spin" aria-hidden="true"/>
                            : <Play data-icon="inline-start" aria-hidden="true"/>}
                        {creatingTest ? 'Creando partido…' : 'Probar comportamiento'}
                    </Button>
                </div>
            </CardHeader>
            <CardContent>
                {behaviours.length === 0 ? (
                    <Empty className="border">
                        <EmptyHeader>
                            <EmptyTitle>Sin comportamientos</EmptyTitle>
                            <EmptyDescription>El club todavía no tiene comportamientos.</EmptyDescription>
                        </EmptyHeader>
                    </Empty>
                ) : (
                    <ul className="grid gap-3 sm:grid-cols-2">
                        {behaviours.map((behaviour) => (
                            <li key={behaviour.id} className="min-w-0">
                                <fieldset className="h-full min-w-0 space-y-4 rounded-xl border bg-card p-5 shadow-xs">
                                    <legend className="max-w-full rounded-md border bg-secondary px-3 py-1 text-sm font-semibold text-primary wrap-anywhere">
                                        {behaviour.name}
                                    </legend>
                                    <p className="text-sm text-muted-foreground wrap-anywhere">
                                        {behaviour.description || 'Sin descripción.'}
                                    </p>
                                    <div className="flex flex-wrap items-center justify-between gap-3">
                                        <BehaviourDetailDialog behaviour={behaviour}/>
                                        <div className="flex items-center gap-1">
                                            <BehaviourEdit behaviour={behaviour} onUpdated={handleUpdated}/>
                                            <DeleteBehaviourButton behaviour={behaviour} onDeleted={handleDeleted}/>
                                        </div>
                                    </div>
                                </fieldset>
                            </li>
                        ))}
                    </ul>
                )}
            </CardContent>
        </Card>
    );
}
