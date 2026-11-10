"""Placeholder for the proposal screenshots. Turns the LDS-01 on and holds the robot still.
The APF controller, trap detector and PPO escape agent are not implemented here yet."""
from controller import Robot

robot = Robot()
step = int(robot.getBasicTimeStep())
lidar = robot.getDevice("LDS-01")
if lidar:
    lidar.enable(step)
while robot.step(step) != -1:
    pass
