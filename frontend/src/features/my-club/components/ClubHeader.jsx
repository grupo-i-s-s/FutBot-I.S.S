import {Handshake, Settings} from 'lucide-react';
import {Badge} from '@/components/ui/badge';
import {Button} from '@/components/ui/button';
import {Card, CardContent} from '@/components/ui/card';
import ClubAvatar from './ClubAvatar';

export default function ClubHeader({club, onSettingsClick}) {
    return (
        <Card>
            <CardContent className={'flex items-start gap-4 sm:items-center'}>
                <ClubAvatar avatar={club.avatar} clubName={club.name}/>
                <div className="min-w-0 flex-1 space-y-2">
                    <p className="text-xs font-bold tracking-[0.12em] text-muted-foreground">MI CLUB</p>
                    <h1 className="text-2xl font-bold break-words sm:text-3xl">{club.name}</h1>
                    <Badge variant={club.friendlyAvailable ? 'default' : 'secondary'}>
                        <Handshake data-icon="inline-start" aria-hidden="true"/>
                        {club.friendlyAvailable ? 'Disponible para amistosos' : 'No disponible para amistosos'}
                    </Badge>
                </div>
                <Button
                    variant="ghost"
                    size="icon-lg"
                    onClick={onSettingsClick}
                    aria-label="Configurar club"
                    title="Configurar club">
                    <Settings className="size-5"/>
                </Button>
            </CardContent>
        </Card>
    );
}