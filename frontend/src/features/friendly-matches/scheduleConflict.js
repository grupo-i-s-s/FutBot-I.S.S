const scheduleFormatter = new Intl.DateTimeFormat('es-AR', {
    dateStyle: 'medium',
    timeStyle: 'short',
    hourCycle: 'h23',
});

export function friendlyMatchError(error, fallback) {
    const message = error.message || fallback;
    if (error.code !== 'LEAGUE_SCHEDULE_CONFLICT') return message;

    const {conflictStart, conflictEnd} = error.fields ?? {};
    if (typeof conflictStart !== 'string' || typeof conflictEnd !== 'string') return message;

    const start = new Date(conflictStart);
    const end = new Date(conflictEnd);
    if (!(start < end)) return message;

    return `${message} La franja ocupada es ${scheduleFormatter.formatRange(start, end)}.`;
}
