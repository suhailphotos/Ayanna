from oauthmanager.core import get_client
from swara.db import get_session
from swara.models import User, Playlist

sp = get_client("spotify")
owners = {}

offset = 0
while True:
    page = sp.current_user_playlists(limit=50, offset=offset)
    items = page["items"]
    if not items:
        break
    for pl in items:
        owner = pl["owner"]
        oid = owner["id"]
        if oid not in owners:
            owners[oid] = owner.get("display_name")
    offset += len(items)

# Insert into User table if not present
with get_session() as ses:
    for oid, name in owners.items():
        # merge: insert if not present, update if already exists
        ses.merge(User(id=oid, display_name=name))
    ses.commit()

print(f"Inserted {len(owners)} users.")
