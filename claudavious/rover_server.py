import cv2
import os
import sys
import time
import threading
from flask import Flask, Response, request, jsonify
from picarx import Picarx

if len(sys.argv) != 2:
    print("Usage: python3 rover_server.py <soil|carpet|wood>")
    raise SystemExit(1)

label = sys.argv[1].strip().lower()

if label not in ["soil", "carpet", "wood"]:
    print("Label must be one of: soil, carpet, wood")
    raise SystemExit(1)

save_dir = os.path.join("data", "train", label)
os.makedirs(save_dir, exist_ok=True)

count = 0
for name in os.listdir(save_dir):
    if name.startswith(label) and name.endswith(".jpg"):
        number_part = name[len(label):-4]
        if number_part.isdigit():
            count = max(count, int(number_part))

px = Picarx()

latest_jpeg = None
frame_lock = threading.Lock()
last_command = "stop"
last_save_time = 0.0

cap = None

CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
SAVE_WIDTH = 320
SAVE_HEIGHT = 240
SAVE_INTERVAL = 0.5
SAVE_JPEG_QUALITY = 75
STREAM_JPEG_QUALITY = 70
STREAM_EVERY_N_FRAMES = 3
GROUND_KEEP_FRACTION = 0.60

for attempt in range(10):
    for index in range(5):
        testcap = cv2.VideoCapture(index)
        time.sleep(0.3)

        if testcap.isOpened():
            ret, frame = testcap.read()
            if ret:
                cap = testcap
                print(f"Using camera index {index}")
                break

        testcap.release()

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
    px.forward(30)
    last_command = "forward"
    print("MOVE: forward")

def move_backward():
    global last_command
    px.set_dir_servo_angle(0)
    px.backward(30)
    last_command = "backward"
    print("MOVE: backward")

def move_left():
    global last_command
    px.set_dir_servo_angle(-35)
    px.forward(30)
    last_command = "left"
    print("MOVE: left")

def move_right():
    global last_command
    px.set_dir_servo_angle(35)
    px.forward(30)
    last_command = "right"
    print("MOVE: right")

def stop_rover():
    global last_command
    px.set_dir_servo_angle(0)
    px.stop()
    last_command = "stop"
    print("MOVE: stop")

def crop_ground_region(frame):
    height = frame.shape[0]
    start_row = int(height * (1.0 - GROUND_KEEP_FRACTION))
    return frame[start_row:, :]

def camera_loop():
    global count
    global last_save_time
    global latest_jpeg

    save_encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), SAVE_JPEG_QUALITY]
    stream_encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), STREAM_JPEG_QUALITY]
    frame_counter = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.01)
            continue

        frame_counter += 1
        now = time.time()

        if (now - last_save_time) >= SAVE_INTERVAL:
            count += 1
            filename = f"{label}{count:04d}.jpg"
            path = os.path.join(save_dir, filename)

            ground_frame = crop_ground_region(frame)
            save_frame = cv2.resize(
                ground_frame,
                (SAVE_WIDTH, SAVE_HEIGHT),
                interpolation=cv2.INTER_AREA
            )

            ok_save, save_jpeg = cv2.imencode(".jpg", save_frame, save_encode_params)
            if ok_save:
                with open(path, "wb") as testfile1:
                    testfile1.write(save_jpeg.tobytes())
                last_save_time = now
                print("saved", path)

        display = frame.copy()
        cv2.putText(
            display,
            f"label={label} count={count} cmd={last_command}",
            (20, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2
        )

        crop_line_y = int(CAMERA_HEIGHT * (1.0 - GROUND_KEEP_FRACTION))
        cv2.line(
            display,
            (0, crop_line_y),
            (CAMERA_WIDTH - 1, crop_line_y),
            (0, 0, 255),
            2
        )

        if frame_counter % STREAM_EVERY_N_FRAMES == 0:
            ok_stream, jpeg = cv2.imencode(".jpg", display, stream_encode_params)
            if ok_stream:
                with frame_lock:
                    latest_jpeg = jpeg.tobytes()

def mjpeg_stream():
    global latest_jpeg

    while True:
        with frame_lock:
            jpeg = latest_jpeg

        if jpeg is None:
            time.sleep(0.01)
            continue

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n" +
            jpeg +
            b"\r\n"
        )

@app.route("/")
def index():
    return f"""
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>Rover Control</title>
<style>
body {{
    font-family: Arial, sans-serif;
    background: #111;
    color: #eee;
    text-align: center;
    margin: 0;
    padding: 20px;
}}
img {{
    width: 640px;
    max-width: 95vw;
    border: 3px solid #444;
    border-radius: 8px;
}}
.controls {{
    margin-top: 20px;
    display: inline-grid;
    grid-template-columns: 100px 100px 100px;
    gap: 10px;
}}
button {{
    padding: 16px;
    font-size: 18px;
    border: none;
    border-radius: 8px;
    cursor: pointer;
}}
.status {{
    margin-top: 16px;
    font-size: 18px;
}}
</style>
</head>
<body>
<h1>Rover Control</h1>
<p>Label: <b>{label}</b></p>
<p>Use arrow keys or WASD. Release key or press space to stop.</p>
<p>Training save uses only the bottom {int(GROUND_KEEP_FRACTION * 100)}% of the frame.</p>
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
async function sendCommand(command) {{
    try {{
        const response = await fetch("/move", {{
            method: "POST",
            headers: {{
                "Content-Type": "application/json"
            }},
            body: JSON.stringify({{ command }})
        }});

        const data = await response.json();

        if (data.ok) {{
            document.getElementById("status").textContent =
                "Last command: " + command;
        }}
    }} catch (err) {{
        document.getElementById("status").textContent = "Request failed";
    }}
}}

document.addEventListener("keydown", function(e) {{
    const key = e.key.toLowerCase();

    if (key === "w" || e.key === "ArrowUp") {{
        e.preventDefault();
        sendCommand("forward");
    }} else if (key === "s" || e.key === "ArrowDown") {{
        e.preventDefault();
        sendCommand("backward");
    }} else if (key === "a" || e.key === "ArrowLeft") {{
        e.preventDefault();
        sendCommand("left");
    }} else if (key === "d" || e.key === "ArrowRight") {{
        e.preventDefault();
        sendCommand("right");
    }} else if (e.key === " ") {{
        e.preventDefault();
        sendCommand("stop");
    }}
}});

document.addEventListener("keyup", function(e) {{
    if (["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", "w", "a", "s", "d"].includes(e.key)) {{
        sendCommand("stop");
    }}
}});
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
    data = request.get_json(silent=True) or {}
    command = str(data.get("command", "")).lower()

    if command == "forward":
        move_forward()
    elif command == "backward":
        move_backward()
    elif command == "left":
        move_left()
    elif command == "right":
        move_right()
    elif command == "stop":
        stop_rover()
    else:
        return jsonify({"ok": False, "error": "invalid command"}), 400

    return jsonify({"ok": True, "command": command})

if __name__ == "__main__":
    thread = threading.Thread(target=camera_loop, daemon=True)
    thread.start()

    try:
        app.run(host="0.0.0.0", port=5000, threaded=True)
    finally:
        stop_rover()
        cap.release()