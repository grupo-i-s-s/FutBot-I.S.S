import './Matches.css'
import { Button } from '@/components/ui/button';
import {useState, useEffect} from 'react';
import { joinFriendlyMatch, listFriendlyMatches } from './api';
import { Card } from '@/components/ui/card';
import {useNavigate} from "react-router";

export default function MatchesPage() {
      
        const [partidosDisponibles, setPartidosDisponibles] = useState([])
        const [partidosUnidos, setPartidosUnidos] = useState([])
        const [loading, setLoading] = useState(true)
        const [error, setError] = useState('')
        const navigate = useNavigate()


        useEffect(() => {
            const controller = new AbortController()

            async function cargarPartidos() {
                try {
                    const datos = await listFriendlyMatches(controller.signal)
                    if (!controller.signal.aborted) setPartidosDisponibles(datos)
                } catch (error) {
                    if (!controller.signal.aborted) setError(error.message)
                } finally {
                    if (!controller.signal.aborted) setLoading(false)
                }
            }

            cargarPartidos()
            return () => controller.abort()
        }, [])


        async function handleJoinMatch(matchId) {
            const response = await joinFriendlyMatch(matchId)
            
            setPartidosDisponibles(partidosDisponibles.filter(partido => partido.matchId != matchId))
            console.log(response)
            console.log(response.status)

            setPartidosUnidos([...partidosUnidos, matchId])
            navigate('/partidos/' + matchId , { replace: true })
        }

    return (
        <main className="Friendly-Matches">
           <Card className="main-card">
                <h1 className = "page-title"> A JUGAR !</h1>
                {loading && <p role="status">Cargando partidos…</p>}
                {error && <p role="alert">{error}</p>}
                {!loading && !error && partidosDisponibles.length === 0 && (
                    <p role="status">No hay partidos disponibles.</p>
                )}
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
