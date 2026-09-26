import { useEffect, useState } from 'react'

export default function App() {
  const [status, setStatus] = useState('checking')
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    const timeout = setTimeout(() => controller.abort(), 8000)
    let active = true

    async function checkConnection() {
      setStatus('checking')
      try {
        const response = await fetch('/api/health/ready', {
          signal: controller.signal,
        })
        if (!response.ok) throw new Error('Servicio no disponible')
        const data = await response.json()
        if (data.status !== 'ok' || data.database !== 'ok') {
          throw new Error('Respuesta inesperada')
        }
        if (active) setStatus('ready')
      } catch {
        if (active) setStatus('error')
      } finally {
        clearTimeout(timeout)
      }
    }

    checkConnection()
    return () => {
      active = false
      clearTimeout(timeout)
      controller.abort()
    }
  }, [attempt])

  const messages = {
    checking: 'Comprobando la conexión con el servidor…',
    ready: 'El entorno está listo. El servidor y la base de datos están conectados.',
    error: 'No se pudo conectar con el servidor o la base de datos.',
  }

  return (
    <main>
      <p className="eyebrow">ENTORNO DE DESARROLLO</p>
      <h1>FutBot</h1>
      <p>La base del proyecto está en marcha.</p>
      <div className={`status ${status}`} role="status" aria-live="polite">
        {messages[status]}
      </div>
      <button disabled={status === 'checking'} onClick={() => setAttempt(attempt + 1)}>
        Comprobar conexión
      </button>
    </main>
  )
}
