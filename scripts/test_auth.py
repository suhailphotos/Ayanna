from oauthmanager.core import get_client
sp = get_client("spotify", open_browser=False)

print("Fetching playlists...")
pls = sp.current_user_playlists(limit=10)["items"]
for p in pls:
    print(f"{p['name']} ({p['id']}) by {p['owner']['display_name']}")
