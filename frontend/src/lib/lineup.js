export function swapAssignedPlayer(slots, targetIndex, playerId) {
    if (!playerId) return null;

    const sourceIndex = slots.findIndex((slot, index) =>
        index !== targetIndex && slot.playerId === playerId,
    );
    if (sourceIndex === -1) return null;

    const swapped = [...slots];
    swapped[targetIndex] = slots[sourceIndex];
    swapped[sourceIndex] = slots[targetIndex];
    return swapped;
}
