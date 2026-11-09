import {useEffect, useState} from 'react';
import {Link, useParams} from 'react-router';
import ClubAvatar from '../my-club/components/ClubAvatar';
import {getClubProfile} from './api';

const PAGE_CLASSES = 'mx-auto max-w-4xl space-y-6 px-4 py-8';
const SECTION_CLASSES = 'space-y-4 rounded-xl border bg-card p-6';

const STAT_FIELDS = [
    ['played', 'Partidos jugados'],
    ['wins', 'Victorias'],
    ['draws', 'Empates'],
    ['losses', 'Derrotas'],
];

export default function ClubProfilePage() {
    const {clubId} = useParams();

    return <ClubProfileContent key={clubId} clubId={clubId}/>;
}

function ClubProfileContent({clubId}) {
    const [attempt, setAttempt] = useState(0);
    const [state, setState] = useState({
        status: 'loading',
        club: null,
        error: null,
    });

    useEffect(() => {
        const controller = new AbortController();
        let active = true;

        setState({
            status: 'loading',
            club: null,
            error: null,
        });

        async function loadClub() {
            try {
                const club = await getClubProfile(clubId, {
                    signal: controller.signal,
                });

                if (active) {
                    setState({
                        status: 'success',
                        club,
                        error: null,
                    });
                }
            } catch (error) {
                if (active && error.name !== 'AbortError') {
                    setState({
                        status: 'error',
                        club: null,
                        error,
                    });
                }
            }
        }

        loadClub();

        return () => {
            active = false;
            controller.abort();
        };
    }, [clubId, attempt]);

    function handleRetry() {
        setState({
            status: 'loading',
            club: null,
            error: null,
        });
        setAttempt((value) => value + 1);
    }

    if (state.status === 'loading') {
        return (
            <main className={PAGE_CLASSES} aria-busy="true">
                <p role="status">Cargando club…</p>
            </main>
        );
    }

    if (state.status === 'error') {
        const {error} = state;
        const isNotFound = error.status === 404;
        const isSessionError = error.status === 401;

        let message = error.message || 'Intentá nuevamente.';

        if (isNotFound) {
            message = 'El club solicitado no existe.';
        } else if (isSessionError) {
            message = 'Iniciá sesión para consultar este club.';
        } else if (error.status === 0) {
            message = 'No se pudo conectar con el servidor.';
        }

        return (
            <main className={PAGE_CLASSES}>
                <div role="alert" className={SECTION_CLASSES}>
                    <h1 className="text-2xl font-bold">
                        {isNotFound
                            ? 'Club no encontrado'
                            : 'No se pudo cargar el club'}
                    </h1>

                    <p>{message}</p>

                    {isSessionError ? (
                        <Link to="/login" className="underline">
                            Iniciar sesión
                        </Link>
                    ) : !isNotFound && (
                        <button
                            type="button"
                            onClick={handleRetry}
                            className="rounded-lg border px-4 py-2"
                        >
                            Reintentar
                        </button>
                    )}

                    <Link to="/clubes" className="block underline">
                        Volver a clubes
                    </Link>
                </div>
            </main>
        );
    }

    const {club} = state;

    return (
        <main className={PAGE_CLASSES}>
            <header className={`${SECTION_CLASSES} flex items-center gap-4`}>
                <ClubAvatar
                    avatar={club.avatar}
                    clubName={club.name}
                />

                <div className="min-w-0">
                    <p className="text-sm text-muted-foreground">
                        Perfil público
                    </p>
                    <h1 className="break-words text-3xl font-bold">
                        {club.name}
                    </h1>
                </div>
            </header>

            <section
                aria-labelledby="club-stats-title"
                className={SECTION_CLASSES}
            >
                <h2 id="club-stats-title" className="text-xl font-bold">
                    Estadísticas
                </h2>

                <dl className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                    {STAT_FIELDS.map(([field, label]) => (
                        <div key={field}>
                            <dt className="text-sm text-muted-foreground">
                                {label}
                            </dt>
                            <dd className="text-2xl font-bold">
                                {club.stats[field]}
                            </dd>
                        </div>
                    ))}
                </dl>
            </section>

            <section
                aria-labelledby="club-ranking-title"
                className={SECTION_CLASSES}
            >
                <h2 id="club-ranking-title" className="text-xl font-bold">
                    Ranking global
                </h2>

                <p className="text-sm text-muted-foreground">
                    Calculado únicamente con resultados de ligas públicas.
                </p>

                <dl className="grid grid-cols-2 gap-4">
                    <div>
                        <dt>Posición</dt>
                        <dd className="text-2xl font-bold">
                            {club.ranking.position}
                        </dd>
                    </div>

                    <div>
                        <dt>Puntos</dt>
                        <dd className="text-2xl font-bold">
                            {club.ranking.points}
                        </dd>
                    </div>
                </dl>
            </section>

            <section
                aria-labelledby="club-players-title"
                className={SECTION_CLASSES}
            >
                <h2 id="club-players-title" className="text-xl font-bold">
                    Plantilla
                </h2>

                {club.players.length === 0 ? (
                    <p>Este club todavía no tiene jugadores.</p>
                ) : (
                    <ul className="divide-y">
                        {club.players.map((player) => (
                            <li key={player.id} className="py-3">
                                {player.name}
                            </li>
                        ))}
                    </ul>
                )}
            </section>

            <Link to="/clubes" className="block underline">
                Volver a clubes
            </Link>
        </main>
    );
}
