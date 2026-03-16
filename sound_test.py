import sounddevice as sd
import numpy as np
import time

DEVICE = 1          # MacBook Pro microphone
SAMPLE_RATE = 48000
WINDOW = 0.1

TRIALS = 10
TRIAL_DURATION = 5

samples_per_trial = int(TRIAL_DURATION / WINDOW)

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

        print(db)

stream.stop()
stream.close()