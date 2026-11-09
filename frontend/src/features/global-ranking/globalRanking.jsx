import {useEffect, useState} from 'react';
import {Button} from '@/components/ui/button';
import ClubAvatar from '../my-club/components/ClubAvatar.jsx';
import {getGlobalRanking} from './api.js';

const stats = [
    ['points', 'Pts'], ['played', 'PJ'], ['wins', 'PG'], ['draws', 'PE'],
    ['losses', 'PP'], ['goalsFor', 'GF'], ['goalsAgainst', 'GC'], ['dg', 'DG'],
];

export default function GlobalRanking() {
    const [page, setPage] = useState(1);
    const [attempt, setAttempt] = useState(0);
    const [result, setResult] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const controller = new AbortController();
        setLoading(true);
        setError(null);

        getGlobalRanking(page, controller.signal)
            .then((data) => {
                if (!controller.signal.aborted) setResult(data);
            })
            .catch((requestError) => {
                if (!controller.signal.aborted) setError(requestError);
            })
            .finally(() => {
                if (!controller.signal.aborted) setLoading(false);
            });

        return () => controller.abort();
    }, [page, attempt]);

    return (
        <main className="mx-auto w-full max-w-6xl px-4 py-8">
            <section className="space-y-4 rounded-xl border bg-white p-6" aria-busy={loading}>
                <h2 className="text-2xl font-semibold">Ranking Global</h2>
                {loading && <p role="status">Cargando ranking global…</p>}
                {error && (
                    <div role="alert" className="space-y-2">
                        <p>No se pudo cargar el ranking global.</p>
                        <Button type="button" variant="outline" onClick={() => setAttempt(attempt + 1)}>
                            Reintentar
                        </Button>
                    </div>
                )}
                {!loading && !error && result && (
                    <>
                        {result.items.length > 0 ? (
                            <div className="overflow-x-auto">
                                <table className="w-full whitespace-nowrap text-center">
                                    <thead className="bg-muted">
                                        <tr>
                                            <th scope="col" className="p-2">#</th>
                                            <th scope="col" className="p-2 text-left">Club</th>
                                            {stats.map(([field, label]) => (
                                                <th key={field} scope="col" className="p-2">{label}</th>
                                            ))}
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {result.items.map((club) => (
                                            <tr key={club.id} className="border-b">
                                                <td className="p-2">{club.position}</td>
                                                <th scope="row" className="p-2 text-left">
                                                    <span className="flex items-center gap-2">
                                                        <ClubAvatar avatar={club.avatar} clubName={club.name} size="md"/>
                                                        {club.name}
                                                    </span>
                                                </th>
                                                {stats.map(([field]) => (
                                                    <td key={field} className="p-2">{club[field]}</td>
                                                ))}
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        ) : (
                            <p role="status">No hay clubes para mostrar en esta página.</p>
                        )}
                        {(result.totalPages > 1 || page > 1) && (
                            <nav className="flex items-center justify-end gap-3" aria-label="Paginación del ranking">
                                <Button type="button" variant="outline" disabled={page <= 1}
                                        onClick={() => setPage(page - 1)}>
                                    Anterior
                                </Button>
                                <span aria-live="polite">Página {result.page} de {result.totalPages}</span>
                                <Button type="button" variant="outline" disabled={!result.hasNext}
                                        onClick={() => setPage(page + 1)}>
                                    Siguiente
                                </Button>
                            </nav>
                        )}
                    </>
                )}
            </section>
        </main>
    );
}
