import { Avatar, AvatarFallback, AvatarImage} from '@/components/ui/avatar';
import {DEFAULT_AVATAR, findAvatar} from '../avatars';

const SIZE_CLASSES = {
    md: 'size-12 text-base',
    lg: 'size-20 text-2xl',
};

function getInitials(name = '') {
    return (name ?? '')
        .split(' ')
        .filter(Boolean)
        .slice(0, 2)
        .map((word) => word[0].toUpperCase())
        .join('');
}

export default function ClubAvatar({avatar, clubName, size = 'lg'}) {
    const option = findAvatar(avatar) ?? findAvatar(DEFAULT_AVATAR);

    return (
        <Avatar
            role="img"
            aria-label={clubName ? `Escudo de ${clubName}` : option.label}
            className={`${SIZE_CLASSES[size] ?? SIZE_CLASSES.lg} rounded-none after:hidden`}
        >
            <AvatarImage
                src={option.src}
                alt=""
                className="rounded-none object-contain"
            />

            <AvatarFallback className="rounded-none bg-transparent font-bold text-primary">
                {getInitials(clubName) || '?'}
            </AvatarFallback>
        </Avatar>
    );
}