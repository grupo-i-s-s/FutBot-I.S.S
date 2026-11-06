import MatchCanvas from '../friendly-matches/components/MatchCanvas.jsx';
import './BehaviourTest.css';

const testSnapshot = {
    state: {
        field: { width: 100, height: 60, goalWidth: 15 },
        teams: [
            { id: 1, color: '#2563eb', score: 0, side: 'LEFT' },
            { id: 2, color: '#dc2626', score: 0, side: 'RIGHT' },
        ],
        players: [
            { id: 1, teamId: 1, x: 24, y: 18, radius: 1.5 },
            { id: 2, teamId: 1, x: 18, y: 30, radius: 1.5 },
            { id: 3, teamId: 1, x: 24, y: 42, radius: 1.5 },
            { id: 4, teamId: 2, x: 76, y: 18, radius: 1.5 },
            { id: 5, teamId: 2, x: 82, y: 30, radius: 1.5 },
            { id: 6, teamId: 2, x: 76, y: 42, radius: 1.5 },
        ],
        ball: { x: 50, y: 30, radius: 0.5 },
    },
};

export default function BehaviourTest() {
    return (
        <main className="match-page">
            <div className="match-page-content">
                <MatchCanvas snapshot={testSnapshot} live={false} />
            </div>
        </main>
    );
}