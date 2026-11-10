"""Placeholder for the proposal screenshots. The opponent PID lane follower is not implemented here yet."""
from controller import Robot

robot = Robot()
step = int(robot.getBasicTimeStep())
while robot.step(step) != -1:
    pass
