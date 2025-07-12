#!/usr/bin/env python3
"""
List all playlists for the current Spotify user.
Run with: python scripts/lsPlaylist.py
"""

from oauthmanager.core import get_client

def main():
    sp = get_client(
        "spotify",
        scopes=["playlist-read-private", "user-library-read"],
        open_browser=False
    )

    all_playlists = []
    offset = 0
    print("Fetching playlists...")
    while True:
        page = sp.current_user_playlists(limit=50, offset=offset)
        items = page["items"]
        if not items:
            break
        all_playlists.extend(items)
        offset += len(items)

    print(f"\nTotal playlists: {len(all_playlists)}\n")
    for p in all_playlists:
        owner = p["owner"]["display_name"] or "Spotify"
        print(
            f"{p['name']:<40} "
            f"{p['id']:<35} "
            f"by {owner:<20} "
            f"({p['tracks']['total']} tracks) "
            f"{'public' if p['public'] else 'private'}"
        )

if __name__ == "__main__":
    main()
