import {useEffect, useRef, useState} from 'react';
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
    const [passwordError, setPasswordError] = useState('');
    const [retryAfter, setRetryAfter] = useState(0);
    const [accessCode, setAccessCode] = useState('');
    const joiningRef = useRef(false);
    const needsAccessCode = league?.isPrivate === true;

    useEffect(() => {
        if (retryAfter <= 0) return;
        const timer = setTimeout(() => setRetryAfter(seconds => seconds - 1), 1000);
        return () => clearTimeout(timer);
    }, [retryAfter]);

    useEffect(() => {
        const controller = new AbortController();

        async function loadTeam() {
            setLeague(suppliedLeague || null);
            setTeam(null);
            setAccessCode('');
            setPasswordError('');
            setRetryAfter(0);
            if (!suppliedLeague && !leagueId) {
                setLoading(false);
                return;
            }
            try {
                setLoading(true);
                setError('');
                const selectedLeague = suppliedLeague
                    || await getLeagueLobby(leagueId, {signal: controller.signal});
                if (controller.signal.aborted) return;
                setLeague(selectedLeague);
                const data = await getDefaultTeam({signal: controller.signal});
                if (!controller.signal.aborted) {
                    setTeam(data);
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
        if (joiningRef.current || !league || !team || retryAfter > 0
            || needsAccessCode && !accessCode.trim()) return;

        joiningRef.current = true;
        setError('');
        setPasswordError('');

        try {
            setJoining(true);
            await joinLeague(
                league.id,
                team.clubId,
                team.lineUp,
                needsAccessCode ? accessCode : undefined
            );
            navigate(`/leagues/${league.id}/lobby`);
        } catch (err) {
            if (err.code === 'LEAGUE_ACCESS_INVALID') {
                setPasswordError('La contraseña de la liga es incorrecta. Revisala y volvé a intentar.');
            } else if (err.status === 429) {
                const seconds = Number(err.retryAfter);
                setRetryAfter(Number.isFinite(seconds) && seconds > 0 ? Math.ceil(seconds) : 60);
            } else {
                const messages = {
                    LEAGUE_FULL: 'La liga está completa. No quedan cupos disponibles.',
                    LEAGUE_CLOSED: 'Las inscripciones de esta liga están cerradas.',
                    ALREADY_REGISTERED: 'Tu club ya está inscripto en esta liga.',
                    NETWORK_ERROR: 'No se pudo conectar con el servidor. Volvé a intentar.',
                };
                setError(messages[err.code] || 'No se pudo completar la inscripción. Revisá tu equipo y volvé a intentar.');
            }
        } finally {
            joiningRef.current = false;
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
                    {' '}<Link to="/mi-club">Configurar mi equipo</Link>
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
                            onChange={(event) => {
                                setAccessCode(event.target.value);
                                setPasswordError('');
                            }}
                            autoComplete="off"
                            aria-invalid={Boolean(passwordError)}
                            aria-describedby={passwordError ? 'access-code-error' : undefined}
                            className="w-full rounded-md border p-2"
                            placeholder="Ingresá el código"
                        />
                        {passwordError && <p id="access-code-error" role="alert">{passwordError}</p>}
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

                {retryAfter > 0 && <p role="alert">Alcanzaste el límite de intentos. Podés volver a intentar en {retryAfter} segundos.</p>}

                <Button
                    onClick={handleJoin}
                    disabled={joining || retryAfter > 0 || team.lineUp.length !== 6 || needsAccessCode && !accessCode.trim()}
                >
                    {joining
                        ? 'Inscribiendo...'
                        : 'Confirmar inscripción'}
                </Button>
            </CardContent>
        </Card>
    );
}
