import {useEffect, useState} from 'react';
import {Link, useLocation, useNavigate} from 'react-router';
import {Button} from '@/components/ui/button';
import {Card} from '@/components/ui/card';
import {joinFriendlyMatch, listMyFriendlyMatches} from './api';
import {useFriendlyMatches} from './hooks/useFriendlyMatches.js';
import FriendlyMatchSearch from './components/FriendlyMatchSearch.jsx';
import './Matches.css';

const statusLabels = {
    WAITING: 'Esperando rival',
    WAITING_OPPONENT: 'Esperando rival',
    SCHEDULED: 'Programado',
    RUNNING: 'En juego',
    FINISHED: 'Finalizado',
    CANCELLED: 'Cancelado',
};

function formatDate(value) {
    return new Date(value).toLocaleString('es-AR');
}

export default function MatchesPage() {
    const [misPartidos, setMisPartidos] = useState([]);
    const [loading, setLoading] = useState(true);
    const [loadError, setLoadError] = useState('');
    const [joinError, setJoinError] = useState('');
    const [joiningId, setJoiningId] = useState(null);
    const [refresh, setRefresh] = useState(0);
    const search = useFriendlyMatches(refresh);
    const navigate = useNavigate();
    const location = useLocation();
    const returnTo = location.pathname + location.search;

    useEffect(() => {
        const controller = new AbortController();

        async function cargarPartidos() {
            setLoading(true);
            setLoadError('');
            try {
                const propios = await listMyFriendlyMatches(controller.signal);
                if (controller.signal.aborted) return;
                setMisPartidos(propios);
            } catch (error) {
                if (!controller.signal.aborted) setLoadError(error.message);
            } finally {
                if (!controller.signal.aborted) setLoading(false);
            }
        }

        cargarPartidos();
        return () => controller.abort();
    }, [refresh]);

    async function handleJoinMatch(matchId) {
        if (joiningId !== null) return;
        setJoiningId(matchId);
        setJoinError('');
        try {
            const response = await joinFriendlyMatch(matchId);
            navigate('/partidos/' + response.matchId, {state: {returnTo}});
        } catch (error) {
            setJoinError(error.message || 'No se pudo completar la inscripción al partido.');
            setRefresh((value) => value + 1);
        } finally {
            setJoiningId(null);
        }
    }

    return (
        <main className="Friendly-Matches">
            <Card className="main-card">
                <h1 className="page-title">Amistosos</h1>
                <Button
                    variant="outline"
                    disabled={loading || search.loading || joiningId !== null}
                    onClick={() => setRefresh((value) => value + 1)}
                >
                    {loadError ? 'Reintentar' : 'Actualizar'}
                </Button>
                {loading && <p role="status">Cargando partidos…</p>}
                {loadError && <p role="alert">{loadError}</p>}
                {joinError && <p role="alert">{joinError}</p>}

                {!loading && !loadError && (
                    <>
                        <section className="matches-section" aria-labelledby="my-matches-title">
                            <h2 id="my-matches-title">Mis amistosos</h2>
                            {misPartidos.length === 0 && (
                                <p role="status">Todavía no creaste ni te uniste a un amistoso.</p>
                            )}
                            <div className="container">
                                {misPartidos.map((partido) => (
                                    <div key={partido.matchId} className="match-box">
                                        <div className="match-details">
                                            <span className="match-title">
                                                {partido.creatorClubName} vs. {partido.visitorClubName ?? 'Esperando rival'}
                                            </span>
                                            <span className="match-date">{formatDate(partido.startDateTime)}</span>
                                            <span className="match-date">
                                                {statusLabels[partido.status] ?? partido.status}
                                                {' · '}{partido.isCreator ? 'Creado por tu club' : 'Tu club es visitante'}
                                            </span>
                                        </div>
                                        <Link
                                            className="join-button"
                                            to={`/partidos/${partido.matchId}`}
                                            state={{returnTo}}
                                            aria-label={`Ver partido ${partido.matchId}`}
                                        >
                                            Ver partido
                                        </Link>
                                    </div>
                                ))}
                            </div>
                        </section>

                    </>
                )}
                <section className="matches-section" aria-labelledby="available-matches-title">
                    <h2 id="available-matches-title">Amistosos disponibles</h2>
                    <FriendlyMatchSearch search={search} disabled={joiningId !== null}/>
                    {search.loading && <p role="status">Buscando amistosos…</p>}
                    {search.error && <p role="alert">{search.error}
                        <Button variant="outline" onClick={search.reload}>Reintentar búsqueda</Button>
                    </p>}
                    {!search.loading && !search.error && search.result.items.length === 0 && (
                        <p role="status">{search.result.total > 0 ? 'No hay partidos en esta página.'
                            : search.creatorName ? `No se encontraron amistosos para "${search.creatorName}".`
                                : 'No hay partidos disponibles.'}</p>
                    )}
                    <div className="container">
                        {!search.loading && !search.error && search.result.items.map((partido) => (
                            <div key={partido.matchId} className="match-box">
                                <div className="match-details">
                                    <span className="match-title">{partido.creatorClubName}</span>
                                    <span className="match-date">{formatDate(partido.startDateTime)}</span>
                                </div>
                                <Button
                                    className="join-button"
                                    disabled={joiningId !== null}
                                    onClick={() => handleJoinMatch(partido.matchId)}
                                >
                                    {joiningId === partido.matchId ? 'Uniéndose…' : 'Unirse'}
                                </Button>
                            </div>
                        ))}
                    </div>
                </section>
            </Card>
        </main>
    );
}
