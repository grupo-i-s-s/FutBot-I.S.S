
import './Matches.css'
import { Button } from '@/components/ui/button';
import {useState} from 'react';
import { join_friendly_match } from './api';
import { Card } from '@/components/ui/card';

export default function MatchesPage() {
        const partidosDisponibles = [
            { idPartido: 1, equipoA: "Los Pibes FC", idEquipoA: 1,fecha: "30 Sep - 20:00hs" },
            { idPartido: 2, equipoA: "La 12", idEquipoA: 2, fecha: "01 Oct - 19:00hs" },
            { idPartido: 3, equipoA: "Veteranos", idEquipoA:3, fecha: "03 Oct - 21:00hs"}
        ];

        const [partidosUnidos, setPartidosUnidos] = useState([])

        async function handleJoinMatch(idPartido, idEquipoA) {
            const response = await join_friendly_match(idPartido, idEquipoA)
            console.log(response)
            console.log(response.status)

            setPartidosUnidos([...partidosUnidos, idPartido])
        }

    return (
        <main className="Friendly-Matches">
           <Card className="main-card">
                <h1 className = "page-title"> Partidos Amistosos</h1>
                <div className = "container"> 
                    {partidosDisponibles.map((partido) => (
                        <div key={partido.idPartido} className="match-box">
                            <span className = "match-title">
                                {partido.equipoA}
                            </span>
                            <span className = "match-date">
                                {partido.fecha}
                            </span>
                            <Button className = "join-button" onClick={() => handleJoinMatch(partido.idPartido, 2)}>
                                Unirse
                            </Button>
                        </div>
                    ))}
                </div>
            </Card>
        </main>
    );
}