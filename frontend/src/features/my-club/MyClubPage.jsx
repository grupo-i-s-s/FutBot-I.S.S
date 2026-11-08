import { useState } from 'react';
import { Brain, CircleAlert, Info, Shirt, Trophy, Users } from 'lucide-react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import ClubBehaviourList from './components/ClubBehaviourList';
import ClubHeader from './components/ClubHeader';
import ClubSettingsDialog from './components/ClubSettingsDialog';
import TeamSettings from './components/TeamSettings';
import LeagueList from './components/LeagueList';
import PlayerList from './components/PlayerList';
import { useMyClub } from './hooks/useMyClub';
import { updateMyClub } from './api';



const PAGE_CLASSES = 'mx-auto w-[calc(100%_-_32px)] max-w-6xl space-y-6 py-8 sm:py-12';
const CLUB_TABS = [
    {value: 'team', label: 'Mi equipo', icon: Shirt},
    {value: 'players', label: 'Jugadores', icon: Users},
    {value: 'behaviours', label: 'Comportamientos', icon: Brain},
    {value: 'leagues', label: 'Ligas inscriptas', icon: Trophy},
];

export default function MyClubPage() {
    const [page, setPage] = useState(1);
    const {
        status, error, club, players, totalPages, totalPlayers, behaviours, leagues, reload, setClub,
        rosterLoading, rosterError, reloadRoster,
    } = useMyClub(page, 9);
    const [isSettingsOpen, setIsSettingsOpen] = useState(false);
    const [notice, setNotice] = useState('');

    const [isSaving, setIsSaving] = useState(false);
    const [saveError, setSaveError] = useState('');

    async function handleSettingsSave(changes) {
        if (isSaving) return;

        setIsSaving(true);
        setSaveError('');
        setNotice('');

        try {
            const updatedClub = await updateMyClub(changes);
            setClub(updatedClub);
            setIsSettingsOpen(false);
            setNotice('Los cambios del club se guardaron correctamente.');
        } catch (requestError) {
            const fieldErrors = Object.values(requestError.fields ?? {}).join(' ');
            setSaveError(fieldErrors || requestError.message);
        } finally {
            setIsSaving(false);
        }
    }

    if (status === 'loading') {
        return (
            <main className={PAGE_CLASSES} aria-busy="true">
                <p className="sr-only" role="status">Cargando tu club…</p>
                <Skeleton className="h-32 w-full rounded-xl" />
                <Skeleton className="h-56 w-full rounded-xl" />
                <Skeleton className="h-40 w-full rounded-xl" />
            </main>
        );
    }

    if (status === 'error') {
        const isSessionError = error?.status === 401;
        return (
            <main className={PAGE_CLASSES}>
                <Alert variant="destructive">
                    <CircleAlert />
                    <AlertTitle>No se pudo cargar tu club</AlertTitle>
                    <AlertDescription>
                        <p>
                            {isSessionError
                                ? 'Tu sesión venció o no iniciaste sesión. Ingresá nuevamente para ver tu club.'
                                : error?.message ?? 'Ocurrió un error inesperado.'}
                        </p>
                        {!isSessionError && (
                            <Button variant="outline" className="mt-2" onClick={reload}>Reintentar</Button>
                        )}
                    </AlertDescription>
                </Alert>
            </main>
        );
    }

    return (
        <main className={PAGE_CLASSES}>
            <ClubHeader club={club} onSettingsClick={() => setIsSettingsOpen(true)} />

            {notice && (
                <Alert>
                    <Info />
                    <AlertDescription>{notice}</AlertDescription>
                </Alert>
            )}

            <Tabs defaultValue="team" className="w-full min-w-0 gap-4">
                <TabsList
                    aria-label="Secciones de Mi club"
                    className="w-full gap-2 rounded-xl border bg-card p-2 shadow-sm group-data-horizontal/tabs:h-16"
                >
                    {CLUB_TABS.map(({value, label, icon: Icon}) => (
                        <TabsTrigger
                            key={value}
                            value={value}
                            className="gap-2 rounded-lg px-3 font-semibold text-foreground/80 hover:bg-accent data-active:bg-primary data-active:text-primary-foreground data-active:hover:bg-primary data-active:hover:text-primary-foreground dark:data-active:bg-primary dark:data-active:text-primary-foreground"
                        >
                            <Icon className="size-[18px]" aria-hidden="true" />
                            {label}
                        </TabsTrigger>
                    ))}
                </TabsList>

                <TabsContent value="team" keepMounted>
                    <TeamSettings
                        key={club.id}
                        clubId={club.id}
                        behaviours={behaviours}
                    />
                </TabsContent>

                <TabsContent value="players">
                    <PlayerList
                        players={players}
                        currentPage={page}
                        totalPages={totalPages}
                        totalPlayers={totalPlayers}
                        onPageChange={setPage}
                        loading={rosterLoading}
                        error={rosterError}
                        onRetry={reloadRoster}
                    />
                </TabsContent>

                <TabsContent value="behaviours">
                    <ClubBehaviourList behaviours={behaviours} />
                </TabsContent>

                <TabsContent value="leagues">
                    <LeagueList leagues={leagues} />
                </TabsContent>
            </Tabs>

            <ClubSettingsDialog
                club={club}
                behaviours={behaviours}
                isOpen={isSettingsOpen}
                onOpenChange={(open) => {
                    if (isSaving) return;
                    setSaveError('');
                    setIsSettingsOpen(open);
                }}
                onSave={handleSettingsSave}
                isSaving={isSaving}
                saveError={saveError}
            />
        </main>
    );
}
