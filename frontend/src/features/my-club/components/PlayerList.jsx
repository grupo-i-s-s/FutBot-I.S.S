import {Users} from 'lucide-react';
import {Avatar, AvatarFallback} from '@/components/ui/avatar';
import {Card, CardContent, CardDescription, CardHeader, CardTitle} from '@/components/ui/card';
import {Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle} from '@/components/ui/empty';
import {Item, ItemContent, ItemDescription, ItemMedia, ItemTitle} from '@/components/ui/item';

export default function PlayerList({players}) {
    return (
        <Card>
            <CardHeader>
                <CardTitle className="flex items-center gap-2 text-lg font-bold">
                    <Users className="size-5" aria-hidden="true"/>
                    Jugadores
                </CardTitle>
                <CardDescription>{players.length} jugadores en el plantel</CardDescription>
            </CardHeader>
            <CardContent>
                {players.length === 0 ? (
                    <Empty className="border">
                        <EmptyHeader>
                            <EmptyMedia variant="icon">
                                <Users/>
                            </EmptyMedia>
                            <EmptyTitle>Sin jugadores</EmptyTitle>
                            <EmptyDescription>El club todavía no tiene jugadores.</EmptyDescription>
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
                                        <ItemTitle className="truncate">{player.name}</ItemTitle>
                                        <ItemDescription>
                                            <span className="sr-only">Comportamiento: </span>
                                            {player.behaviourName}
                                        </ItemDescription>
                                    </ItemContent>
                                </Item>
                            </li>
                        ))}
                    </ul>
                )}
            </CardContent>
        </Card>
    );
}