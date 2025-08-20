import spotipy
from spotipy.oauth2 import SpotifyOAuth

# Fill these in from your Spotify app dashboard
CLIENT_ID = "ee2f488d96a04a62a88936b97eb2c54f"
CLIENT_SECRET = "54a1811cdbcc4ee78824d17d18e10dfb"
REDIRECT_URI = "http://127.0.0.1:8765/callback"  # or your registered one

# Include all scopes you may need
SCOPES = [
    "playlist-read-private",
    "playlist-modify-private",
    "user-library-read",
    "user-read-private",
]  # This is usually enough. For audio-features, user auth is enough.

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    redirect_uri=REDIRECT_URI,
    scope=" ".join(SCOPES),
    open_browser=True,
    cache_path=".spotify_token"
))

# Test: Try any valid track ID
track_id = "11dFghVXANMlKmJXsNCbNl"
features = sp.audio_features([track_id])[0]

print("Audio Features for", track_id)
for k, v in features.items():
    print(f"{k}: {v}")
