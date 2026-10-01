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

  const statusClasses = {
    checking: 'bg-[#f0f2f4]',
    ready: 'bg-[#e5f3e9]',
    error: 'bg-[#fce8e6] text-[#8b211b]',
  }

  return (
    <main className="mx-auto my-[12vh] w-[calc(100%_-_40px)] max-w-[620px] rounded-[20px] border border-frame bg-white p-[clamp(24px,5vw,48px)]">
      <p className="text-xs leading-relaxed font-bold tracking-[0.12em]">
        ENTORNO DE DESARROLLO
      </p>

      <h1 className="my-4 text-5xl leading-normal font-bold">FutBot</h1>

      <p className="leading-relaxed">
        La base del proyecto está en marcha.
      </p>

      <div
        className={`my-7 rounded-lg p-5 leading-relaxed ${statusClasses[status]}`}
        role="status"
        aria-live="polite"
      >
        {messages[status]}
      </div>

      <button
        className="cursor-pointer rounded-lg bg-brand px-5 py-3 text-white focus-visible:outline-3 focus-visible:outline-offset-4 focus-visible:outline-[#c37b08] disabled:cursor-wait disabled:opacity-65"
        disabled={status === 'checking'}
        onClick={() => setAttempt(attempt + 1)}
      >
        Comprobar conexión
      </button>
    </main>
  )
}
