import { useState } from 'react'
import { CircleAlert, Info } from 'lucide-react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import ClubHeader from './components/ClubHeader'
import ClubSettingsDialog from './components/ClubSettingsDialog'
import LeagueList from './components/LeagueList'
import PlayerList from './components/PlayerList'
import { useMyClub } from './hooks/useMyClub'
import { MOCK_JOINED_LEAGUES } from './mockData'
import { Link } from 'react-router'

const PAGE_CLASSES = 'mx-auto w-[calc(100%_-_32px)] max-w-4xl space-y-6 py-8 sm:py-12'

export default function MyClubPage() {
    const { status, error, club, players, behaviours, reload, setClub, updatePlayer } = useMyClub()
    const [isSettingsOpen, setIsSettingsOpen] = useState(false)
    const [notice, setNotice] = useState('')

    // SIMULADO: los cambios se aplican solo en esta vista.
    // Reemplazar por PATCH /club/me cuando el endpoint exista.
    function handleSettingsSave(changes) {
        setClub((currentClub) => ({ ...currentClub, ...changes }))
        setIsSettingsOpen(false)
        setNotice('Los cambios se aplican solo en esta vista: todavía no se guardan en el servidor.')
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

            <PlayerList
                players={players}
                behaviours={behaviours}
                onBehaviourAssigned={updatePlayer}
            />
            <LeagueList leagues={MOCK_JOINED_LEAGUES} isMock />
            <Link
                to="/ligas-disponibles"
                className="inline-block font-semibold text-brand underline"
            >
                Explorar ligas disponibles
            </Link>

            <ClubSettingsDialog
                club={club}
                isOpen={isSettingsOpen}
                onOpenChange={setIsSettingsOpen}
                onSave={handleSettingsSave}
            />
        </main>
    )
}
