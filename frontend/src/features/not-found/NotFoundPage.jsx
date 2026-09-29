import {Link} from 'react-router';
import {SearchX} from 'lucide-react';
import {Button} from '@/components/ui/button';
import {
    Empty,
    EmptyContent,
    EmptyDescription,
    EmptyHeader,
    EmptyMedia,
    EmptyTitle,
} from '@/components/ui/empty';

export default function NotFoundPage() {
    return (
        <main className="mx-auto w-[calc(100%_-_32px)] max-w-md py-16">
            <Empty className="border bg-white">
                <EmptyHeader>
                    <EmptyMedia variant="icon">
                        <SearchX/>
                    </EmptyMedia>
                    <EmptyTitle>Página no encontrada</EmptyTitle>
                    <EmptyDescription>La dirección que ingresaste no existe.</EmptyDescription>
                </EmptyHeader>
                <EmptyContent>
                    <Button nativeButton={false} render={<Link to="/mi-club" />}>Ir a Mi club</Button>
                </EmptyContent>
            </Empty>
        </main>
    );
}