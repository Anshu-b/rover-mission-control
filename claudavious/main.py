import time
import threading
from picarx import Picarx
from sensors import SoundSensor, SoilSensor, DHTSensor, UltrasonicSensor
from stepper import StepperMotor
from navigation import Navigator
from firebase_stream import push_reading, push_sound_validity, push_ultrasonic, push_path, push_event
from dashboard import Dashboard
from config import SOUND_THRESHOLD, SOUND_AVG_WINDOW, DATA_INTERVAL, OBSTACLE_DISTANCE

print("[MAIN] Initializing hardware...")
px = Picarx()
sound = SoundSensor()
soil = SoilSensor()
dht = DHTSensor()
ultrasonic = UltrasonicSensor(px)
stepper = StepperMotor()
nav = Navigator(px, ultrasonic)

state = {
    "temp": 0, "humidity": 0, "sound_level": 0,
    "soil_moisture": 0, "ultrasonic": 0, "floor_type": "unknown",
    "x": 0, "y": 0, "heading": 90, "mode": "idle",
    "path": [], "sound_history": [],
}
state_lock = threading.Lock()


def update_state(key, val):
    with state_lock:
        state[key] = val


def get_state():
    with state_lock:
        s = state.copy()
        s["path"] = list(nav.path)
        x, y, h = nav.get_position()
        s["x"] = round(x, 2)
        s["y"] = round(y, 2)
        s["heading"] = round(h, 2)
        s["mode"] = nav.get_mode()
        s.pop("sound_history", None)
        return s


def sensor_loop():
    print("[SENSORS] Starting sensor loop")
    while True:
        s = sound.read()
        update_state("sound_level", s)

        with state_lock:
            state["sound_history"].append({"time": time.time(), "level": s})
            cutoff = time.time() - SOUND_AVG_WINDOW
            state["sound_history"] = [x for x in state["sound_history"] if x["time"] > cutoff]

        temp, hum = dht.read()
        if temp is not None:
            update_state("temp", temp)
            update_state("humidity", hum)

        update_state("soil_moisture", soil.read())

        dist = ultrasonic.read()
        update_state("ultrasonic", dist)
        push_ultrasonic(dist, dist > 0 and dist < OBSTACLE_DISTANCE)

        time.sleep(0.5)


def sound_monitor():
    print("[SOUND] Starting sound monitor")
    while True:
        with state_lock:
            history = list(state["sound_history"])

        if len(history) > 5:
            avg = sum(h["level"] for h in history) / len(history)
            exceeded = avg > SOUND_THRESHOLD

            push_sound_validity(avg, exceeded,
                                action="return_home" if exceeded else "none")

            if exceeded and nav.get_mode() == "autonomous":
                print(f"[SOUND] Threshold exceeded! avg={avg:.0f}")
                push_event("sound_alert", {"avg_level": round(avg, 2)})
                nav.stop()
                time.sleep(0.5)
                threading.Thread(target=nav.return_home, daemon=True).start()
        time.sleep(1)


def firebase_loop():
    print("[FIREBASE] Starting data upload")
    while True:
        data = get_state()
        push_reading(data)
        push_path(nav.path[-50:])
        time.sleep(DATA_INTERVAL)

def floor_detection_loop(shared_cap=None):
    import cv2
    import numpy as np
    import onnxruntime as ort

    session = ort.InferenceSession("/home/claudavious/groundVision/ground_classifier_int8.onnx")
    cap = shared_cap if shared_cap else cv2.VideoCapture('/dev/video0', cv2.CAP_V4L2)
    labels = ['soil', 'carpet', 'wood']
    prev_floor = 'unknown'

    print("[FLOOR] CNN model loaded, starting detection")

    while True:
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.5)
            continue

        h, w, _ = frame.shape
        frame = frame[int(h * 0.4):h, :]
        frame = cv2.resize(frame, (96, 96))

        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = frame.astype(np.float32) / 255.0
        img = np.transpose(img, (2, 0, 1))
        img = np.expand_dims(img, 0)

        pred = session.run(None, {"input": img})[0]
        label = labels[np.argmax(pred)]

        update_state("floor_type", label)

        if label != prev_floor and prev_floor != 'unknown':
            print(f"[FLOOR] Change: {prev_floor} -> {label}")
            push_event("floor_change", {"from": prev_floor, "to": label})
            nav.pause()
            time.sleep(0.3)
            nav._drive_forward(3.0)
            nav.px.stop()
            time.sleep(0.5)
            reading = stepper.probe_cycle(soil)
            push_event("probe_reading", {"soil_moisture": reading, "floor_type": label})
            nav.unpause()

        prev_floor = label
        time.sleep(1)


def handle_command(action):
    print(f"[CMD] {action}")

    if action == "start":
        if nav.get_mode() == "idle":
            threading.Thread(target=nav.run_autonomous, daemon=True).start()
            push_event("mode_change", {"mode": "autonomous"})

    elif action == "stop":
        nav.stop()
        push_event("mode_change", {"mode": "idle"})

    elif action == "return_home":
        nav.stop()
        time.sleep(0.5)
        threading.Thread(target=nav.return_home, daemon=True).start()
        push_event("mode_change", {"mode": "returning"})

    elif action == "deploy_probe":
        def probe():
            nav.pause()
            reading = stepper.probe_cycle(soil)
            push_event("manual_probe", {"soil_moisture": reading})
            nav.unpause()
        threading.Thread(target=probe, daemon=True).start()

    elif action == "retract_probe":
        stepper.retract_probe()


class SharedCamera:
    def __init__(self, device='/dev/video1'):
        import cv2
        self.cap = cv2.VideoCapture(device, cv2.CAP_V4L2)
        self.frame = None
        self.lock = threading.Lock()
        self.running = True
        self.thread = threading.Thread(target=self._reader, daemon=True)
        self.thread.start()

    def _reader(self):
        while self.running:
            ret, frame = self.cap.read()
            if ret:
                with self.lock:
                    self.frame = frame

    def read(self):
        with self.lock:
            if self.frame is not None:
                return True, self.frame.copy()
            return False, None

    def isOpened(self):
        return self.cap.isOpened()

    def release(self):
        self.running = False
        self.cap.release()


if __name__ == "__main__":
    print("[MAIN] Mars Rover System")
    print("=" * 40)

    shared_cap = SharedCamera('/dev/video0')
    if not shared_cap.isOpened():
        print("[WARN] Camera not available")
        shared_cap = None

    threads = [
        threading.Thread(target=sensor_loop, daemon=True),
        threading.Thread(target=sound_monitor, daemon=True),
        threading.Thread(target=firebase_loop, daemon=True),
        threading.Thread(target=floor_detection_loop, args=(shared_cap,), daemon=True),
    ]

    for t in threads:
        t.start()

    dash = Dashboard(get_state, handle_command, shared_cap)
    dash.start(port=8000)