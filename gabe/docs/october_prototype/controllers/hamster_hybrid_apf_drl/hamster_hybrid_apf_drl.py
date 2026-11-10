"""Placeholder for the proposal screenshots. Turns the Hamster sensors on and holds the robot still.
The APF controller, trap detector and PPO escape agent are not implemented here yet."""
from controller import Robot

robot = Robot()
step = int(robot.getBasicTimeStep())
for name in ("left proximity", "right proximity", "left floor", "right floor", "accelerometer"):
    device = robot.getDevice(name)
    if device:
        device.enable(step)
while robot.step(step) != -1:
    pass
