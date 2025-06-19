import os
import shutil
import zipfile
from insightface.app import FaceAnalysis

def ensure_antelopev2_ready(ctx_id=0, verbose=True):
    models_dir = os.path.expanduser("~/.insightface/models")
    model_zip = os.path.join(models_dir, "antelopev2.zip")
    model_dir = os.path.join(models_dir, "antelopev2")
    antelope_inner = os.path.join(model_dir, "antelopev2")

    # Step 1: Download via API, will error if first time
    try:
        app = FaceAnalysis(name='antelopev2')
        app.prepare(ctx_id=ctx_id)
        if verbose:
            print("antelopev2 model loaded and ready!")
        return app
    except AssertionError:
        if verbose:
            print("Model files not fully ready, fixing structure...")

    # Step 2: If zip exists, unzip it
    if os.path.isfile(model_zip):
        if verbose:
            print("Extracting antelopev2.zip...")
        with zipfile.ZipFile(model_zip, 'r') as zip_ref:
            zip_ref.extractall(model_dir)
        os.remove(model_zip)

    # Step 3: Flatten nested folder if present
    if os.path.isdir(antelope_inner):
        if verbose:
            print("Flattening nested antelopev2 directory...")
        for filename in os.listdir(antelope_inner):
            src = os.path.join(antelope_inner, filename)
            dst = os.path.join(model_dir, filename)
            if not os.path.exists(dst):
                shutil.move(src, dst)
        os.rmdir(antelope_inner)

    # Step 4: Try to load again (should succeed now)
    app = FaceAnalysis(name='antelopev2')
    app.prepare(ctx_id=ctx_id)
    if verbose:
        print("antelopev2 model loaded and ready!")
    return app

if __name__ == "__main__":
    ensure_antelopev2_ready(ctx_id=0)  # 0 = GPU, -1 = CPU
