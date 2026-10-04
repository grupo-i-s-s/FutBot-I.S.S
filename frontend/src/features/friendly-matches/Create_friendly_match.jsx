import { useState } from 'react'
import './Create_friendly_match.css'
import { create_friendly_match } from './api'


export default function CreateFriendlyMatch(){
    const [createMatch, setCreateMatch] = useState(false);
  
    const [matchTime, setMatchTime] = useState(""); 

    const handleCreateMatch = async (e) => {
        e.preventDefault();                     //Esto evita refrescar la pagina 

        setCreateMatch(true);

        try{
            const response = await create_friendly_match(matchTime)
            console.log("Rta del server", response)
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