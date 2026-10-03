import { useEffect, useState } from 'react'
import { matchStreamUrl } from '../matchApi.js'

export function useMatchConnection(matchId) {
  const [status, setStatus] = useState('idle')

  useEffect(() => {
    if (matchId == null) {
      setStatus('idle')
      return
    }

    let socket

    try {
      socket = new WebSocket(matchStreamUrl(matchId))
    } catch {
      setStatus('error')
      return
    }

    let disposed = false
    setStatus('connecting')

    socket.onopen = () => {
      if (!disposed) setStatus('connected')
    }

    socket.onerror = () => {
      if (!disposed) setStatus('error')
    }

    socket.onclose = (event) => {
      if (disposed) return
      setStatus(event.code === 1000 ? 'closed' : 'disconnected')
    }

    return () => {
      disposed = true
      socket.close(1000)
    }
  }, [matchId])

  return status
}

// USO DEL HOOK
// import { useMatchConnection } from './hooks/useMatchConnection.js'
//
// export function MatchConnectionStatus({ matchId }) {
//   const status = useMatchConnection(matchId)
//
//   return <p>Conexión: {status}</p>
// }