# Swara

Swara automatically organises your music by **how it sounds**, not by the messy genre tags on streaming services.

* Extract every track you own from Spotify  
* Download real audio files (spotDL)  
* Generate CLAP embeddings for each song  
* Cluster similar-sounding tracks  
* Train a classifier so future songs drop into the right bucket automatically  

_Why “Swara”?_  
In Sanskrit it means a musical note—the perfect shorthand for a tool that understands the notes themselves.

---

## Quick start

```bash
conda env create -f environment.yml
conda activate swara-dev
poetry install --sync   # locks dependencies for publishing
python scripts/fetch_all.py
```

Audio lands in data/raw/.

---

## 7 · Tiny oauthManager tweak (optional)

SpotDL can pick up `SPOTIPY_CLIENT_ID` / `SPOTIPY_CLIENT_SECRET` environment vars.  
If you’d like to avoid an extra OAuth browser pop-up you can:

1. Extend `SpotifyProvider.build_client()` to `os.environ.setdefault("SPOTIPY_CLIENT_ID", secrets["client_id"])` (and secret).
2. SpotDL will reuse those creds automatically.

Totally optional—the current flow already works.

---

## 8 · Next steps after download

* **Audio deduplication** – compute SHA-256 of every file, drop duplicates by hash *and* by Spotify Track ID.  
* **Embedding extraction** – pass each unique file through CLAP, write one `.npy` row per song.  
* **Exploration notebook** – UMAP scatter plot; eyeball weird clusters.  
* **K-Means** – pick `k` via elbow / silhouette; save `clusters.csv`.  
* **Random Forest training** – fit on `(embedding → cluster_id)`, save to `$SWARA_MODELS`.  
* **API wrapper** – `swara.app.main` exposes `predict(file_path)` so future tracks get an instant cluster.  
* **Playlist exporter** – create / update Spotify playlists named like `Swara · Cluster 07`.

Everything above is already scaffolded—you just fill in the blanks.

Have fun building 🎶


