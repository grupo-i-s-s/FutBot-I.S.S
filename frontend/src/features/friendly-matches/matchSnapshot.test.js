import {describe, expect, it} from 'vitest';
import {isPaused, validateSnapshot} from './matchSnapshot.js';

function snapshot(overrides = {}) {
    return {
        schemaVersion: 1,
        type: 'match.snapshot',
        matchId: 42,
        sequence: 1,
        sentAt: '2026-10-20T12:00:00Z',
        state: {
            status: 'RUNNING',
            clockMs: 75000,
            durationMs: 300000,
            phase: 'PLAYING',
            breakIndex: null,
            breakRemainingMs: 0,
            field: {
                width: 100,
                height: 60,
                goalWidth: 15,
            },
            teams: [
                {id: 1, name: 'Local', side: 'LEFT', score: 0},
                {id: 2, name: 'Visitante', side: 'RIGHT', score: 0},
            ],
            players: Array.from({length: 6}, (_, index) => ({
                id: index + 1,
                teamId: index < 3 ? 1 : 2,
                name: `Jugador ${index}`,
                x: 20 + index,
                y: 30,
                radius: 1.4,
            })),
            ball: {x: 50, y: 30, radius: 0.5},
            ...overrides,
        },
    };
}

describe('Pausas del partido', () => {
    it.each([
        ['HYDRATION_BREAK', 1],
        ['HALF_BREAK', 2],
        ['HYDRATION_BREAK', 3],
    ])('acepta %s en la pausa %s', (phase, breakIndex) => {
        const payload = snapshot({
            phase,
            breakIndex,
            breakRemainingMs: 15000,
        });

        expect(validateSnapshot(payload, 42)).toBe(payload);
        expect(isPaused(payload.state)).toBe(true);
    });

    it('acepta el juego activo', () => {
        const payload = snapshot();

        expect(validateSnapshot(payload, 42)).toBe(payload);
        expect(isPaused(payload.state)).toBe(false);
    });

    it('acepta snapshots anteriores sin metadatos de pausa', () => {
        const payload = snapshot();

        delete payload.state.phase;
        delete payload.state.breakIndex;
        delete payload.state.breakRemainingMs;

        expect(validateSnapshot(payload, 42)).toBe(payload);
        expect(isPaused(payload.state)).toBe(false);
    });

    it.each([
        {phase: 'HALF_BREAK', breakIndex: 1, breakRemainingMs: 15000},
        {phase: 'HYDRATION_BREAK', breakIndex: 2, breakRemainingMs: 15000},
        {phase: 'HYDRATION_BREAK', breakIndex: 1, breakRemainingMs: 0},
        {phase: 'PLAYING', breakIndex: null, breakRemainingMs: 1000},
        {
            status: 'FINISHED',
            phase: 'HALF_BREAK',
            breakIndex: 2,
            breakRemainingMs: 1000,
        },
    ])('rechaza metadatos inconsistentes: %j', (overrides) => {
        expect(() => validateSnapshot(snapshot(overrides), 42))
            .toThrow('incompatible');
    });
});
