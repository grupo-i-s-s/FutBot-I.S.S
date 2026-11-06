export default function BehaviourTest() {
    return (
        <main className="match-page">
            <div className="match-page-content">
                <div><p className="match-eyebrow">AMISTOSO · {matchId}</p><h1>El partido</h1></div>
                <Link to="/partidos-disponibles">Volver a amistosos</Link>
            </div>
        </main>
    );
}