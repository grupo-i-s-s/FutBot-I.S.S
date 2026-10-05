import { useEffect, useRef } from 'react'
import { drawField, interpolateState } from './fieldDrawing.js'

export default function MatchCanvas({ snapshot, live }) {
  const canvas = useRef(null)
  const history = useRef({ previous: null, current: null })
  const redraw = useRef(null)

  useEffect(() => {
    const old = history.current.current
    const scoreChanged = old && old.state.teams.some((team) => (
      snapshot.state.teams.find((next) => next.id === team.id)?.score !== team.score
    ))
    const now = performance.now()
    const canBlend = live && old && old.state.status === snapshot.state.status
      && !scoreChanged && now - old.receivedAt < 500
    history.current = {
      previous: canBlend ? old : null,
      current: { state: snapshot.state, receivedAt: now },
    }
    redraw.current?.()
  }, [snapshot, live])

  useEffect(() => {
    const element = canvas.current
    const context = element.getContext('2d')
    if (!context) return
    let frame
    let viewWidth
    let viewHeight
    const reducedMotion = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches ?? false

    function draw(now = performance.now()) {
      const { previous, current } = history.current
      if (!current) return
      const state = live && !reducedMotion ? interpolateState(previous, current, now) : current.state
      drawField(context, state, viewWidth, viewHeight, window.devicePixelRatio || 1)
    }

    function resize() {
      const rect = element.getBoundingClientRect()
      viewWidth = rect.width || 1000
      viewHeight = rect.height || 600
      const ratio = window.devicePixelRatio || 1
      element.width = Math.round(viewWidth * ratio)
      element.height = Math.round(viewHeight * ratio)
      draw()
    }

    function animate(now) {
      draw(now)
      frame = requestAnimationFrame(animate)
    }

    const observer = new ResizeObserver(resize)
    observer.observe(element)
    resize()
    redraw.current = draw
    // El ciclo lee refs y no fuerza renders de React a 60 Hz. Durante espera,
    // desconexión y final sólo se dibuja al recibir datos o cambiar el tamaño.
    if (live) frame = requestAnimationFrame(animate)
    window.addEventListener('resize', resize)
    return () => {
      cancelAnimationFrame(frame)
      redraw.current = null
      observer.disconnect()
      window.removeEventListener('resize', resize)
    }
  }, [live])

  return (
    <canvas
      ref={canvas}
      className="match-canvas"
      style={{ aspectRatio: `${snapshot.state.field.width} / ${snapshot.state.field.height}` }}
      role="img"
      aria-label={`Cancha del partido, ${snapshot.state.players.length} jugadores. Las alineaciones se muestran debajo.`}
    >
      Tu navegador no permite dibujar la cancha. El marcador y los jugadores están disponibles en esta página.
    </canvas>
  )
}
