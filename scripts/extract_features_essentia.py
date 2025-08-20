#!/usr/bin/env python3
"""
extract_features_essentia.py

Run this script as:
$ poetry run python scripts/extract_features_essentia.py /path/to/audio.mp3

Outputs a simple dict of features (prints to stdout).
"""

import sys
from pathlib import Path

try:
    import essentia
    import essentia.standard as es
except ImportError:
    print("Essentia is not installed. Try: pip install essentia")
    sys.exit(1)

def extract_features(audio_path):
    audio = es.MonoLoader(filename=str(audio_path))()
    # Compute low-level features
    mfcc = es.MFCC(numberCoefficients=13)
    mfcc_bands, mfcc_coeffs = mfcc(audio)
    spectral_centroid = es.CentralMoments()(audio)[0]
    rms = es.RMS()(audio)
    zcr = es.ZeroCrossingRate()(audio)
    # Rhythm features
    bpm = es.RhythmExtractor2013()(audio)[0]
    danceability = es.Danceability()(audio)
    # Tonal/key
    key, scale, strength = es.KeyExtractor()(audio)
    # High-level

    features, _ = es.MusicExtractor(
        lowlevelFrameSize=2048, lowlevelHopSize=1024
    )(str(audio_path))
    # Safely get high-level features or fallback to None/0.0
    def safe(key, default=0.0):
        try:
            return float(features[key])
        except Exception:
            return default
    
    return {
        "bpm": bpm,
        "danceability": danceability,
        "key": key,
        "scale": scale,
        "mfcc_mean": [float(x) for x in mfcc_coeffs],
        "spectral_centroid_mean": float(spectral_centroid),
        "rms_mean": float(rms),
        "zero_crossing_rate": float(zcr),
        "mood_acoustic": safe('highlevel.mood_acoustic.confidence', 0.0),
        "mood_aggressive": safe('highlevel.mood_aggressive.confidence', 0.0),
        "voice_instrumental": safe('highlevel.voice_instrumental.confidence', 0.0),
    }

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/extract_features_essentia.py /path/to/audio.mp3")
        sys.exit(1)
    audio_path = Path(sys.argv[1])
    if not audio_path.exists():
        print("File does not exist:", audio_path)
        sys.exit(1)
    features = extract_features(audio_path)
    for k, v in features.items():
        print(f"{k}: {v}")
