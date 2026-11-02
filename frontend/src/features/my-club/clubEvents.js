const CLUB_UPDATED_EVENT = 'futbot:club-updated';

export function notifyClubUpdated(club) {
    window.dispatchEvent(new CustomEvent(CLUB_UPDATED_EVENT, {detail: club}));
}

export function subscribeToClubUpdates(listener) {
    const handleUpdate = (event) => listener(event.detail);
    window.addEventListener(CLUB_UPDATED_EVENT, handleUpdate);

    return () => window.removeEventListener(CLUB_UPDATED_EVENT, handleUpdate);
}
