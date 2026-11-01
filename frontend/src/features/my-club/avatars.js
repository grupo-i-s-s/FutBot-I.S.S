export const DEFAULT_AVATAR = 'avatar-01.png';

export const AVATAR_OPTIONS = Array.from({length: 20}, (_, index) => {
    const number = String(index + 1).padStart(2, '0');
    const filename = `avatar-${number}.png`;

    return {
        key: filename,
        label: `Escudo ${number}`,
        src: `/avatars/${filename}`,
    };
});

export function findAvatar(filename) {
    return AVATAR_OPTIONS.find((option) => option.key === filename);
}