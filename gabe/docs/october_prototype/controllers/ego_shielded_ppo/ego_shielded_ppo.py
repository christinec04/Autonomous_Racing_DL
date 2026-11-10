"""Placeholder for the proposal screenshots. Turns the ego sensors on and holds the car still.
The PPO policy and the APF shield are not implemented here yet."""
from controller import Robot

robot = Robot()
step = int(robot.getBasicTimeStep())
for name in ("lidar2d", "gps", "inertial unit"):
    device = robot.getDevice(name)
    if device:
        device.enable(step)
while robot.step(step) != -1:
    pass
