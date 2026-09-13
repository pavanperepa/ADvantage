"""Generate an original, vocal-free sports instrumental for the Houston reel."""

from __future__ import annotations

from array import array
from pathlib import Path
import math
import random
import wave


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "assets" / "music" / "houston-sports-pulse-instrumental.wav"

SAMPLE_RATE = 32_000
TEMPO = 126
BEAT = 60 / TEMPO
BARS = 12
DURATION = BARS * 4 * BEAT
SAMPLES = int(DURATION * SAMPLE_RATE)


def add_tone(
    left: array,
    right: array,
    start: float,
    duration: float,
    frequency: float,
    amplitude: float,
    *,
    decay: float = 3.5,
    pan: float = 0.0,
    harmonics: tuple[tuple[int, float], ...] = ((1, 1.0),),
) -> None:
    first = max(0, int(start * SAMPLE_RATE))
    count = min(int(duration * SAMPLE_RATE), SAMPLES - first)
    left_gain = math.sqrt((1 - pan) / 2)
    right_gain = math.sqrt((1 + pan) / 2)
    for offset in range(count):
        t = offset / SAMPLE_RATE
        attack = min(1.0, t / 0.008)
        envelope = attack * math.exp(-decay * t / max(duration, 0.001))
        value = 0.0
        for multiplier, level in harmonics:
            value += level * math.sin(2 * math.pi * frequency * multiplier * t)
        value *= amplitude * envelope
        left[first + offset] += value * left_gain
        right[first + offset] += value * right_gain


def add_kick(left: array, right: array, start: float, amplitude: float = 0.9) -> None:
    first = int(start * SAMPLE_RATE)
    count = min(int(0.22 * SAMPLE_RATE), SAMPLES - first)
    phase = 0.0
    for offset in range(count):
        t = offset / SAMPLE_RATE
        frequency = 95 * math.exp(-9 * t) + 42
        phase += 2 * math.pi * frequency / SAMPLE_RATE
        envelope = math.exp(-18 * t)
        click = math.sin(2 * math.pi * 160 * t) * math.exp(-80 * t) * 0.2
        value = amplitude * (math.sin(phase) * envelope + click)
        left[first + offset] += value * 0.72
        right[first + offset] += value * 0.72


def add_noise_hit(
    left: array,
    right: array,
    start: float,
    duration: float,
    amplitude: float,
    *,
    pan: float,
    seed: int,
    tone_frequency: float = 0.0,
) -> None:
    rng = random.Random(seed)
    first = int(start * SAMPLE_RATE)
    count = min(int(duration * SAMPLE_RATE), SAMPLES - first)
    left_gain = math.sqrt((1 - pan) / 2)
    right_gain = math.sqrt((1 + pan) / 2)
    previous = 0.0
    for offset in range(count):
        t = offset / SAMPLE_RATE
        noise = rng.uniform(-1.0, 1.0)
        bright_noise = noise - previous * 0.72
        previous = noise
        envelope = math.exp(-32 * t / max(duration, 0.001))
        tone = math.sin(2 * math.pi * tone_frequency * t) * 0.28 if tone_frequency else 0.0
        value = amplitude * envelope * (bright_noise * 0.72 + tone)
        left[first + offset] += value * left_gain
        right[first + offset] += value * right_gain


def build() -> Path:
    left = array("f", [0.0]) * SAMPLES
    right = array("f", [0.0]) * SAMPLES

    # D-minor progression: Dm, Bb, F, C. The second half lifts an octave.
    roots = [73.42, 58.27, 87.31, 65.41]
    chord_notes = [
        (146.83, 174.61, 220.00),
        (116.54, 146.83, 174.61),
        (174.61, 220.00, 261.63),
        (130.81, 164.81, 196.00),
    ]
    note_pattern = (0, 2, 1, 2, 0, 2, 1, 2)

    event_seed = 100
    for bar in range(BARS):
        bar_start = bar * 4 * BEAT
        root = roots[bar % len(roots)]
        chord = chord_notes[bar % len(chord_notes)]
        lift = 1.12 if bar >= 8 else 1.0

        # Warm, wide chord pulse under the rhythm.
        for index, note in enumerate(chord):
            add_tone(
                left,
                right,
                bar_start,
                4 * BEAT,
                note,
                0.055 * lift,
                decay=0.75,
                pan=(-0.38 + index * 0.38),
                harmonics=((1, 1.0), (2, 0.18)),
            )

        for beat_index in range(4):
            beat_start = bar_start + beat_index * BEAT
            add_kick(left, right, beat_start, 0.78 if beat_index in (0, 2) else 0.58)
            if beat_index in (1, 3):
                add_noise_hit(
                    left,
                    right,
                    beat_start,
                    0.16,
                    0.36,
                    pan=0.06,
                    seed=event_seed,
                    tone_frequency=185,
                )
                event_seed += 1

            add_tone(
                left,
                right,
                beat_start,
                BEAT * 0.84,
                root,
                0.27 * lift,
                decay=3.8,
                harmonics=((1, 1.0), (2, 0.3), (3, 0.12)),
            )

            for eighth in range(2):
                hit_start = beat_start + eighth * BEAT / 2
                add_noise_hit(
                    left,
                    right,
                    hit_start,
                    0.055,
                    0.09 if eighth == 0 else 0.065,
                    pan=-0.35 if (beat_index + eighth) % 2 == 0 else 0.35,
                    seed=event_seed,
                )
                event_seed += 1

        # Bright pluck pattern gives the reel forward motion without vocals.
        for eighth, note_index in enumerate(note_pattern):
            note = chord[note_index] * (2 if bar >= 8 else 1)
            add_tone(
                left,
                right,
                bar_start + eighth * BEAT / 2,
                BEAT * 0.42,
                note,
                0.12 * lift,
                decay=6.5,
                pan=-0.28 if eighth % 2 == 0 else 0.28,
                harmonics=((1, 1.0), (2, 0.42), (3, 0.17)),
            )

        if bar in (3, 7, 11):
            # Short rhythmic fill at the end of each four-bar phrase.
            for step in range(4):
                add_noise_hit(
                    left,
                    right,
                    bar_start + (3.0 + step * 0.23) * BEAT,
                    0.10,
                    0.20 + step * 0.025,
                    pan=-0.25 + step * 0.16,
                    seed=event_seed,
                    tone_frequency=145 + step * 25,
                )
                event_seed += 1

    # Gentle master fades and safe normalization.
    peak = max(max(abs(value) for value in left), max(abs(value) for value in right), 0.001)
    gain = 0.90 / peak
    fade_in = int(0.35 * SAMPLE_RATE)
    fade_out = int(1.1 * SAMPLE_RATE)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(OUTPUT), "wb") as stream:
        stream.setnchannels(2)
        stream.setsampwidth(2)
        stream.setframerate(SAMPLE_RATE)
        frames = array("h")
        for index in range(SAMPLES):
            fade = min(1.0, index / fade_in)
            if index >= SAMPLES - fade_out:
                fade *= max(0.0, (SAMPLES - index) / fade_out)
            frames.append(int(max(-1.0, min(1.0, left[index] * gain * fade)) * 32767))
            frames.append(int(max(-1.0, min(1.0, right[index] * gain * fade)) * 32767))
        stream.writeframes(frames.tobytes())

    return OUTPUT


if __name__ == "__main__":
    print(build())
