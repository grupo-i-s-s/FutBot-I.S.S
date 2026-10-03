import { useEffect, useState } from 'react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from '@/components/ui/card'
import {
    getDefaultTeam,
    joinLeague,
    getLeagueLobby,
} from './api.js'

export default function InscripcionLigaPage({ league }) {
    const [team, setTeam] = useState(null)
    const [loading, setLoading] = useState(true)
    const [joining, setJoining] = useState(false)
    const [error, setError] = useState('')
    const [accessCode, setAccessCode] = useState('')
    const [joined, setJoined] = useState(false)
    const [lobby, setLobby] = useState(null)

    useEffect(() => {
        async function loadTeam() {
            try {
                setLoading(true)
                setError('')

                const data = await getDefaultTeam()
                setTeam(data)
            } catch (err) {
                setError(err?.message ?? 'No se pudo cargar tu equipo.')
            } finally {
                setLoading(false)
            }
        }

        loadTeam()
    }, [])

    async function handleJoin() {
        if (joining) return

        try {
            setJoining(true)
            setError('')

            const response = await joinLeague(
                league.id,
                team.clubId,
                team.lineUp,
                league.type === 'PRIVATE' ? accessCode : undefined
            )

            const lobbyData = await getLeagueLobby(league.id)

            setLobby(lobbyData)
            setJoined(true)

            console.log(response)
        } catch (err) {
            if (err?.status === 409) {
                setError(
                    err.message ||
                    'No hay cupos disponibles, el código es incorrecto o el club ya está inscripto.'
                )
            } else if (err?.status === 400) {
                setError(
                    err.message ||
                    'El equipo no es válido para esta liga.'
                )
            } else {
                setError(
                    err?.message ||
                    'No se pudo completar la inscripción.'
                )
            }
        } finally {
            setJoining(false)
        }
    }

    if (!league) {
        return (
            <Alert variant="destructive">
                <AlertTitle>No se seleccionó ninguna liga</AlertTitle>
                <AlertDescription>
                    Debés seleccionar una liga para poder inscribirte.
                </AlertDescription>
            </Alert>
        )
    }

    if (loading) {
        return <p>Cargando tu equipo...</p>
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
        )
    }

    if (joined) {
        return (
            <Card>
                <CardHeader>
                    <CardTitle>Inscripción confirmada</CardTitle>
                    <CardDescription>
                        Tu club ya está inscripto en {league.name}.
                    </CardDescription>
                </CardHeader>

                <CardContent>
                    <h2 className="font-semibold">Lobby</h2>

                    <pre className="mt-2 rounded-md bg-muted p-4 text-sm">
                        {JSON.stringify(lobby, null, 2)}
                    </pre>
                </CardContent>
            </Card>
        )
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

                    <pre className="mt-2 rounded-md bg-muted p-4 text-sm">
                        {JSON.stringify(team, null, 2)}
                    </pre>
                </div>

                {league.type === 'PRIVATE' && (
                    <div className="space-y-2">
                        <label
                            htmlFor="access-code"
                            className="font-medium"
                        >
                            Código de acceso
                        </label>

                        <input
                            id="access-code"
                            type="text"
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
                    disabled={joining}
                >
                    {joining
                        ? 'Inscribiendo...'
                        : 'Confirmar inscripción'}
                </Button>
            </CardContent>
        </Card>
    )
}




