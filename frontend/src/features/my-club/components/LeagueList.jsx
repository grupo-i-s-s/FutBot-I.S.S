import {Trophy} from 'lucide-react';
import {Badge} from '@/components/ui/badge';
import {Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle} from '@/components/ui/card';
import {Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle} from '@/components/ui/empty';
import {Item, ItemActions, ItemContent, ItemDescription, ItemGroup, ItemTitle} from '@/components/ui/item';

const LEAGUE_TYPE_LABELS = {
    PUBLIC: 'Pública',
    PRIVATE: 'Privada',
};

export default function LeagueList({leagues, isMock = false}) {
    return (
        <Card>
            <CardHeader>
                <CardTitle className="flex items-center gap-2 text-lg font-bold">
                    <Trophy className="size-5" aria-hidden="true"/>
                    Ligas inscriptas
                </CardTitle>
                <CardDescription>Ligas en las que participa tu club.</CardDescription>
                {isMock && (
                    <CardAction>
                        <Badge variant="outline">Datos de ejemplo</Badge>
                    </CardAction>
                )}
            </CardHeader>
            <CardContent>
                {leagues.length === 0 ? (
                    <Empty className="border">
                        <EmptyHeader>
                            <EmptyMedia variant="icon">
                                <Trophy/>
                            </EmptyMedia>
                            <EmptyTitle>Sin ligas</EmptyTitle>
                            <EmptyDescription>El club no está inscripto en ninguna liga.</EmptyDescription>
                        </EmptyHeader>
                    </Empty>
                ) : (
                    <ItemGroup>
                        {leagues.map((league) => (
                            <Item key={league.id} variant="outline">
                                <ItemContent>
                                    <ItemTitle>{league.name}</ItemTitle>
                                    <ItemDescription>
                                        {LEAGUE_TYPE_LABELS[league.type]} · {league.teams}/{league.maxTeams} equipos
                                    </ItemDescription>
                                </ItemContent>
                                <ItemActions>
                                    <Badge variant="secondary">{league.status}</Badge>
                                </ItemActions>
                            </Item>
                        ))}
                    </ItemGroup>
                )}
            </CardContent>
        </Card>
    );
}