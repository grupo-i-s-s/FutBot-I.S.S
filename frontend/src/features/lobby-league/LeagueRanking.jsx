import React, {useEffect, useState} from 'react';
import { getLeagueRanking } from './api.js';
import './LeagueRanking.css';

export default function LeagueRanking({leagueId}) {
    const[rankData, setRankData] = useState([]);
    
    useEffect(() => {
                    async function rank() {
                        const rank = await getLeagueRanking(leagueId);  
                        setRankData(rank)
                    }
                    rank()    
                    }, [leagueId]);

    return (
        <div className="lobby-card">
            <h2>Ranking de la Liga</h2>
            
            {/* 2. Estructura de la tabla */}
            <div className="ranking-table">
                {/* Encabezados */}
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

                {/* 3. Filas de datos (Iteración) */}
                <div className="ranking-body">
                    {rankData.map((club, index) => (
                        <div className="ranking-row" key={club.id}>
                            <span className="col-pos">{index + 1}</span>
                            <span className="col-club">{club.nombre}</span>
                            <span className="col-stat font-bold">{club.puntos}</span>
                            <span className="col-stat">{club.pj}</span>
                            <span className="col-stat">{club.pg}</span>
                            <span className="col-stat">{club.pe}</span>
                            <span className="col-stat">{club.pp}</span>
                            <span className="col-stat">{club.dg}</span>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}