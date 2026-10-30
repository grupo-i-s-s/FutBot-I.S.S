export const isTerminal = (snapshot) => ['FINISHED', 'CANCELLED'].includes(snapshot?.state?.status);

const integer = (value) => Number.isSafeInteger(value) && value >= 0;
const positive = (value) => Number.isFinite(value) && value > 0;
const entity = (value) => value && Number.isFinite(value.x) && Number.isFinite(value.y) && positive(value.radius);
export const isPaused = (state) =>
    state?.status === 'RUNNING'
    && ['HYDRATION_BREAK', 'HALF_BREAK'].includes(state.phase);

function validBreakState(state) {
    if (!state || typeof state !== 'object') return false;

    const fields = ['phase', 'breakIndex', 'breakRemainingMs'];
    const hasBreakFields = fields.some((field) =>
        Object.hasOwn(state, field)
    );

    if (!hasBreakFields) return true;

    if (!fields.every((field) => Object.hasOwn(state, field))) {
        return false;
    }

    if (!integer(state.breakRemainingMs)) return false;

    if (state.phase === 'PLAYING') {
        return state.breakIndex === null
            && state.breakRemainingMs === 0;
    }

    if (!isPaused(state) || state.breakRemainingMs <= 0) {
        return false;
    }

    if (state.phase === 'HALF_BREAK') {
        return state.breakIndex === 2;
    }

    return state.breakIndex === 1 || state.breakIndex === 3;
}

// HTTP y WebSocket comparten contrato. Validar antes de dibujar evita mezclar
// partidos o interpretar una versión incompatible como posiciones válidas.
export function validateSnapshot(snapshot, matchId) {
    const state = snapshot?.state;
    const field = state?.field;
    const teams = state?.teams;
    const players = state?.players;
    const valid = snapshot?.schemaVersion === 1 && snapshot.type === 'match.snapshot'
        && snapshot.matchId === matchId && integer(snapshot.sequence)
        && typeof snapshot.sentAt === 'string'
        && ['WAITING', 'RUNNING', 'FINISHED', 'CANCELLED'].includes(state?.status)
        && validBreakState(state)
        && integer(state.clockMs) && integer(state.durationMs) && state.durationMs > 0
        && state.clockMs <= state.durationMs
        && positive(field?.width) && positive(field?.height) && positive(field?.goalWidth)
        && field.goalWidth < field.height
        && Array.isArray(teams) && teams.length >= 1 && teams.length <= 2
        && teams.every((team) => integer(team.id) && team.id > 0 && typeof team.name === 'string'
            && ['LEFT', 'RIGHT'].includes(team.side) && integer(team.score))
        && new Set(teams.map((team) => team.id)).size === teams.length
        && new Set(teams.map((team) => team.side)).size === teams.length
        && Array.isArray(players) && new Set(players.map((player) => player?.id)).size === players.length
        && players.every((player) => entity(player) && integer(player.id) && player.id > 0
            && typeof player.name === 'string' && teams.some((team) => team.id === player.teamId))
        && (state.ball === null || entity(state.ball))
        && (state.status !== 'WAITING' || (players.length === 0 && state.ball === null))
        && (!['RUNNING', 'FINISHED'].includes(state.status)
            || (teams.length === 2 && state.ball !== null && teams.every((team) => players.filter((player) => player.teamId === team.id).length === 4)));
    if (!valid) throw new Error('El servidor envió un estado de partido incompatible.');
    return snapshot;
}
