import { Users, Plus } from 'lucide-react'
import { Link } from 'react-router'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from '@/components/ui/empty'
import { Item, ItemContent, ItemDescription, ItemMedia, ItemTitle } from '@/components/ui/item'
import { BehaviorSelector } from './BehaviorSelector'
import { buttonVariants } from '@/components/ui/button'

const PACSS_ATTRIBUTES = [
    ['Power', 'power'],
    ['Agility', 'agility'],
    ['Control', 'control'],
    ['Speed', 'speed'],
    ['Strength', 'strength'],
]

export default function PlayerList({ players, behaviours, onBehaviourAssigned }) {
    return (
        <Card>
            <CardHeader>
                <CardTitle className="flex items-center gap-2 text-lg font-bold">
                    <Users className="size-5" aria-hidden="true" />
                    Jugadores
                </CardTitle>
                <CardDescription>{players.length} jugadores en el plantel</CardDescription>

                <CardAction>
                    <Link to="/crear-jugador" className={buttonVariants({ size: 'sm' })}>
                        <Plus className="size-4" aria-hidden="true"/>
                        Crear Nuevo jugador
                    </Link>
                </CardAction>
            </CardHeader>

            <CardContent>
                {players.length === 0 ? (
                    <Empty className="border">
                        <EmptyHeader>
                            <EmptyMedia variant="icon">
                                <Users />
                            </EmptyMedia>
                            <EmptyTitle>Sin jugadores</EmptyTitle>
                            <EmptyDescription>
                                El club todavía no tiene jugadores.
                            </EmptyDescription>
                        </EmptyHeader>
                    </Empty>
                ) : (
                    <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
                        {players.map((player) => (
                            <li key={player.id}>
                                <Item variant="outline">
                                    <ItemMedia>
                                        <Avatar>
                                            <AvatarFallback className="font-bold text-primary">
                                                {player.name.charAt(0).toUpperCase()}
                                            </AvatarFallback>
                                        </Avatar>
                                    </ItemMedia>

                                    <ItemContent className="min-w-0">
                                        <ItemTitle className="truncate">
                                            {player.name}
                                        </ItemTitle>

                                        <div className="grid grid-cols-2 gap-x-4 gap-y-1 mt-2 text-sm">
                                            {PACSS_ATTRIBUTES.map(([label, key]) => (
                                                <span key={key}>
                                                    <strong>{label}:</strong> {player[key]}
                                                </span>
                                            ))}
                                        </div>

                                        <ItemDescription className="mt-2">
                                            <span className="font-medium">
                                                Comportamiento:
                                            </span>{' '}
                                            {player.behaviourName}
                                        </ItemDescription>

                                        <BehaviorSelector
                                            player={player}
                                            behaviours={behaviours}
                                            onBehaviourAssigned={onBehaviourAssigned}
                                        />
                                    </ItemContent>
                                </Item>
                            </li>
                        ))}
                    </ul>
                )}
            </CardContent>
        </Card>
    )
}
