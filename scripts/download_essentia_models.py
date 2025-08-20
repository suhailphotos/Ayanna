#!/usr/bin/env python3
"""
test_essentia_ml.py

Test extraction of modern Essentia high-level features using TF/ONNX models.

Usage:
  ESSENTIA_MODEL_PATH=/mnt/ai/models/essentia \
  python scripts/test_essentia_ml.py /path/to/audio.mp3

You'll need:
  - msd-musicnn.pb, msd-musicnn.json in $ESSENTIA_MODEL_PATH/msd-musicnn/
  - mood_acoustic-msd-musicnn.pb, mood_acoustic-msd-musicnn.json in $ESSENTIA_MODEL_PATH/mood_acoustic-msd-musicnn/
"""

import sys, os
from pathlib import Path

try:
    import essentia
    from essentia.standard import MonoLoader, TensorflowPredictMusiCNN, TensorflowPredict2D
except ImportError:
    print("Essentia 2.x with Tensorflow support required. Try: pip install essentia-tensorflow")
    sys.exit(1)

# Model paths
MODEL_PATH = os.environ.get("ESSENTIA_MODEL_PATH", "/mnt/ai/models/essentia")
EMBEDDING_NAME = "msd-musicnn"
CLASSIFIER_NAME = "mood_acoustic-msd-musicnn"

EMBEDDING_MODEL = os.path.join(MODEL_PATH, EMBEDDING_NAME, "msd-musicnn.pb")
EMBEDDING_METADATA = os.path.join(MODEL_PATH, EMBEDDING_NAME, "msd-musicnn.json")
CLASSIFIER_MODEL = os.path.join(MODEL_PATH, CLASSIFIER_NAME, "mood_acoustic-msd-musicnn.pb")
CLASSIFIER_METADATA = os.path.join(MODEL_PATH, CLASSIFIER_NAME, "mood_acoustic-msd-musicnn.json")

def main(audio_path):
    audio = MonoLoader(filename=audio_path, sampleRate=16000)() # TF models expect 16kHz

    # 1. Extract embedding
    musicnn = TensorflowPredictMusiCNN(
        graphFilename=EMBEDDING_MODEL,
        output="model/dense/BiasAdd",    # Check JSON for output layer
        loadUpstream=True,
        backend='tensorflow',
        inferenceBatchSize=1,
        computeEmbeddings=True,
        inputName="model/input_audio",
        outputNames=["model/dense/BiasAdd"],
        modelMetaFilename=EMBEDDING_METADATA
    )
    embedding = musicnn(audio)
    # If embedding is 2D, take mean over time
    if len(embedding.shape) == 2:
        embedding = embedding.mean(axis=0)

    # 2. Run classifier
    classifier = TensorflowPredict2D(
        graphFilename=CLASSIFIER_MODEL,
        modelMetaFilename=CLASSIFIER_METADATA,
        backend='tensorflow',
        output="output",   # check .json for output node name!
    )
    out = classifier(embedding.reshape(1, -1))
    print(f"mood_acoustic: {out}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/test_essentia_ml.py /path/to/audio.mp3")
        sys.exit(1)
    main(sys.argv[1])
