import click, itertools
from oauthmanager.core import get_client
from swara.formatters import render_table   # universal printer

sp = get_client("spotify")

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
@click.argument("entity", type=click.Choice(["playlist", "track"]),
                default="playlist")
def ls(entity):
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
        click.echo(render_table(rows))
