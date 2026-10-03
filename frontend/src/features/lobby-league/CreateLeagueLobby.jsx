import './LeagueLobby.css';

export function LeagueLobby() {

  const lobby = 1;
  return (
    <div className="lobby-container">
      <header className="lobby-header">
        <h1>Liga #</h1>
        <span className="status">
          estado
        </span>
      </header>

      <div className="lobby-card">
        <h2>Detalles del Lobby</h2>
        <div className="info-grid">
          <div className="info-item">
            <span>Nombre:</span>
            <strong>#</strong>
          </div>
          <div className="info-item">
            <span>Creador:</span>
            <strong>#</strong>
          </div>
          <div className="info-item">
            <span>Maximo de participantes:</span>
            <strong>#</strong>
          </div>
          <div className="info-item">
            <span>Formato:</span>
            <strong>#</strong>
          </div>
          <div className="info-item">
            <span>Hora:</span>
            <strong>#</strong>
          </div>
        </div>
      </div>

      <div className="lobby-card">
        <h2>Jugadores Inscriptos (#)</h2>
        <div className="player-list">
          <span>[Lista de jugadores]</span>
        </div>
      </div>

      <div className="leave-league">
        <button> Abandonar Liga </button>
      </div>
    </div>
  );
}

export default LeagueLobby;