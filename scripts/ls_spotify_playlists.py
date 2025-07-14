# scripts/ls_spotify_playlists.py

from oauthmanager.core import get_client

sp = get_client("spotify")
offset = 0
total = 0
print(f"{'Playlist Name':40} {'ID':35} {'Owner':20} {'Tracks'}")
print("-" * 90)

while True:
    page = sp.current_user_playlists(limit=50, offset=offset)
    items = page["items"]
    if not items:
        break
    for p in items:
        print(f"{p['name'][:38]:40} {p['id']:35} {p['owner']['display_name'] or p['owner']['id']:<20} {p['tracks']['total']}")
        total += 1
    offset += len(items)

print(f"\nTotal playlists: {total}")
