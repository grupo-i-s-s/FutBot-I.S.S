import React from 'react';
import './LeagueRanking.css';

export default function LeagueRanking() {
    // 1. Datos de prueba simulando lo que vendrá del backend
    const clubesRanking = [
        { id: 1, nombre: 'fidodidofc', puntos: 12, pj: 4, pg: 4, pe: 0, pp: 0, dg: 8 },
        { id: 2, nombre: 'tintinfc', puntos: 9, pj: 4, pg: 3, pe: 0, pp: 1, dg: 5 },
        { id: 3, nombre: 'feliputo', puntos: 4, pj: 4, pg: 1, pe: 1, pp: 2, dg: -2 }
    ];

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
                    {clubesRanking.map((club, index) => (
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