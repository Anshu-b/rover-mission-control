import sounddevice as sd
import numpy as np
import time
import requests
import json

# -----------------------------
# Firebase config
# -----------------------------

FIREBASE_URL = "https://marsroverproject-c0f62-default-rtdb.firebaseio.com"
FIREBASE_SECRET = "Vot1KuGQdP5MX8Mkl4GZ7SPTLG2cRMXn4AyEe2bo"

# -----------------------------
# Audio config
# -----------------------------

DEVICE = 1
SAMPLE_RATE = 48000
WINDOW = 0.1

TRIALS = 10
TRIAL_DURATION = 5

samples_per_trial = int(TRIAL_DURATION / WINDOW)

# -----------------------------
# Firebase sender
# -----------------------------

def send_to_firebase(data):

    url = f"{FIREBASE_URL}/sound_experiment_laptop.json?auth={FIREBASE_SECRET}"

    requests.post(url, data=json.dumps(data))


# -----------------------------
# Audio stream
# -----------------------------

stream = sd.InputStream(
    samplerate=SAMPLE_RATE,
    channels=1,
    device=DEVICE
)

stream.start()

for trial in range(TRIALS):

    print(f"\nTrial {trial+1}")

    for i in range(samples_per_trial):

        audio, overflow = stream.read(int(WINDOW * SAMPLE_RATE))

        rms = np.sqrt(np.mean(audio**2))
        db = 20 * np.log10(rms + 1e-6)

        timestamp = time.time()

        print(db)

        data = {
            "trial": trial + 1,
            "timestamp": timestamp,
            "laptop_db": float(db)
        }

        send_to_firebase(data)

stream.stop()
stream.close()