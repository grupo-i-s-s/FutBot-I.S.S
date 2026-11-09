import React, { useEffect, useState } from 'react';
import { fetchBehaviours } from '../services/behavioursApi';
import { buttonVariants } from '@/components/ui/button';
import { Plus } from 'lucide-react';
import DeleteBehaviourButton from './DeleteBehaviourButton';
import { Link, useLocation, useNavigate } from 'react-router';
import { createBehaviourTestMatch } from '../api.js';
import BehaviourEdit from './BehaviourEdit';

export default function BehaviourList() {
    const [behaviours, setBehaviours] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const location = useLocation();
    const [notice, setNotice] = useState(location.state?.notice ?? '');
    const navigate = useNavigate();
    const [creatingTest, setCreatingTest] = useState(false);
    const [testError, setTestError] = useState('');

    const loadBehaviours = async () => {
        setLoading(true);
        setError(null);
        try {
            const data = await fetchBehaviours();
            setBehaviours(data);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    async function handleTestBehaviours() {
        if (creatingTest) return;

        setCreatingTest(true);
        setTestError('');

        try {
            const match = await createBehaviourTestMatch();
            navigate(`/partidos/${match.matchId}`, { replace: true });
        } catch (error) {
            setTestError(error.message || 'No se pudo crear el partido de prueba.');
        } finally {
            setCreatingTest(false);
        }
    }

    useEffect(() => {
        loadBehaviours();
    }, []);

    if (loading) {
        return <div className="p-6 text-center text-gray-600">Cargando catálogo de comportamientos...</div>;
    }

    if (error) {
        return (
            <div className="p-6 text-center text-red-600">
                <p className="mb-4">{error}</p>
                <button
                    onClick={loadBehaviours}
                    className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                >
                    Reintentar
                </button>
                {testError && <p role="alert">{testError}</p>}
            </div>
        );
    }

    function handleUpdated(updatedBehaviour) {
    setBehaviours((current) =>
        current.map((item) =>
            item.id === updatedBehaviour.id
                ? {...item, ...updatedBehaviour}
                : item
        )
    );

    setNotice(
        `El comportamiento “${updatedBehaviour.name}” se actualizó correctamente. ` +
        `Versión ${updatedBehaviour.version}.`
    );
}

    function handleDeleted(deletedBehaviour) {
        setBehaviours((current) =>
            current.filter((item) => item.id !== deletedBehaviour.id)
        );
        setNotice(`El comportamiento “${deletedBehaviour.name}” se eliminó correctamente.`);
    }

    return (
        <div className="max-w-4xl mx-auto p-6">
            <h2 className="text-2xl font-bold mb-6 text-gray-800">Catálogo de Comportamientos</h2>

            {notice && (
                <p role="status" className="mb-4 rounded-xl border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">
                    {notice}
                </p>
            )}

            <div className="mb-6 flex justify-between items-center gap-4">
                <Link to="/mi-club" className={buttonVariants({ size: 'sm' })}>
                    Volver a Mi Club
                </Link>
                <div className="flex gap-2">
                    <Link to="/crear-comportamiento" className={buttonVariants({ size: 'sm' })}>
                        <Plus className="size-4" aria-hidden="true" />
                        Crear nuevo comportamiento
                    </Link>
                    <button
                        type="button"
                        className={buttonVariants({ size: 'sm' })}
                        onClick={handleTestBehaviours}
                        disabled={creatingTest}
                    >
                        {creatingTest ? 'Creando partido...' : 'Probar comportamientos'}
                    </button>
                </div>
            </div>

            {behaviours.length === 0 && (
                <p className="py-6 text-center text-gray-500">
                    No hay comportamientos disponibles en este momento.
                </p>
            )}

            <ul className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
                {behaviours.map((behaviour) => (
                    <li key={behaviour.id}
                        className="border p-4 rounded-lg shadow-sm bg-white flex flex-col justify-between">
                        <div>
                            <div className="flex justify-between items-start mb-2">
                                <h3 className="text-lg font-semibold text-gray-900">{behaviour.name}</h3>
                                {behaviour.isDefault && (
                                    <span className="bg-green-100 text-green-800 text-xs px-2 py-1 rounded font-medium">
                                        Default
                                    </span>
                                )}
                            </div>
                            <p className="text-gray-600 text-sm mb-4">{behaviour.description || 'Sin descripción.'}</p>
                        </div>
                        <div className="mt-2 flex items-center justify-between gap-3">
                            <a
                                href={`/behaviours/${behaviour.id}`}
                                className="text-blue-600 hover:underline text-sm font-medium"
                            >
                                Ver detalle &rarr;
                            </a>

                            <div className="flex items-center gap-1">
                                <BehaviourEdit
                                    behaviour={behaviour}
                                    onUpdated={handleUpdated}
                                />
                            
                                <DeleteBehaviourButton
                                    behaviour={behaviour}
                                    onDeleted={handleDeleted}
                                />
                            </div>
                        </div>
                    </li>
                ))}
            </ul>
        </div>
    );
}
