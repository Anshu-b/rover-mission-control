import cv2
import time
import threading
import numpy as np
import onnxruntime as ort
from flask import Flask, Response, request, jsonify
from picarx import Picarx

px = Picarx()

latest_jpeg = None
frame_lock = threading.Lock()
last_command = "stop"
latest_prediction = "unknown"
latest_confidence = 0.0

cap = None

CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
STREAM_JPEG_QUALITY = 70
STREAM_EVERY_N_FRAMES = 3
GROUND_KEEP_FRACTION = 0.60

MODEL_PATH = "model_out/ground_classifier.onnx"
CLASS_NAMES = ["soil", "carpet", "wood"]
INPUT_WIDTH = 96
INPUT_HEIGHT = 96
MOVE_SPEED = 30
TURN_ANGLE = 35

session = ort.InferenceSession(MODEL_PATH)
input_name = session.get_inputs()[0].name

for testx1 in range(10):
    for testx2 in range(5):
        testcap1 = cv2.VideoCapture(testx2)
        time.sleep(0.3)

        if testcap1.isOpened():
            testret1, testframe1 = testcap1.read()
            if testret1:
                cap = testcap1
                print(f"Using camera index {testx2}")
                break

        testcap1.release()

    if cap is not None:
        break

    print("Camera not ready yet, retrying...")
    time.sleep(1)

if cap is None:
    print("Could not open any camera")
    raise SystemExit(1)

cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)

app = Flask(__name__)


def move_forward():
    global last_command
    px.set_dir_servo_angle(0)
    px.forward(MOVE_SPEED)
    last_command = "forward"
    print("MOVE: forward")


def move_backward():
    global last_command
    px.set_dir_servo_angle(0)
    px.backward(MOVE_SPEED)
    last_command = "backward"
    print("MOVE: backward")


def move_left():
    global last_command
    px.set_dir_servo_angle(-TURN_ANGLE)
    px.forward(MOVE_SPEED)
    last_command = "left"
    print("MOVE: left")


def move_right():
    global last_command
    px.set_dir_servo_angle(TURN_ANGLE)
    px.forward(MOVE_SPEED)
    last_command = "right"
    print("MOVE: right")


def stop_rover():
    global last_command
    px.set_dir_servo_angle(0)
    px.stop()
    last_command = "stop"
    print("MOVE: stop")


def crop_ground_region(frame):
    testheight1 = frame.shape[0]
    teststart1 = int(testheight1 * (1.0 - GROUND_KEEP_FRACTION))
    return frame[teststart1:, :]


def preprocess_for_model(frame):
    testimage1 = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    testimage1 = cv2.resize(
        testimage1,
        (INPUT_WIDTH, INPUT_HEIGHT),
        interpolation=cv2.INTER_AREA
    )
    testimage1 = testimage1.astype(np.float32) / 255.0
    testimage1 = np.transpose(testimage1, (2, 0, 1))
    testimage1 = np.expand_dims(testimage1, axis=0)
    return testimage1


def softmax(logits):
    testshift1 = logits - np.max(logits)
    testexp1 = np.exp(testshift1)
    return testexp1 / np.sum(testexp1)


def classify_ground(frame):
    testinput1 = preprocess_for_model(frame)
    testoutput1 = session.run(None, {input_name: testinput1})[0]
    testprobs1 = softmax(testoutput1[0])
    testindex1 = int(np.argmax(testprobs1))
    return CLASS_NAMES[testindex1], float(testprobs1[testindex1])


def camera_loop():
    global latest_jpeg
    global latest_prediction
    global latest_confidence

    teststreamparams1 = [int(cv2.IMWRITE_JPEG_QUALITY), STREAM_JPEG_QUALITY]
    testframecount1 = 0

    while True:
        testret1, testframe1 = cap.read()
        if not testret1:
            time.sleep(0.01)
            continue

        testframecount1 += 1

        testground1 = crop_ground_region(testframe1)
        testlabel1, testconfidence1 = classify_ground(testground1)

        latest_prediction = testlabel1
        latest_confidence = testconfidence1

        testdisplay1 = testframe1.copy()

        cv2.putText(
            testdisplay1,
            f"pred={latest_prediction} conf={latest_confidence:.2f}",
            (20, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2
        )

        cv2.putText(
            testdisplay1,
            f"cmd={last_command}",
            (20, 70),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2
        )

        testliney1 = int(CAMERA_HEIGHT * (1.0 - GROUND_KEEP_FRACTION))
        cv2.line(
            testdisplay1,
            (0, testliney1),
            (CAMERA_WIDTH - 1, testliney1),
            (0, 0, 255),
            2
        )

        if testframecount1 % STREAM_EVERY_N_FRAMES == 0:
            testok1, testjpeg1 = cv2.imencode(
                ".jpg",
                testdisplay1,
                teststreamparams1
            )

            if testok1:
                with frame_lock:
                    latest_jpeg = testjpeg1.tobytes()


def mjpeg_stream():
    global latest_jpeg

    while True:
        with frame_lock:
            testjpeg1 = latest_jpeg

        if testjpeg1 is None:
            time.sleep(0.01)
            continue

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" +
            testjpeg1 +
            b"\r\n"
        )


@app.route("/")
def index():
    return """
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Rover Inference Control</title>
<style>
body {
    font-family: Arial, sans-serif;
    background: #111;
    color: #eee;
    text-align: center;
    margin: 0;
    padding: 20px;
}
img {
    width: 640px;
    max-width: 95vw;
    border: 3px solid #444;
    border-radius: 8px;
}
.controls {
    margin-top: 20px;
    display: inline-grid;
    grid-template-columns: 100px 100px 100px;
    gap: 10px;
}
button {
    padding: 16px;
    font-size: 18px;
    border: none;
    border-radius: 8px;
    cursor: pointer;
}
.status {
    margin-top: 16px;
    font-size: 18px;
}
</style>
</head>
<body>
<h1>Rover Inference Control</h1>
<p>Use arrow keys or WASD. Release key or press space to stop.</p>
<p>Live screen shows model prediction from the bottom 60% ground crop.</p>
<img src="/stream" alt="rover stream">
<div class="controls">
    <div></div>
    <button onmousedown="sendCommand('forward')" onmouseup="sendCommand('stop')">Forward</button>
    <div></div>
    <button onmousedown="sendCommand('left')" onmouseup="sendCommand('stop')">Left</button>
    <button onclick="sendCommand('stop')">Stop</button>
    <button onmousedown="sendCommand('right')" onmouseup="sendCommand('stop')">Right</button>
    <div></div>
    <button onmousedown="sendCommand('backward')" onmouseup="sendCommand('stop')">Backward</button>
    <div></div>
</div>
<div class="status" id="status">Last command: stop</div>

<script>
async function sendCommand(command) {
    try {
        const response = await fetch("/move", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ command })
        });

        const data = await response.json();

        if (data.ok) {
            document.getElementById("status").textContent =
                "Last command: " + command;
        }
    } catch (err) {
        document.getElementById("status").textContent = "Request failed";
    }
}

document.addEventListener("keydown", function(e) {
    const key = e.key.toLowerCase();

    if (key === "w" || e.key === "ArrowUp") {
        e.preventDefault();
        sendCommand("forward");
    } else if (key === "s" || e.key === "ArrowDown") {
        e.preventDefault();
        sendCommand("backward");
    } else if (key === "a" || e.key === "ArrowLeft") {
        e.preventDefault();
        sendCommand("left");
    } else if (key === "d" || e.key === "ArrowRight") {
        e.preventDefault();
        sendCommand("right");
    } else if (e.key === " ") {
        e.preventDefault();
        sendCommand("stop");
    }
});

document.addEventListener("keyup", function(e) {
    if (["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", "w", "a", "s", "d"].includes(e.key)) {
        sendCommand("stop");
    }
});
</script>
</body>
</html>
"""


@app.route("/stream")
def stream():
    return Response(
        mjpeg_stream(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )


@app.route("/move", methods=["POST"])
def move():
    testdata1 = request.get_json(silent=True) or {}
    testcommand1 = str(testdata1.get("command", "")).lower()

    if testcommand1 == "forward":
        move_forward()
    elif testcommand1 == "backward":
        move_backward()
    elif testcommand1 == "left":
        move_left()
    elif testcommand1 == "right":
        move_right()
    elif testcommand1 == "stop":
        stop_rover()
    else:
        return jsonify({"ok": False, "error": "invalid command"}), 400

    return jsonify({"ok": True, "command": testcommand1})


@app.route("/prediction")
def prediction():
    return jsonify(
        {
            "label": latest_prediction,
            "confidence": latest_confidence,
            "command": last_command
        }
    )


if __name__ == "__main__":
    testthread1 = threading.Thread(target=camera_loop, daemon=True)
    testthread1.start()

    try:
        app.run(host="0.0.0.0", port=5000, threaded=True)
    finally:
        stop_rover()
        cap.release()