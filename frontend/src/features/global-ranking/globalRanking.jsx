import React, { useEffect, useState } from 'react';
import { getGlobalRanking } from './api.js';
import '../lobby-league/LeagueRanking.css';

export default function GlobalRanking() {
    const [rankData, setRankData] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const controller = new AbortController();
        async function fetchRank() {
            try {
                const data = await getGlobalRanking(controller.signal);
                if (!controller.signal.aborted) {
                    setRankData(data.items);
                }
            } catch (err) {
                if (!controller.signal.aborted) {
                    setError(err);
                }
            } finally {
                if (!controller.signal.aborted) {
                    setLoading(false);
                }
            }
        }
        fetchRank();
        return () => controller.abort();
    }, []);

    if (loading) return <div className="lobby-card">Cargando ranking global...</div>;
    if (error) return <div className="lobby-card text-red-500">No se pudo cargar el ranking global.</div>;

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