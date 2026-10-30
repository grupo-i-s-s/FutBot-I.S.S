import {useEffect, useState} from 'react';
import {Link, useNavigate, useParams} from 'react-router';
import {abandonarLobby, obtenerLobby} from './api.js';
import './CreateLeagueLobby.css';

export function LeagueLobby() {

    const {id} = useParams();
    const [lobby, setLobby] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [refresh, setRefresh] = useState(0);
    const navigate = useNavigate();


    useEffect(() => {
        const controller = new AbortController();

        async function cargarLobby() {
            setLoading(true);
            setError(null);

            try {
                const data = await obtenerLobby(id, controller.signal);

                if (!controller.signal.aborted) {
                    setLobby(data);
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

    async function handleLeaveLeague() {
        const confirmed = window.confirm('¿Estás seguro de que querés abandonar esta liga?');
        if (!confirmed) return;
        try {
            await abandonarLobby(id);
            navigate('/mi-club');
        } catch (err) {
            alert('No se pudo abandonar la liga');
        }
    }

    if (loading) {
        return (
            <p className="lobby-status" role="status">
                Cargando liga…
            </p>
        );
    }

    if (error) {
        return (
            <div className="lobby-container">
                <p className="lobby-status error" role="alert">
                    {error.status === 404
                        ? 'La liga no existe.'
                        : error.message}
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

    const frequencies = {
        CONTINUOUS: 'Seguidas',
        DAILY: 'Diarias',
        WEEKLY: 'Semanales',
    };
    return (
        <div className="lobby-container">
            <header className="lobby-header">
                <h1>Liga
                    <strong> {lobby.name}</strong>
                </h1>
            </header>

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
                                <span className="player-name">{club.name}</span>

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
                    onClick={() => setRefresh((value) => value + 1)}
                >
                    Actualizar
                </button>
            </div>

            <div className="leave-league">
                <button
                    type="button"
                    onClick={handleLeaveLeague}
                >
                    Abandonar Liga
                </button>
            </div>
        </div>
    );
}

export default LeagueLobby;