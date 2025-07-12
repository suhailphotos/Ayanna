import json
from pathlib import Path

MY_NAME = "Suhail Suhail"
CONFIG = Path(__file__).parents[1] / "src" / "swara" / ".config"
EXCLUDE_JSON = CONFIG / "exclude.json"

from oauthmanager.core import get_client
sp = get_client("spotify")  # token comes from oauthManager

all_playlists = []
offset = 0
while True:
    page = sp.current_user_playlists(limit=50, offset=offset)
    items = page["items"]
    if not items:
        break
    all_playlists.extend(items)
    offset += len(items)  # next page

# Filter playlists NOT created by you and format the output
other_playlists = [
    {
        "id": p["id"],
        "name": p["name"],
        "owner": p["owner"]["display_name"] or "Spotify",
        "tracks": p["tracks"]["total"],
        "public": p["public"]
    }
    for p in all_playlists
    if (p["owner"]["display_name"] or "Spotify") != MY_NAME
]

output = {
    "playlists": other_playlists,
    "tracks": []
}

with open(EXCLUDE_JSON, "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

