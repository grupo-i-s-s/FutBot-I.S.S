import {useEffect, useRef, useState} from 'react';
import {Link, useNavigate, useParams} from 'react-router';
import {Alert, AlertDescription, AlertTitle} from '@/components/ui/alert';
import {Button} from '@/components/ui/button';
import {Card, CardContent, CardDescription, CardHeader, CardTitle,} from '@/components/ui/card';
import {getDefaultTeam, getLeagueLobby, joinLeague,} from './api.js';
import {routePath, routes} from '@/routes.js';

function LineupGroup({title, players}) {
    return (
        <section aria-label={title}>
            <h3 className="font-medium">{title}</h3>
            <ol className="mt-2 space-y-2">
                {players.map(player => (
                    <li key={player.id}>
                        <p>{player.name}</p>
                        <p className="text-sm text-muted-foreground">
                            {player.position && <>{player.position} · </>}
                            {player.behaviourName}
                        </p>
                    </li>
                ))}
            </ol>
        </section>
    );
}

export default function InscripcionLigaPage({league: suppliedLeague} = {}) {
    const {id: leagueId} = useParams();
    const navigate = useNavigate();
    const [league, setLeague] = useState(suppliedLeague || null);
    const [team, setTeam] = useState(null);
    const [loading, setLoading] = useState(true);
    const [joining, setJoining] = useState(false);
    const [error, setError] = useState('');
    const [passwordError, setPasswordError] = useState('');
    const [retryAfter, setRetryAfter] = useState(0);
    const [accessCode, setAccessCode] = useState('');
    const [lineupChanged, setLineupChanged] = useState(false);
    const [teamReload, setTeamReload] = useState(0);
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
            setLineupChanged(false);
            setError('');
            if (!suppliedLeague && !leagueId) {
                setLoading(false);
                return;
            }
            try {
                setLoading(true);
                const selectedLeague = suppliedLeague
                    || await getLeagueLobby(leagueId, {signal: controller.signal});
                if (controller.signal.aborted) return;
                setLeague(selectedLeague);
                if (selectedLeague.isRegistered) return;
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
    }, [leagueId, suppliedLeague, teamReload]);

    async function handleJoin() {
        if (joiningRef.current || !league || !team || lineupChanged || retryAfter > 0
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
            navigate(routePath(routes.leagueLobby, {id: league.id}));
        } catch (err) {
            if (err.code === 'LEAGUE_ACCESS_INVALID') {
                setPasswordError('La contraseña de la liga es incorrecta. Revisala y volvé a intentar.');
            } else if (err.code === 'LEAGUE_LINEUP_CHANGED') {
                setLineupChanged(true);
                setError('Tu equipo guardado cambió. Actualizá la alineación y revisala antes de inscribirte.');
            } else if (err.code === 'LEAGUE_LINEUP_INVALID') {
                setTeam(null);
                setError(err.message || 'Tu equipo guardado ya no es válido. Revisá la alineación antes de inscribirte.');
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
                    {' '}<Link to={routes.leagues}>Ver ligas disponibles</Link>
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
                    <Link to={routePath(routes.leagueLobby, {id: league.id})}>Ver lobby</Link>
                </CardContent>
            </Card>
        );
    }

    if (!team) {
        return (
            <Alert variant="destructive">
                <AlertTitle>No se pudo cargar el equipo</AlertTitle>
                <AlertDescription>
                    {error || 'No se encontró un equipo disponible para inscribirse.'}
                    {' '}<Link to={routes.myClub}>Configurar mi equipo</Link>
                </AlertDescription>
            </Alert>
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
                <div className="space-y-3">
                    <h2 className="font-semibold">
                        Equipo que se inscribirá
                    </h2>
                    <p>Formación <strong>{team.formationName}</strong></p>
                    <div className="grid gap-4 sm:grid-cols-2">
                        <LineupGroup title="Titulares" players={team.starters} />
                        <LineupGroup title="Suplentes" players={team.substitutes} />
                    </div>
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
                {lineupChanged && (
                    <Button variant="outline" onClick={() => setTeamReload(count => count + 1)}>
                        Actualizar equipo
                    </Button>
                )}

                {retryAfter > 0 && <p role="alert">Alcanzaste el límite de intentos. Podés volver a intentar en {retryAfter} segundos.</p>}

                <Button
                    onClick={handleJoin}
                    disabled={joining || lineupChanged || retryAfter > 0 || needsAccessCode && !accessCode.trim()}
                >
                    {joining
                        ? 'Inscribiendo...'
                        : 'Confirmar inscripción'}
                </Button>
            </CardContent>
        </Card>
    );
}
