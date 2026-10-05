import './Matches.css'
import { Button } from '@/components/ui/button';
import {useState, useEffect} from 'react';
import { joinFriendlyMatch, listFriendlyMatches } from './api';
import { Card } from '@/components/ui/card';

export default function MatchesPage() {
      
        const [partidosDisponibles, setPartidosDisponibles] = useState([])
        const [partidosUnidos, setPartidosUnidos] = useState([])
        useEffect(() => {listFriendlyMatches().then((datos => {setPartidosDisponibles(datos)}))}, []) // Esto me carga todos los partidos disponibles una vez al entrar.


        async function handleJoinMatch(matchId) {
            const response = await joinFriendlyMatch(matchId)
            
            setPartidosDisponibles(partidosDisponibles.filter(partido => partido.matchId != idPartido))
            console.log(response)
            console.log(response.status)

            setPartidosUnidos([...partidosUnidos, matchId])
        }

    return (
        <main className="Friendly-Matches">
           <Card className="main-card">
                <h1 className = "page-title"> Partidos Amistosos</h1>
                <div className = "container"> 
                    {partidosDisponibles.map((partido) => (
                        <div key={partido.matchId} className="match-box">
                            <span className = "match-title">
                                {partido.creatorClubName}
                            </span>
                            <span className = "match-date">
                                {partido.startDateTime}
                            </span>
                            <Button className = "join-button" onClick={() => handleJoinMatch(partido.matchId)}>
                                Unirse
                            </Button>
                        </div>
                    ))}
                </div>
            </Card>
        </main>
    );
}