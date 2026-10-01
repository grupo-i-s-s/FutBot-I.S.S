import pymunk
from pymunk.vec2d import Vec2d

# Run primitive
# Moves self to target_position with speed
# Target_position is a vector (x,y)


def run_to(self, target_position, speed):
    self_pos = self.body.position
    obj_pos = Vec2d(target_position[0], target_position[1])

    direccion = obj_pos.__sub__(self_pos)

    self.body.velocity = direccion.normalized() * speed

def kick(self, ball, target_position, speed, kick_range):
    player_position = self.body.position
    ball_position = ball.body.position

    # Comprobar que el jugador alcance la pelota.
    distance = (ball_position - player_position).length

    if distance > kick_range: # kick_range calcular desde self.control antes de pasarlo. 
        return False

    # Calcular la dirección de la pelota al destino.
    target = Vec2d(target_position[0], target_position[1])
    direction = target - ball_position

    # Evitar una patada sin dirección o rapidez.
    if direction.length == 0 or speed <= 0:
        return False
    
    unit_direction = direction.normalized()
    # Velocidad de salida de la pelota.
    ball.body.velocity = unit_direction * speed

    return True
