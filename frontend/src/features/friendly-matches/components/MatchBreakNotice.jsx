import {isPaused} from '../matchSnapshot.js';

export function breakLabel(state) {
    if (state.phase === 'HALF_BREAK') return 'Entretiempo';

    return state.breakIndex === 1
        ? 'Primera pausa de hidratación'
        : 'Segunda pausa de hidratación';
}

export default function MatchBreakNotice({state, connected}) {
    if (!isPaused(state)) return null;

    const seconds = Math.ceil(state.breakRemainingMs / 1000);

    return (
        <section className="match-break-notice" role="status">
            <p className="match-break-title">
                {breakLabel(state)}
            </p>

            <p className="match-break-countdown">
                {seconds} s
            </p>

            <p>
                {connected
                    ? 'El partido se reanuda automáticamente.'
                    : 'Tiempo restante según la última actualización recibida.'}
            </p>
        </section>
    );
}