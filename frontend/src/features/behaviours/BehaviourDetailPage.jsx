import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router';
import { getBehaviour } from './api';
import './BehaviourDetailPage.css';
import DeleteBehaviourButton from './components/DeleteBehaviourButton';

export default function BehaviourDetailPage() {
    const { behaviourId } = useParams();

    const [behaviour, setBehaviour] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [attempt, setAttempt] = useState(0);
    const navigate = useNavigate();

    useEffect(() => {
        const controller = new AbortController();

        async function loadBehaviour() {
            setLoading(true);
            setError('');
            setBehaviour(null);

            try {
                const data = await getBehaviour(behaviourId, {
                    signal: controller.signal,
                });

                if (!controller.signal.aborted) {
                    setBehaviour(data);
                }
            } catch (err) {
                if (controller.signal.aborted) return;

                setError(
                    err.status === 401
                        ? 'Iniciá sesión para consultar el comportamiento.'
                        : err.message || 'No se pudo cargar el comportamiento.'
                );
            } finally {
                if (!controller.signal.aborted) {
                    setLoading(false);
                }
            }
        }

        loadBehaviour();

        return () => controller.abort();
    }, [behaviourId, attempt]);

    return (
        <main className="behaviour-detail-page">
            <section className="behaviour-detail-card" aria-busy={loading}>
                <h1 className="behaviour-detail-title">
                    Detalle de comportamiento
                </h1>

                {loading && (
                    <p role="status">Cargando comportamiento…</p>
                )}

                {error && (
                    <div>
                        <p role="alert" className="behaviour-detail-error">
                            {error}
                        </p>

                        <button
                            type="button"
                            className="behaviour-detail-button"
                            onClick={() => setAttempt(attempt + 1)}
                        >
                            Reintentar
                        </button>
                    </div>
                )}

                {behaviour && (
                    <>
                        <h2 className="behaviour-detail-name">
                            {behaviour.name}
                        </h2>

                        <DeleteBehaviourButton
                            behaviour={behaviour}
                            onDeleted={(deletedBehaviour) => {
                                navigate('/behaviours', {
                                    replace: true,
                                    state: {
                                        notice: `El comportamiento “${deletedBehaviour.name}” se eliminó correctamente.`,
                                    },
                                });
                            }}
                        />

                        <p className="behaviour-detail-description">
                            Código del comportamiento. Solo lectura.
                        </p>

                        <pre className="behaviour-detail-code">
                            <code>{behaviour.code}</code>
                        </pre>
                    </>
                )}

            </section>
        </main>
    );
}
