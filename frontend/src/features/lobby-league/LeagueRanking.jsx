import React, { useEffect, useState } from 'react';
import './LeagueRanking.css'; // Reutilizamos los mismos estilos si aplican

export default function GlobalRanking() {
    const [rankData, setRankData] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        async function fetchGlobalRanking() {
            try {
                const response = await fetch("http://localhost:8000/ranking-global", {
                    credentials: "include",
                    headers: {
                        "x-futbot-request": "1"
                    }
                });
                if (!response.ok) throw new Error("No se pudo cargar el ranking global.");
                const data = await response.json();
                setRankData(data.items);
            } catch (err) {
                setError(err.message);
            } finally {
                setLoading(false);
            }
        }
        fetchGlobalRanking();
    }, []);

    if (loading) return <div className="lobby-card text-center p-6">Cargando ranking global...</div>;
    if (error) return <div className="lobby-card text-center p-6 text-red-500">{error}</div>;

    return (
        <div className="lobby-card">
            <h2>Ranking Global</h2>
            <div className="ranking-table">
                <div className="ranking-header">
                    <span className="col-pos">#</span>
                    <span className="col-club">Club</span>
                    <span className="col-stat">Pts</span>
                    <span className="col-stat">PJ</span>
                    <span className="col-stat">PG</span>
                    <span className="col-stat">PE</span>
                    <span className="col-stat">PP</span>
                    <span className="col-stat">DG</span>
                </div>

                <div className="ranking-body">
                    {rankData.map((club, index) => (
                        <div className="ranking-row" key={index}>
                            <span className="col-pos">{index + 1}</span>
                            <span className="col-club">{club.name}</span>
                            <span className="col-stat font-bold">{club.points}</span>
                            <span className="col-stat">{club.played}</span>
                            <span className="col-stat">{club.wins}</span>
                            <span className="col-stat">{club.draws}</span>
                            <span className="col-stat">{club.losses}</span>
                            <span className="col-stat">{club.dg}</span>
                        </div>
                    ))}
                    {rankData.length === 0 && (
                        <div className="p-4 text-center text-gray-400">
                            Todavía no hay registros en el ranking global.
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
}