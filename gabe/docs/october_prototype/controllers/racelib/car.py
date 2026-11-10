"""Ground truth state, aerodynamics and command helpers for a RaceCar controller."""
import math
import os
import sys

from vehicle import Driver

from track import CDA, CLA, RHO

sys.stdout.reconfigure(line_buffering=True)


class Car:
    def __init__(self):
        self.d = Driver()
        self.dt = self.d.getBasicTimeStep() / 1000.0
        self.node = self.d.getSelf()
        self.trans = self.node.getField("translation")
        self.rot = self.node.getField("rotation")
        self.d.setGear(1)
        self.args = dict(a.split("=", 1) for a in sys.argv[1:] if "=" in a)
        self.v_prev = None
        self.read()

    def read(self):
        p = self.node.getPosition()
        R = self.node.getOrientation()
        vel = self.node.getVelocity()
        self.x, self.y, self.z = p
        self.fwd = (R[0], R[3])
        self.left = (R[1], R[4])
        self.up_z = R[8]
        self.yaw = math.atan2(R[3], R[0])
        self.vx = vel[0] * R[0] + vel[1] * R[3]
        self.vy = vel[0] * R[1] + vel[1] * R[4]
        self.yaw_rate = vel[5]
        self.speed = math.hypot(vel[0], vel[1])
        if self.v_prev is not None:
            ax_w = (vel[0] - self.v_prev[0]) / self.dt
            ay_w = (vel[1] - self.v_prev[1]) / self.dt
            self.ax = ax_w * R[0] + ay_w * R[3]
            self.ay = ax_w * R[1] + ay_w * R[4]
        else:
            self.ax = self.ay = 0.0
        self.v_prev = (vel[0], vel[1])

    def aero(self):
        """Webots has no aerodynamics, add drag and downforce at the centre of mass every step."""
        v = self.speed
        q = 0.5 * RHO * v
        down = 0.5 * RHO * CLA * (self.vx ** 2)
        R = self.node.getOrientation()
        vel = self.node.getVelocity()
        fx = -q * CDA * vel[0] - down * R[2]
        fy = -q * CDA * vel[1] - down * R[5]
        fz = -down * R[8]
        self.node.addForce([fx, fy, fz], False)

    def command(self, steer, throttle, brake):
        """steer in [-1, 1] maps to the steering limit, positive turns left. Webots steers right for positive angles."""
        self.d.setSteeringAngle(-0.45 * max(-1.0, min(1.0, steer)))
        self.d.setThrottle(max(0.0, min(1.0, throttle)))
        self.d.setBrakeIntensity(max(0.0, min(1.0, brake)))

    def step(self):
        self.aero()
        r = self.d.step()
        self.read()
        return r

    def place(self, x, y, yaw, speed=0.0):
        self.trans.setSFVec3f([x, y, 0.36])
        self.rot.setSFRotation([0, 0, 1, yaw])
        self.node.resetPhysics()
        if speed:
            self.node.setVelocity([speed * math.cos(yaw), speed * math.sin(yaw), 0, 0, 0, 0])
        self.v_prev = None


def out_dir(*parts):
    here = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(here, "..", "..", "runs", *parts)
    os.makedirs(path, exist_ok=True)
    return os.path.abspath(path)
