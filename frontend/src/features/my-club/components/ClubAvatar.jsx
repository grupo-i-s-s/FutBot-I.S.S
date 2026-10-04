import {Avatar, AvatarFallback} from "@/components/ui/avatar";
import {findAvatar} from '../avatars';

const SIZE_CLASSES = {
    md: 'size-12 text-base',
    lg: 'size-20 text-2xl'
};

const ICON_SIZE_CLASSES = {
    md: 'size-6',
    lg: 'size-10'
};

function getInitials(name = '') {
    return name
        .split(' ')
        .filter(Boolean)
        .slice(0, 2)
        .map((word) => word[0].toUpperCase())
        .join('');
}

export default function ClubAvatar({avatar, clubName, size = 'lg'}) {
    const option = findAvatar(avatar);

    return (
        <Avatar className={SIZE_CLASSES[size]}
                aria-label={option ? `Avatar: ${option.label}` : `Avatar de ${clubName}`}>

            <AvatarFallback className={`font-bold ${option?.className ?? 'bg-primary text-primary-foreground'}`}>
                {option ? <option.Icon className={ICON_SIZE_CLASSES[size]}
                                       aria-hidden="true"/> : getInitials(clubName) || '?'}
            </AvatarFallback>

        </Avatar>
    );
}