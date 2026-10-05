import { useEffect, useState } from 'react'
import { getDefaultTeam, getFormations, updateDefaultTeam } from '../api'
import { Users } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle, } from '@/components/ui/card'


const SELECT_CLASSES =
    'w-full min-w-0 rounded-md border border-input bg-background px-2 py-2 text-sm'

function loadTeam(response) {
    const { lineUp } = response

    return {
        formation: String(lineUp.formationId),
        slots: [...lineUp.starters, ...lineUp.substitutes].map(
            (slot) => ({
                playerId: String(slot.playerId),
                behaviourId: String(slot.behaviourId),
            })
        ),
    }
}

export default function TeamSettings({ clubId, players, behaviours }) {
    const [error, setError] = useState('')
    const [success, setSuccess] = useState('')
    const [team, setTeam] = useState(null)
    const [formations, setFormations] = useState([])
    const [loading, setLoading] = useState(true)
    const [isSaving, setIsSaving] = useState(false)

    function clearFeedback() {
        setError('')
        setSuccess('')
    }
    useEffect(() => {
        const controller = new AbortController()
        const options = { signal: controller.signal }

        async function fetchTeam() {
            setLoading(true)
            setTeam(null)
            setError('')
            setSuccess('')

            try {
                const [response, catalog] = await Promise.all([
                    getDefaultTeam(options),
                    getFormations(options),
                ])

                if (controller.signal.aborted) return

                if (!response) {
                    throw new Error(
                        'No se encontró el equipo del club en la base de datos.'
                    )
                }

                setTeam(loadTeam(response))
                setFormations(catalog.items)
            } catch (err) {
                if (!controller.signal.aborted) {
                    setError(err.message || 'No se pudo cargar el equipo.')
                }
            } finally {
                if (!controller.signal.aborted) {
                    setLoading(false)
                }
            }
        }

        fetchTeam()
        return () => controller.abort()
    }, [clubId])

    function changeSlot(index, field, value) {
        clearFeedback()

        setTeam((current) => ({
            ...current,
            slots: current.slots.map((slot, slotIndex) => {
                if (slotIndex !== index) return slot

                if (field === 'playerId') {
                    const player = players.find(
                        (item) => String(item.id) === value
                    )

                    return {
                        playerId: value,
                        behaviourId: String(player?.behaviorId ?? ''),
                    }
                }

                return { ...slot, [field]: value }
            }),
        }))
    }

    async function handleSubmit(event) {
        event.preventDefault()
        if (isSaving || !team) return
        clearFeedback()

        const playerIds = team.slots.map((slot) => slot.playerId)

        if (playerIds.some((id) => !id)) {
            setError('Elegí los 6 jugadores del equipo.')
            return
        }

        if (new Set(playerIds).size !== 6) {
            setError('Un jugador no puede ocupar dos lugares.')
            return
        }

        if (team.slots.some((slot) =>
            !behaviours.some(
                (behaviour) => String(behaviour.id) === slot.behaviourId
            )
        )) {
            setError('Elegí un comportamiento para cada jugador.')
            return
        }

        if (!formations.some(
            (formation) => String(formation.id) === team.formation
        )) {
            setError('Elegí una formación disponible.')
            return
        }

        const selections = team.slots.map((slot) => ({
            playerId: Number(slot.playerId),
            behaviourId: Number(slot.behaviourId),
        }))

        setIsSaving(true)

        try {
            const response = await updateDefaultTeam({
                formationId: Number(team.formation),
                starters: selections.slice(0, 3),
                substitutes: selections.slice(3, 6),
            })

            setTeam(loadTeam(response))
            setSuccess('Equipo guardado correctamente.')
        } catch (err) {
            const fields = Object.values(err.fields ?? {}).join(' ')
            setError(
                fields || err.message || 'No se pudo guardar el equipo.'
            )
        } finally {
            setIsSaving(false)
        }
    }
    if (loading) {
        return <p role="status">Cargando equipo...</p>
    }
    if (!team) {
        return <p role="alert">{error}</p>
    }

    return (
        <Card>
            <CardHeader>
                <CardTitle className="flex items-center gap-2 text-lg font-bold">
                    <Users className="size-5" aria-hidden="true" />
                    Mi equipo
                </CardTitle>
                <CardDescription>
                    3 titulares y 3 suplentes.
                </CardDescription>
            </CardHeader>

            <CardContent>
                <form onSubmit={handleSubmit} noValidate className="space-y-4">
                    <div className="space-y-1">
                        <label htmlFor="team-formation" className="text-sm font-medium">
                            Formación
                        </label>

                        <select
                            id="team-formation"
                            disabled={isSaving}
                            className={SELECT_CLASSES}
                            value={team.formation}
                            onChange={(event) => {
                                clearFeedback()
                                setTeam((current) => ({
                                    ...current,
                                    formation: event.target.value,
                                }))
                            }}
                        >
                            {formations.map((formation) => (
                                <option key={formation.id} value={formation.id}>
                                    {formation.name}
                                </option>
                            ))} 
                        </select>
                    </div>

                    {team.slots.map((slot, index) => (
                        <fieldset
                            key={index}
                            disabled={isSaving}
                            className="min-w-0 space-y-2 rounded-md border p-2"
                        >
                            <legend className="px-1 text-sm font-semibold">
                                {index < 3
                                    ? `Titular ${index + 1}`
                                    : `Suplente ${index - 2}`}
                            </legend>

                            <div>
                                <label htmlFor={`team-player-${index}`} className="sr-only">
                                    Jugador del lugar {index + 1}
                                </label>

                                <select
                                    id={`team-player-${index}`}
                                    className={SELECT_CLASSES}
                                    value={slot.playerId}
                                    onChange={(event) =>
                                        changeSlot(index, 'playerId', event.target.value)
                                    }
                                >
                                    <option value="">Elegir jugador</option>

                                    {players.map((player) => (
                                        <option
                                            key={player.id}
                                            value={player.id}
                                            disabled={team.slots.some(
                                                (other, otherIndex) =>
                                                    otherIndex !== index &&
                                                    other.playerId === String(player.id)
                                            )}
                                        >
                                            {player.name}
                                        </option>
                                    ))}
                                </select>
                            </div>

                            <div>
                                <label htmlFor={`team-behaviour-${index}`} className="sr-only">
                                    Comportamiento del lugar {index + 1}
                                </label>

                                <select
                                    id={`team-behaviour-${index}`}
                                    className={SELECT_CLASSES}
                                    value={slot.behaviourId}
                                    onChange={(event) =>
                                        changeSlot(index, 'behaviourId', event.target.value)
                                    }
                                >
                                    <option value="">Elegir comportamiento</option>

                                    {behaviours.map((behaviour) => (
                                        <option key={behaviour.id} value={behaviour.id}>
                                            {behaviour.name}
                                        </option>
                                    ))}
                                </select>
                            </div>
                        </fieldset>
                    ))}

                    {players.length < 6 && (
                        <p className="text-sm text-destructive">
                            Necesitás al menos 6 jugadores para configurar el equipo.
                        </p>
                    )}

                    {behaviours.length === 0 && (
                        <p className="text-sm text-destructive">
                            Necesitás comportamientos disponibles.
                        </p>
                    )}

                    <Button
                        type="submit"
                        className="w-full"
                        disabled={ isSaving || players.length < 6 || behaviours.length === 0 || formations.length === 0 }
                    >
                        {isSaving ? 'Guardando...' : 'Guardar equipo'}
                    </Button>

                    {error && (
                        <p role="alert" className="text-sm text-destructive">
                            {error}
                        </p>
                    )}

                    {success && (
                        <p role="status" className="text-sm">
                            {success}
                        </p>
                    )}
                </form>
            </CardContent>
        </Card>
    )
}