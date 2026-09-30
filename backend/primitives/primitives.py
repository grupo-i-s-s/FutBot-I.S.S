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
