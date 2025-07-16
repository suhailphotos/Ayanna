import click, itertools
from tabulate import tabulate
from oauthmanager.core import get_client

sp = get_client("spotify")

# ── minimal renderer ─────────────────────────────────────────────
def _render(rows, *, head=False, head_n=20, headers="keys"):
    if head:
        rows = rows[:head_n]
    return tabulate(rows, headers=headers, tablefmt="github", stralign="left")

def _fetch_playlists():
    lim = 50
    off = 0
    while True:
        page = sp.current_user_playlists(limit=lim, offset=off)
        yield from page["items"]
        if page["next"] is None:
            break
        off += lim

@click.group(help="Spotify live data")
def spotify(): ...

@spotify.command("ls")
@click.argument(
    "entity",
    type=click.Choice(["playlist", "track"]),
    default="playlist",
)
@click.option("--head", is_flag=True, help="show only first 20 rows")
@click.option("--head-n", default=20, show_default=True)
def ls(entity, head, head_n):
    if entity == "playlist":
        rows = [
            {
                "id": p["id"],
                "name": p["name"],
                "owner": p["owner"]["display_name"] or p["owner"]["id"],
                "tracks": p["tracks"]["total"],
            }
            for p in _fetch_playlists()
        ]
        click.echo(_render(rows, head=head, head_n=head_n))
