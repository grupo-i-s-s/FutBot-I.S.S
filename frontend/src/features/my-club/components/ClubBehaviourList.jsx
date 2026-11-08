import {Link} from 'react-router';
import {buttonVariants} from '@/components/ui/button';
import {Card, CardContent, CardDescription, CardHeader, CardTitle} from '@/components/ui/card';
import {Empty, EmptyDescription, EmptyHeader, EmptyTitle} from '@/components/ui/empty';
import {Item, ItemContent, ItemDescription, ItemFooter, ItemTitle} from '@/components/ui/item';

export default function ClubBehaviourList({behaviours}) {
    return (
        <Card>
            <CardHeader className="flex flex-wrap items-start justify-between gap-3">
                <div className="space-y-1">
                    <CardTitle className="text-lg font-bold">Comportamientos</CardTitle>
                    <CardDescription>Catálogo de comportamientos de tu club.</CardDescription>
                </div>
                <Link to="/behaviours" className={buttonVariants({variant: 'outline', size: 'sm'})}>
                    Gestionar comportamientos
                </Link>
            </CardHeader>
            <CardContent>
                {behaviours.length === 0 ? (
                    <Empty className="border">
                        <EmptyHeader>
                            <EmptyTitle>Sin comportamientos</EmptyTitle>
                            <EmptyDescription>El club todavía no tiene comportamientos.</EmptyDescription>
                        </EmptyHeader>
                    </Empty>
                ) : (
                    <ul className="grid gap-3 sm:grid-cols-2">
                        {behaviours.map((behaviour) => (
                            <Item key={behaviour.id} render={<li/>} variant="outline">
                                <ItemContent className="min-w-0">
                                    <ItemTitle className="max-w-full wrap-anywhere">{behaviour.name}</ItemTitle>
                                    <ItemDescription className="wrap-anywhere">
                                        {behaviour.description || 'Sin descripción.'}
                                    </ItemDescription>
                                </ItemContent>
                                <ItemFooter>
                                    <Link
                                        to={`/behaviours/${behaviour.id}`}
                                        className={buttonVariants({variant: 'outline', size: 'sm'})}
                                        aria-label={`Ver detalle de ${behaviour.name}`}
                                    >
                                        Ver detalle
                                    </Link>
                                </ItemFooter>
                            </Item>
                        ))}
                    </ul>
                )}
            </CardContent>
        </Card>
    );
}
