import { useState } from 'react'
import './Create_friendly_match.css'
import { createFriendlyMatch } from './api'
import { useNavigate } from 'react-router'


export default function CreateFriendlyMatch(){
    const [createMatch, setCreateMatch] = useState(false);
    const navigate = useNavigate()
    const [matchTime, setMatchTime] = useState(""); 

    const handleCreateMatch = async (e) => {
        e.preventDefault();                     //Esto evita refrescar la pagina 

        setCreateMatch(true);

        try{
            const response = await createFriendlyMatch(matchTime)
            console.log("Rta del server", response)
            navigate('/home', { replace: true })
        }
        finally{
            setCreateMatch(false);
        }
    }

  return (
    <div className="init-page"> 
      <div className="match-card">

        <h2 className="title">A jugar!</h2>

        <form onSubmit={handleCreateMatch}>
          <div className="form-group">
            <label>
                Horario para comenzar el partido
            </label>
            <input 
              type="datetime-local" 
              id="horario"
              value={matchTime}
              onChange={(e) => setMatchTime(e.target.value)}
              required
            />
          </div>
          <button 
            type="submit" 
            className="login-button" 
            disabled={createMatch|| !matchTime}
          >
            {createMatch ? "Creando partido..." : "Crear Partido"}
          </button>

        </form>
      </div>
    </div>
  );
}