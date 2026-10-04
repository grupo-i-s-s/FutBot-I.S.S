export function fieldTransform(field, viewWidth, viewHeight, padding = 18) {
  const scale = Math.min((viewWidth - padding * 2) / field.width, (viewHeight - padding * 2) / field.height)
  return { scale, x: (viewWidth - field.width * scale) / 2, y: (viewHeight - field.height * scale) / 2 }
}

export function interpolateState(previous, current, now) {
  if (!previous || !current) return current?.state
  const elapsed = current.receivedAt - previous.receivedAt
  const factor = elapsed > 0 ? Math.max(0, Math.min(1, (now - 100 - previous.receivedAt) / elapsed)) : 1
  const blend = (before, after) => ({
    ...after, x: before.x + (after.x - before.x) * factor, y: before.y + (after.y - before.y) * factor,
  })
  const beforeById = new Map(previous.state.players.map((player) => [player.id, player]))
  return {
    ...current.state,
    players: current.state.players.map((player) => beforeById.has(player.id) ? blend(beforeById.get(player.id), player) : player),
    ball: previous.state.ball && current.state.ball ? blend(previous.state.ball, current.state.ball) : current.state.ball,
  }
}

export function drawField(context, state, viewWidth, viewHeight, pixelRatio) {
  const { field, players, ball, teams } = state
  const transform = fieldTransform(field, viewWidth, viewHeight)
  context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0)
  context.fillStyle = '#123c2b'
  context.fillRect(0, 0, viewWidth, viewHeight)
  context.translate(transform.x, transform.y)
  context.scale(transform.scale, transform.scale)
  for (let stripe = 0; stripe < 10; stripe++) {
    context.fillStyle = stripe % 2 ? '#26724a' : '#2b7d51'
    context.fillRect(stripe * field.width / 10, 0, field.width / 10, field.height)
  }
  context.strokeStyle = '#e3f1e7'
  context.lineWidth = 0.25
  context.strokeRect(0, 0, field.width, field.height)
  context.beginPath()
  context.moveTo(field.width / 2, 0)
  context.lineTo(field.width / 2, field.height)
  context.stroke()
  context.beginPath()
  context.arc(field.width / 2, field.height / 2, field.height / 8, 0, Math.PI * 2)
  context.stroke()
  const areaWidth = field.width * 0.13
  const areaHeight = field.height / 2
  context.strokeRect(0, (field.height - areaHeight) / 2, areaWidth, areaHeight)
  context.strokeRect(field.width - areaWidth, (field.height - areaHeight) / 2, areaWidth, areaHeight)
  const goalY = (field.height - field.goalWidth) / 2
  context.strokeRect(-1, goalY, 1, field.goalWidth)
  context.strokeRect(field.width, goalY, 1, field.goalWidth)

  for (const player of players) {
    context.fillStyle = teams.find((team) => team.id === player.teamId)?.color ?? '#2563eb'
    context.beginPath()
    context.arc(player.x, player.y, player.radius, 0, Math.PI * 2)
    context.fill()
    context.strokeStyle = '#fff'
    context.stroke()
    context.fillStyle = '#fff'
    context.font = `bold ${player.radius}px system-ui`
    context.textAlign = 'center'
    context.textBaseline = 'middle'
    context.fillText(String(player.id), player.x, player.y)
  }
  if (ball) {
    context.beginPath()
    context.arc(ball.x, ball.y, ball.radius, 0, Math.PI * 2)
    context.fillStyle = '#fff'
    context.fill()
    context.strokeStyle = '#12251c'
    context.stroke()
  }
}
