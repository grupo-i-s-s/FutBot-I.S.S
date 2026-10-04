import { useState } from 'react'
import { CircleAlert, Info } from 'lucide-react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import ClubHeader from './components/ClubHeader'
import ClubSettingsDialog from './components/ClubSettingsDialog'
import LeagueList from './components/LeagueList'
import PlayerList from './components/PlayerList'
import TeamSettings from './components/TeamSettings'
import { useMyClub } from './hooks/useMyClub'
import { updateMyClub } from './api'

const PAGE_CLASSES = 'mx-auto w-[calc(100%_-_32px)] max-w-4xl space-y-6 py-8 sm:py-12 xl:w-[calc(100%_-_560px)]'

export default function MyClubPage() {
    const { status, error, club, players, behaviours, leagues, reload, setClub, updatePlayer } = useMyClub()
    const [isSettingsOpen, setIsSettingsOpen] = useState(false)
    const [notice, setNotice] = useState('')

const [isSaving, setIsSaving] = useState(false)
const [saveError, setSaveError] = useState('')

    // SIMULADO: los cambios se aplican solo en esta vista.
    // Reemplazar por PATCH /club/me cuando el endpoint exista.
    async function handleSettingsSave(changes) {
    if (isSaving) return

    setIsSaving(true)
    setSaveError('')
    setNotice('')

    try {
        const updatedClub = await updateMyClub(changes)
        setClub(updatedClub)
        setIsSettingsOpen(false)
        setNotice('Los cambios del club se guardaron correctamente.')
    } catch (requestError) {
        const fieldErrors = Object.values(requestError.fields ?? {}).join(' ')
        setSaveError(fieldErrors || requestError.message)
    } finally {
        setIsSaving(false)
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
        )
    }

    if (status === 'error') {
        const isSessionError = error?.status === 401
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
        )
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

            <div className="relative">
                <PlayerList
                    players={players}
                    behaviours={behaviours}
                    onBehaviourAssigned={updatePlayer}
                />

                <aside
                    aria-label="Ligas inscriptas"
                    className="mt-6 xl:absolute xl:top-0 xl:mt-0 xl:left-[-280px]"
                >
                    <LeagueList leagues={leagues} />
                </aside>

                <aside
                    aria-label="Mi equipo"
                    className="mt-6 xl:absolute xl:top-0 xl:mt-0 xl:right-[-280px] xl:w-64"
                >
                    <TeamSettings
                        key={club.id}
                        clubId={club.id}
                        players={players}
                        behaviours={behaviours}
                    />
                </aside>
            </div>
                    
            <ClubSettingsDialog
                club={club}
                isOpen={isSettingsOpen}
                onOpenChange={(open) => {
                    if (isSaving) return
                    setSaveError('')
                    setIsSettingsOpen(open)
                }}
                onSave={handleSettingsSave}
                isSaving={isSaving}
                saveError={saveError}
            />
        </main>
    )
}
