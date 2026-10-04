import { useState } from 'react'
import './Create_friendly_match.css'

export default function CreateFriendlyMatch(){
    const [createMatch, setCreatMatch] = useState(false);
  
    const [matchTime, setMatchTime] = useState(""); 

    const handleCreateMatch = async (e) => {
        e.preventDefault();

        setIsLoading(true);

        try{
            console.log("Esperando a crear el partido a las:", matchTime);
        }
        finally{
            setIsLoading(false);
        }
    }

  return (
    <div className="init-page"> 
      <div className="match-card">
        
        {/* Usamos la clase "title" que tenés en tu CSS */}
        <h2 className="title">A jugar!</h2>

        <form onSubmit={handleCreateMatch}>
          
          {/* Metimos el input adentro del form y usamos "form-group" */}
          <div className="form-group">
            <label htmlFor="horario">
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