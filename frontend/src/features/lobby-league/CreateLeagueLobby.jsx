import { useEffect, useRef, useState } from 'react';
import { Link, Navigate, useNavigate, useParams } from 'react-router';
import { abandonarLobby, iniciarLiga, obtenerIdentidad, obtenerLobby } from './api.js';
import LeagueRanking from './LeagueRanking.jsx';
import LeagueFixture from './LeagueFixture.jsx';
import './CreateLeagueLobby.css';

export function LeagueLobby() {
    const { id } = useParams();
    return <LeagueLobbyContent key={id} id={id} />;
}

function LeagueLobbyContent({ id }) {
    const [lobby, setLobby] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [refresh, setRefresh] = useState(0);
    const [tab, setTab] = useState('lobby');
    const [clubId, setClubId] = useState(null);
    const [starting, setStarting] = useState(false);
    const [startError, setStartError] = useState('');
    const startingRef = useRef(false);
    const navigate = useNavigate();


    useEffect(() => {
        const controller = new AbortController();

        async function cargarLobby() {
            setLoading(true);
            setError(null);

            try {
                const [data, identity] = await Promise.all([
                    obtenerLobby(id, controller.signal),
                    obtenerIdentidad(controller.signal),
                ]);

                if (!controller.signal.aborted) {
                    setLobby(data);
                    setClubId(identity.clubId);
                }
            } catch (err) {
                if (!controller.signal.aborted) {
                    setError(err);
                }
            } finally {
                if (!controller.signal.aborted) {
                    setLoading(false);
                }
            }
        }

        cargarLobby();

        return () => controller.abort();
    }, [id, refresh]);

    useEffect(() => {
        function actualizar(event) {
            if (event.type === 'league-updated' && event.detail?.leagueId != null
                && String(event.detail.leagueId) !== id) return;
            if (!startingRef.current) setRefresh(value => value + 1);
        }
        window.addEventListener('focus', actualizar);
        window.addEventListener('league-updated', actualizar);
        return () => {
            window.removeEventListener('focus', actualizar);
            window.removeEventListener('league-updated', actualizar);
        };
    }, [id]);

    useEffect(() => {
        if (!['open', 'running'].includes(lobby?.status)) return;
        const timer = window.setInterval(() => {
            if (document.visibilityState === 'visible' && !startingRef.current) {
                setRefresh(value => value + 1);
            }
        }, 10000);
        return () => window.clearInterval(timer);
    }, [lobby?.status]);

    async function handleStartLeague() {
        if (startingRef.current) return;
        if (!window.confirm('Al iniciar se cierran las inscripciones y quedan programados los partidos. ¿Querés continuar?')) return;
        startingRef.current = true;
        setStarting(true);
        setStartError('');
        try {
            await iniciarLiga(id);
            setLobby(await obtenerLobby(id));
        } catch (err) {
            setStartError(err.message);
        } finally {
            startingRef.current = false;
            setStarting(false);
        }
    }

    async function handleLeaveLeague() {
        const isCreator = clubId === lobby?.creatorClubId;
        const message = isCreator
            ? '¿Seguro que querés cancelar esta liga? Esta acción no se puede deshacer.'
            : '¿Estás seguro de que querés abandonar esta liga?';

        if (!window.confirm(message)) return;

        try {
            await abandonarLobby(id);

            if (isCreator) {
                navigate('/home', {
                    replace: true,
                    state: { notice: 'La liga se ha eliminado.' },
                });
            } else {
                navigate('/mi-club');
            }
        } catch (err) {
            alert(err.message || 'No se pudo abandonar la liga');
        }
    }

    if (loading && !lobby) {
        return (
            <p className="lobby-status" role="status">
                Cargando liga…
            </p>
        );
    }

    if (error?.status === 404) {
        return <Navigate to="/liga-cancelada" replace />;
    }

    if (error && !lobby) {
        return (
            <div className="lobby-container">
                <p className="lobby-status error" role="alert">
                    {error.message}
                </p>

                {error.status === 401 ? (
                    <Link to="/login">Iniciar sesión</Link>
                ) : (
                    <button
                        type="button"
                        onClick={() => setRefresh((value) => value + 1)}
                    >
                        Reintentar
                    </button>
                )}
            </div>
        );
    }

    const started = lobby.status === 'running' || lobby.status === 'finished';
    return (
        <div className="lobby-container">
            <header className="lobby-header">
                <h1>Liga
                    <strong> {lobby.name}</strong>
                </h1>
                <span>{{ open: 'Abierta', running: 'En curso', finished: 'Finalizada', cancelled: 'Cancelada' }[lobby.status]}</span>
            </header>

            {error && <p role="alert">{error.message}</p>}

            <div className="lobby-tabs">
                <button className={tab === 'lobby' ? 'active' : ''} onClick={() => setTab('lobby')}>Lobby</button>
                <button className={tab === 'ranking' ? 'active' : ''} onClick={() => setTab('ranking')}>Ranking</button>
            </div>

            <div hidden={tab !== 'lobby'}>
                <div className="lobby-card">
                    <h2>Detalles del Lobby</h2>
                    <div className="info-grid">
                        <div className="info-item">
                            <span>Tipo:</span>
                            <strong>{lobby.isPrivate ? 'Privada' : 'Pública'}</strong>
                        </div>

                        <div className="info-item">
                            <span>Mínimo de clubes:</span>
                            <strong>{lobby.minTeams}</strong>
                        </div>

                        <div className="info-item">
                            <span>Cupos restantes:</span>
                            <strong>{lobby.remainingSlots}</strong>
                        </div>
                    </div>
                </div>

                {lobby.status === 'open' && clubId === lobby.creatorClubId && (
                    <div className="lobby-card">
                        <p>Clubes inscriptos: {lobby.registeredTeams}. Mínimo para iniciar: {lobby.minTeams}.</p>
                        <button type="button" onClick={handleStartLeague}
                            disabled={starting || loading || lobby.registeredTeams < lobby.minTeams}>
                            {starting ? 'Iniciando…' : 'Iniciar liga'}
                        </button>
                        {startError && <p role="alert">{startError}</p>}
                    </div>
                )}

                {started && (
                    <LeagueFixture key={id} id={id} clubId={clubId} clubs={lobby.clubs}
                        leagueStatus={lobby.status} isRegistered={lobby.isRegistered}
                        refresh={refresh} onRefresh={() => setRefresh(value => value + 1)} />
                )}

                <div className="lobby-card">
                    <h2>
                        Clubes inscriptos ({lobby.registeredTeams}/{lobby.maxTeams})
                    </h2>

                    <p>
                        {lobby.isRegistered
                            ? 'Tu club está inscripto.'
                            : 'Tu club no está inscripto.'}
                    </p>

                    <div className="player-list">
                        {lobby.clubs.length === 0 ? (
                            <p className="empty-players">
                                Todavía no hay clubes inscriptos.
                            </p>
                        ) : (
                            lobby.clubs.map((club) => (
                                <div className="player-item" key={club.id}>
                                    <Link to={`/club/${club.id}`} className="player-name">
                                        {club.name}
                                    </Link>

                                    {club.id === lobby.creatorClub?.id && (
                                        <span className="host-badge">Creador</span>
                                    )}
                                </div>
                            ))
                        )}
                    </div>
                </div>

                <div className="lobby-actions">
                    <button
                        type="button"
                        disabled={loading || starting}
                        onClick={() => setRefresh((value) => value + 1)}
                    >
                        Actualizar
                    </button>
                </div>

                {lobby.status === 'open' && lobby.isRegistered && <div className="leave-league">
                    <button
                        type="button"
                        onClick={handleLeaveLeague}
                    >
                        {clubId === lobby.creatorClubId ? 'Cancelar' : 'Abandonar'}
                    </button>
                </div>}
            </div>
            {tab === 'ranking' && <LeagueRanking key={refresh} leagueId={id} />}
        </div>
    );
}

export default LeagueLobby;
