import {useEffect, useRef, useState} from 'react';
import {Link, useNavigate, useParams} from 'react-router';
import {Alert, AlertDescription, AlertTitle} from '@/components/ui/alert';
import {ArrowLeft, ArrowRight, Check, CircleAlert, CircleCheck, ClipboardList, Globe, LockKeyhole, Trophy, Users} from 'lucide-react';
import {Badge} from '@/components/ui/badge';
import {Button, buttonVariants} from '@/components/ui/button';
import {Field, FieldLabel} from '@/components/ui/field';
import {Input} from '@/components/ui/input';
import {Card, CardContent, CardDescription, CardHeader,} from '@/components/ui/card';
import {getDefaultTeam, getLeagueLobby, joinLeague,} from './api.js';
import {routePath, routes} from '@/routes.js';

function RegistrationLayout({children}) {
    return (
        <main className="mx-auto w-[calc(100%_-_32px)] max-w-6xl space-y-6 py-8 sm:py-12">
            <Link to={routes.leagues} className={buttonVariants({variant: 'outline'})}>
                <ArrowLeft aria-hidden="true"/> Volver a ligas disponibles
            </Link>
            {children}
        </main>
    );
}

function LineupGroup({title, players}) {
    return (
        <section aria-label={title} className="min-w-0 space-y-3">
            <div className="flex items-center gap-2">
                <h3 className="font-semibold">{title}</h3>
                <Badge variant="outline">{players.length}</Badge>
            </div>
            <ol className="list-none divide-y rounded-xl border bg-background px-4">
                {players.map(player => (
                    <li key={player.id} className="flex min-w-0 items-center gap-3 py-4">
                        <span className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-secondary text-primary" aria-hidden="true">
                            <Users className="size-4"/>
                        </span>
                        <div className="min-w-0 space-y-1">
                            <p className="text-sm font-semibold wrap-anywhere">{player.name}</p>
                            <p className="text-xs leading-relaxed text-muted-foreground wrap-anywhere">
                                {player.position && <>{player.position} · </>}
                                {player.behaviourName}
                            </p>
                        </div>
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
        return <RegistrationLayout>
            <Card><CardContent><p role="status" className="py-8 text-center text-sm text-muted-foreground">Cargando la liga y tu equipo...</p></CardContent></Card>
        </RegistrationLayout>;
    }

    if (!league) {
        return (
            <RegistrationLayout>
                <Alert variant="destructive">
                    <CircleAlert aria-hidden="true"/>
                    <AlertTitle>{error ? 'No se pudo cargar la liga' : 'No se seleccionó ninguna liga'}</AlertTitle>
                    <AlertDescription>
                        {error || 'Debés seleccionar una liga para poder inscribirte.'}
                        {' '}<Link to={routes.leagues}>Ver ligas disponibles</Link>
                    </AlertDescription>
                </Alert>
            </RegistrationLayout>
        );
    }

    if (league.isRegistered) {
        return (
            <RegistrationLayout>
                <Card className="mx-auto max-w-xl rounded-2xl text-center">
                    <CardHeader className="justify-items-center gap-3 px-6 pt-4">
                        <span className="flex size-16 items-center justify-center rounded-2xl bg-secondary text-primary">
                            <CircleCheck className="size-8" aria-hidden="true"/>
                        </span>
                        <h1 className="text-2xl font-bold">Inscripción confirmada</h1>
                        <CardDescription>Tu club ya está inscripto en {league.name}.</CardDescription>
                    </CardHeader>
                    <CardContent className="pb-4">
                        <Link to={routePath(routes.leagueLobby, {id: league.id})} className={buttonVariants({className: 'h-10'})}>
                            Ver lobby <ArrowRight aria-hidden="true"/>
                        </Link>
                    </CardContent>
                </Card>
            </RegistrationLayout>
        );
    }

    return (
        <RegistrationLayout>
            <header className="flex items-center gap-4">
                <span className="flex size-16 shrink-0 items-center justify-center rounded-2xl bg-secondary text-primary">
                    <Trophy className="size-8" aria-hidden="true"/>
                </span>
                <div className="min-w-0 space-y-2">
                    <h1 className="text-2xl font-bold tracking-tight wrap-anywhere sm:text-3xl">Inscribirse en {league.name}</h1>
                    <div className="flex flex-wrap items-center gap-3">
                        <Badge variant="secondary">
                            {needsAccessCode ? <LockKeyhole aria-hidden="true"/> : <Globe aria-hidden="true"/>}
                            {needsAccessCode ? 'Liga privada' : 'Liga pública'}
                        </Badge>
                        <p className="text-sm text-muted-foreground">Revisá tu equipo y confirmá la inscripción.</p>
                    </div>
                </div>
            </header>

            {!team ? (
                <Card>
                    <CardContent className="space-y-4">
                        <Alert variant="destructive">
                            <CircleAlert aria-hidden="true"/>
                            <AlertTitle>No se pudo cargar el equipo</AlertTitle>
                            <AlertDescription>{error || 'No se encontró un equipo disponible para inscribirse.'}</AlertDescription>
                        </Alert>
                        <Link to={routes.myClub} className={buttonVariants()}>
                            <Users aria-hidden="true"/> Configurar mi equipo
                        </Link>
                    </CardContent>
                </Card>
            ) : (
                <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1fr)_320px]">
                    <Card className="min-w-0 rounded-2xl">
                        <CardHeader className="gap-3 border-b p-6">
                            <h2 className="flex items-center gap-2 text-lg font-bold">
                                <Users className="size-5" aria-hidden="true"/> Equipo que se inscribirá
                            </h2>
                            <CardDescription>Se usará el equipo guardado en Mi club.</CardDescription>
                            <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg bg-secondary/50 p-3">
                                <p className="flex items-center gap-2 text-sm text-muted-foreground">
                                    <ClipboardList className="size-4" aria-hidden="true"/>
                                    Formación <strong className="text-foreground">{team.formationName}</strong>
                                </p>
                                <Link to={routes.myClub} className={buttonVariants({variant: 'outline', size: 'sm'})}>Modificar equipo</Link>
                            </div>
                        </CardHeader>
                        <CardContent className="grid gap-5 px-6 pb-2 sm:grid-cols-2">
                            <LineupGroup title="Titulares" players={team.starters}/>
                            <LineupGroup title="Suplentes" players={team.substitutes}/>
                        </CardContent>
                    </Card>

                    <Card className="rounded-2xl ring-primary/15 lg:sticky lg:top-6">
                        <CardHeader className="gap-2 border-b px-6 pb-5">
                            <h2 className="text-lg font-bold">Confirmar inscripción</h2>
                            <CardDescription>
                                {needsAccessCode ? 'Ingresá el código de acceso de la liga para participar.' : 'Confirmá la participación de tu club con este equipo.'}
                            </CardDescription>
                        </CardHeader>
                        <CardContent className="space-y-5 px-6 pb-2">
                            {needsAccessCode && (
                                <Field>
                                    <FieldLabel htmlFor="access-code">Código de acceso</FieldLabel>
                                    <Input id="access-code" type="password" className="h-10" value={accessCode}
                                        onChange={event => {
                                            setAccessCode(event.target.value);
                                            setPasswordError('');
                                        }}
                                        autoComplete="off" aria-invalid={Boolean(passwordError)}
                                        aria-describedby={passwordError ? 'access-code-error' : undefined}
                                        placeholder="Ingresá el código"/>
                                    {passwordError && <p id="access-code-error" role="alert" className="text-sm text-destructive">{passwordError}</p>}
                                </Field>
                            )}
                            {error && (
                                <Alert variant="destructive">
                                    <CircleAlert aria-hidden="true"/>
                                    <AlertTitle>No se pudo completar la inscripción</AlertTitle>
                                    <AlertDescription>{error}</AlertDescription>
                                </Alert>
                            )}
                            {lineupChanged && (
                                <Button variant="outline" className="w-full" onClick={() => setTeamReload(count => count + 1)}>Actualizar equipo</Button>
                            )}
                            {retryAfter > 0 && (
                                <Alert variant="destructive"><AlertDescription>Alcanzaste el límite de intentos. Podés volver a intentar en {retryAfter} segundos.</AlertDescription></Alert>
                            )}
                            <Button className="h-11 w-full" onClick={handleJoin}
                                disabled={joining || lineupChanged || retryAfter > 0 || needsAccessCode && !accessCode.trim()}>
                                <Check aria-hidden="true"/>{joining ? 'Inscribiendo...' : 'Confirmar inscripción'}
                            </Button>
                        </CardContent>
                    </Card>
                </div>
            )}
        </RegistrationLayout>
    );
}
