import pymunk
from types import SimpleNamespace

from primitives.primitives import kick


# Crear el espacio de simulación.
space = pymunk.Space()
space.gravity = (0, 0)

# Crear objetos sencillos que tengan el atributo .body.
player = SimpleNamespace(body=pymunk.Body(1, 1))
ball = SimpleNamespace(body=pymunk.Body(1, 1))

space.add(player.body, ball.body)

# PRUEBA 1: jugador cerca, debería poder patear.
player.body.position = (0, 0)
ball.body.position = (12, 0)

result = kick(player, ball, (100, 0), speed=30, kick_range=15)

print("Cerca: ¿pateó?", result)
print("Velocidad:", ball.body.velocity)

# Avanzar 0.1 segundos para comprobar el movimiento.
space.step(0.1)
print("Posición después:", ball.body.position)

# PRUEBA 2: jugador lejos, no debería poder patear.
# Reiniciamos la pelota para que no conserve la patada anterior.
ball.body.position = (100, 0)
ball.body.velocity = (0, 0)

result = kick(player, ball, (200, 0), speed=30, kick_range=15)

print("Lejos: ¿pateó?", result)
print("Velocidad:", ball.body.velocity)