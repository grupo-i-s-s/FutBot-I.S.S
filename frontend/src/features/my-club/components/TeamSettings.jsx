import { useState } from 'react'
import { Users } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
    Card,
    CardContent,
    CardDescription,
    CardHeader,
    CardTitle,
} from '@/components/ui/card'

const FORMATIONS = ['1-1-1', '2-1', '1-2']

const SELECT_CLASSES =
    'w-full min-w-0 rounded-md border border-input bg-background px-2 py-2 text-sm'

function storageKey(clubId) {
    return `futbot:club:${clubId}:default-team`
}

function loadTeam(clubId, players, behaviours) {
    const initialTeam = {
        formation: FORMATIONS[0],
        slots: Array.from({ length: 6 }, (_, index) => ({
            playerId: String(players[index]?.id ?? ''),
            behaviourId: String(players[index]?.behaviorId ?? ''),
        })),
    }

    try {
        const saved = JSON.parse(localStorage.getItem(storageKey(clubId)))

        if (!Array.isArray(saved?.slots) || saved.slots.length !== 6) {
            return initialTeam
        }

        return {
            formation: FORMATIONS.includes(saved.formation)
                ? saved.formation
                : FORMATIONS[0],
            slots: saved.slots.map((slot) => ({
                playerId: players.some(
                    (player) => String(player.id) === slot?.playerId
                ) ? slot.playerId : '',
                behaviourId: behaviours.some(
                    (behaviour) => String(behaviour.id) === slot?.behaviourId
                ) ? slot.behaviourId : '',
            })),
        }
    } catch {
        return initialTeam
    }
}

export default function TeamSettings({ clubId, players, behaviours }) {
    const [team, setTeam] = useState(
        () => loadTeam(clubId, players, behaviours)
    )
    const [error, setError] = useState('')
    const [success, setSuccess] = useState('')

    function clearFeedback() {
        setError('')
        setSuccess('')
    }

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

    function handleSubmit(event) {
        event.preventDefault()
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

        try {
            localStorage.setItem(storageKey(clubId), JSON.stringify(team))
            setSuccess('Equipo guardado en este navegador.')
        } catch {
            setError('No se pudo guardar el equipo en este navegador.')
        }
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
                            {FORMATIONS.map((formation) => (
                                <option key={formation} value={formation}>
                                    {formation}
                                </option>
                            ))}
                        </select>
                    </div>

                    {team.slots.map((slot, index) => (
                        <fieldset
                            key={index}
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
                        disabled={players.length < 6 || behaviours.length === 0}
                    >
                        Guardar equipo
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