import './CreatePlayersPage.css';
import { useState } from 'react';
import './CreatePlayersPage.css';

async function handleSubmit(event) {
    event.preventDefault()
    const response = await register(name)
    console.log(response)
    console.log(response.status)
}

export default function CreatePlayerPage() {
    const [name, setName] = useState('');
    const [power, setPower] = useState(60);
    const [agility, setAgility] = useState(60);
    const [control, setControl] = useState(60);
    const [speed, setSpeed] = useState(60);
    const [strength, setStrength] = useState(60);
    const handleSubmit = (event) => { event.preventDefault(); };

    const totalPoints = power + agility + control + speed + strength;

    return (
    <main className="create-players-page"> 
        <h1 className="main-page-title">Crear Jugador</h1>
        <section className="name-card">
        <form onSubmit={handleSubmit}>
            <div className="formulary-box">
                <input  
                id="user-name" 
                type="text" 
                placeholder="Nombre" 
                value={name}
                onChange={(event) => setName(event.target.value)}/>
            </div>

            <div className="attribute-header">
                <label htmlFor="power-range">Potencia</label>
                <span className="attribute-value">{power}</span>
            </div>
            <input 
                id="power"
                className="slider"
                type="range" 
                min="20" 
                max="100" 
                value={power}
                onChange={(event) => setPower(Number(event.target.value))}/>

            <div className="attribute-header">
                <label htmlFor="power-range">Agilidad</label>
                <span className="attribute-value">{agility}</span>
            </div>
            <input 
                id="agility"
                className="slider"
                type="range" 
                min="20" 
                max="100" 
                value={agility}
                onChange={(event) => setAgility(Number(event.target.value))}/>

            <div className="attribute-header">
                <label htmlFor="power-range">Control</label>
                <span className="attribute-value">{control}</span>
            </div>
            <input 
                id="control"
                className="slider"
                type="range" 
                min="20" 
                max="100" 
                value={control}
                onChange={(event) => setControl(Number(event.target.value))}/>

            <div className="attribute-header">
                <label htmlFor="power-range">Velocidad</label>
                <span className="attribute-value">{speed}</span>
            </div>
            <input 
                id="speed"
                className="slider"
                type="range" 
                min="20" 
                max="100" 
                value={speed}
                onChange={(event) => setSpeed(Number(event.target.value))}/>
            
            <div className="attribute-header">
                <label htmlFor="power-range">Fuerza</label>
                <span className="attribute-value">{strength}</span>
            </div>
            <input 
                id="strength"
                className="slider"
                type="range" 
                min="20" 
                max="100" 
                value={strength}
                onChange={(event) => setStrength(Number(event.target.value))}/>

            <div className="total-box">
                <span className="total-label">Puntos Totales:</span>
                <span className="total-value">{totalPoints}</span>
            </div>

            <button type="submit" className="register-button"> Confirmar </button>
        </form>
        </section>
    </main>
  );
}