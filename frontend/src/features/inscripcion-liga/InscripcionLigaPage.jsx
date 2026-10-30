import {useEffect, useState} from 'react';
import {Link, useNavigate, useParams, useSearchParams} from 'react-router';
import {Alert, AlertDescription, AlertTitle} from '@/components/ui/alert';
import {Button} from '@/components/ui/button';
import {Card, CardContent, CardDescription, CardHeader, CardTitle,} from '@/components/ui/card';
import {getDefaultTeam, getLeagueLobby, joinLeague,} from './api.js';

export default function InscripcionLigaPage({league: suppliedLeague} = {}) {
    const {id} = useParams();
    const [searchParams] = useSearchParams();
    const leagueId = id || searchParams.get('leagueId');
    const navigate = useNavigate();
    const [league, setLeague] = useState(suppliedLeague || null);
    const [team, setTeam] = useState(null);
    const [loading, setLoading] = useState(true);
    const [joining, setJoining] = useState(false);
    const [error, setError] = useState('');
    const [accessCode, setAccessCode] = useState('');
    const needsAccessCode = Boolean(league?.requiresAccessCode || league?.isPrivate || league?.type === 'PRIVATE');

    useEffect(() => {
        const controller = new AbortController();

        async function loadTeam() {
            setLeague(suppliedLeague || null);
            setTeam(null);
            setAccessCode('');
            if (!suppliedLeague && !leagueId) {
                setLoading(false);
                return;
            }
            try {
                setLoading(true);
                setError('');
                const [data, selectedLeague] = await Promise.all([
                    getDefaultTeam({signal: controller.signal}),
                    suppliedLeague || getLeagueLobby(leagueId, {signal: controller.signal}),
                ]);
                if (!controller.signal.aborted) {
                    setTeam(data);
                    setLeague(selectedLeague);
                }
            } catch (err) {
                if (!controller.signal.aborted) {
                    setError(err?.message ?? 'No se pudo cargar la liga o tu equipo.');
                }
            } finally {
                if (!controller.signal.aborted) setLoading(false);
            }
        }

        loadTeam();
        return () => controller.abort();
    }, [leagueId, suppliedLeague]);

    async function handleJoin() {
        if (joining || !league || !team) return;

        setError('');

        try {
            setJoining(true);
            setError('');

            await joinLeague(
                league.id,
                team.clubId,
                team.lineUp,
                needsAccessCode ? accessCode : undefined
            );
            navigate(`/leagues/${league.id}/lobby`);
        } catch (err) {
            if (err?.status === 409) {
                setError(
                    err.message ||
                    'No hay cupos disponibles, el código es incorrecto o el club ya está inscripto.'
                );
            } else if (err?.status === 400) {
                setError(
                    err.message ||
                    'El equipo no es válido para esta liga.'
                );
            } else {
                setError(
                    err?.message ||
                    'No se pudo completar la inscripción.'
                );
            }
        } finally {
            setJoining(false);
        }
    }

    if (loading) {
        return <p role="status">Cargando la liga y tu equipo...</p>;
    }

    if (!league) {
        return (
            <Alert variant="destructive">
                <AlertTitle>{error ? 'No se pudo cargar la liga' : 'No se seleccionó ninguna liga'}</AlertTitle>
                <AlertDescription>
                    {error || 'Debés seleccionar una liga para poder inscribirte.'}
                    {' '}<Link to="/ligas-disponibles">Ver ligas disponibles</Link>
                </AlertDescription>
            </Alert>
        );
    }

    if (!team) {
        return (
            <Alert variant="destructive">
                <AlertTitle>No se pudo cargar el equipo</AlertTitle>
                <AlertDescription>
                    {error ||
                        'No se encontró un equipo disponible para inscribirse.'}
                </AlertDescription>
            </Alert>
        );
    }

    if (league.isRegistered) {
        return (
            <Card>
                <CardHeader>
                    <CardTitle>Inscripción confirmada</CardTitle>
                    <CardDescription>
                        Tu club ya está inscripto en {league.name}.
                    </CardDescription>
                </CardHeader>

                <CardContent>
                    <Link to={`/leagues/${league.id}/lobby`}>Ver lobby</Link>
                </CardContent>
            </Card>
        );
    }

    return (
        <Card>
            <CardHeader>
                <CardTitle>Inscribirse en {league.name}</CardTitle>

                <CardDescription>
                    Revisá tu equipo y confirmá la inscripción.
                </CardDescription>
            </CardHeader>

            <CardContent className="space-y-4">
                <div>
                    <h2 className="font-semibold">
                        Equipo que se inscribirá
                    </h2>

                    <ul className="mt-2 space-y-1">
                        {team.players.map((player) => <li key={player.id}>{player.name}</li>)}
                    </ul>
                </div>

                {needsAccessCode && (
                    <div className="space-y-2">
                        <label
                            htmlFor="access-code"
                            className="font-medium"
                        >
                            Código de acceso
                        </label>

                        <input
                            id="access-code"
                            type="password"
                            value={accessCode}
                            onChange={(event) =>
                                setAccessCode(event.target.value)
                            }
                            className="w-full rounded-md border p-2"
                            placeholder="Ingresá el código"
                        />
                    </div>
                )}

                {error && (
                    <Alert variant="destructive">
                        <AlertTitle>
                            No se pudo completar la inscripción
                        </AlertTitle>

                        <AlertDescription>
                            {error}
                        </AlertDescription>
                    </Alert>
                )}

                <Button
                    onClick={handleJoin}
                    disabled={joining || team.lineUp.length !== 6 || needsAccessCode && !accessCode.trim()}
                >
                    {joining
                        ? 'Inscribiendo...'
                        : 'Confirmar inscripción'}
                </Button>
            </CardContent>
        </Card>
    );
}
