import time
import math
import threading
import random
from config import SPEED, OBSTACLE_DISTANCE, TURN_ANGLE, HOME_THRESHOLD, STEP_DISTANCE


class Navigator:
    def __init__(self, px, ultrasonic):
        self.px = px
        self.ultrasonic = ultrasonic
        self.x = 0.0
        self.y = 0.0
        self.heading = 90.0
        self.path = []
        self.mode = "idle"
        self._lock = threading.Lock()
        self._running = False
        self._paused = False

    def get_position(self):
        with self._lock:
            return self.x, self.y, self.heading

    def get_mode(self):
        with self._lock:
            return self.mode

    def set_mode(self, mode):
        with self._lock:
            self.mode = mode

    def _update_position(self, distance):
        with self._lock:
            rad = math.radians(self.heading)
            self.x += distance * math.cos(rad)
            self.y += distance * math.sin(rad)
            self.path.append({
                "x": round(self.x, 2),
                "y": round(self.y, 2),
                "heading": round(self.heading, 2),
                "time": time.time()
            })

    def _drive_forward(self, duration=0.5):
        self.px.set_dir_servo_angle(0)
        self.px.forward(SPEED)
        time.sleep(duration)
        self.px.stop()
        self._update_position(STEP_DISTANCE)

    def _turn_left(self):
        self.px.set_dir_servo_angle(-TURN_ANGLE)
        self.px.forward(SPEED)
        time.sleep(0.5)
        self.px.stop()
        self.px.set_dir_servo_angle(0)
        with self._lock:
            self.heading = (self.heading + 30) % 360
        self._update_position(STEP_DISTANCE * 0.5)

    def _turn_right(self):
        self.px.set_dir_servo_angle(TURN_ANGLE)
        self.px.forward(SPEED)
        time.sleep(0.5)
        self.px.stop()
        self.px.set_dir_servo_angle(0)
        with self._lock:
            self.heading = (self.heading - 30) % 360
        self._update_position(STEP_DISTANCE * 0.5)

    def _avoid_obstacle(self):
        self.px.set_dir_servo_angle(0)
        self.px.backward(SPEED)
        time.sleep(0.3)
        self.px.stop()

        if random.random() > 0.5:
            self._turn_left()
            self._turn_left()
        else:
            self._turn_right()
            self._turn_right()

        dist = self.ultrasonic.read()
        if dist > 0 and dist < OBSTACLE_DISTANCE:
            self._turn_left()
            self._turn_left()

    def stop(self):
        self._running = False
        self.px.stop()
        self.px.set_dir_servo_angle(0)
        self.set_mode("idle")

    def pause(self):
        self._paused = True
        self.px.stop()

    def unpause(self):
        self._paused = False

    def distance_to_home(self):
        with self._lock:
            return math.sqrt(self.x ** 2 + self.y ** 2)

    def angle_to_home(self):
        with self._lock:
            return math.degrees(math.atan2(-self.y, -self.x)) % 360

    def _turn_to_heading(self, target):
        with self._lock:
            current = self.heading
        diff = (target - current + 360) % 360
        if diff < 15 or diff > 345:
            return
        if diff <= 180:
            turns = max(1, int(diff / 30))
            for _ in range(turns):
                if self.get_mode() != "returning":
                    break
                self._turn_left()
                time.sleep(0.1)
        else:
            turns = max(1, int((360 - diff) / 30))
            for _ in range(turns):
                if self.get_mode() != "returning":
                    break
                self._turn_right()
                time.sleep(0.1)

    def run_autonomous(self):
        self._running = True
        self.set_mode("autonomous")
        print("[NAV] Autonomous mode started")

        while self._running and self.get_mode() == "autonomous":
            if self._paused:
                time.sleep(0.1)
                continue

            dist = self.ultrasonic.read()
            if dist > 0 and dist < OBSTACLE_DISTANCE:
                self.px.stop()
                time.sleep(0.1)
                self._avoid_obstacle()
            else:
                self._drive_forward(0.5)
            time.sleep(0.1)

        self.px.stop()
        print("[NAV] Autonomous mode stopped")

    def return_home(self):
        self.set_mode("returning")
        self._running = True
        print("[NAV] Returning home...")

        while self._running and self.get_mode() == "returning":
            dist_home = self.distance_to_home()
            if dist_home < HOME_THRESHOLD:
                self.px.stop()
                self.set_mode("idle")
                print("[NAV] Home reached!")
                return

            target = self.angle_to_home()
            self._turn_to_heading(target)

            obstacle_dist = self.ultrasonic.read()
            if obstacle_dist > 0 and obstacle_dist < OBSTACLE_DISTANCE:
                self._avoid_obstacle()
            else:
                self._drive_forward(0.5)
            time.sleep(0.1)

        self.px.stop()
