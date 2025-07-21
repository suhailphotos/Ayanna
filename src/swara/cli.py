"""
Swara CLI
=========

$ swara init                 # one-time setup
$ swara download             # run the downloader
"""

from __future__ import annotations
from swara import db_cli
from swara.downloader import provider_snapshot
from swara.providers.spotify_cli import spotify
from swara.models import Track, Playlist, ExcludePlaylist, ExcludeTrack
from swara.db import get_session
from swara.sync import sync_db, prune_orphans
from sqlalchemy import delete, update, select
import shutil, os, sys, subprocess, json
from pathlib import Path
import click
import sys, pydoc


PKG_ROOT   = Path(__file__).resolve().parent
CONFIG_SRC = PKG_ROOT / ".config"
CONFIG_DIR = Path(os.getenv("XDG_CONFIG_HOME", Path.home() / ".config")) / "swara"
TEMPLATE_FILES = [("exclude.json", "exclude.json", False)]
RAW = Path(os.getenv("DATASET", PKG_ROOT.parents[1] / "data")) / "raw"



# ──────────────────────────────────────────────────────────────────────────────
def copy_templates() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    for src_name, dest_name, overwrite in TEMPLATE_FILES:
        src  = CONFIG_SRC / src_name
        dest = CONFIG_DIR / dest_name
        if not src.exists():
            click.secho(f"Template missing in package: {src}", fg="red")
            continue
        if dest.exists() and not overwrite:
            click.echo(f"· {dest.name} already exists – skipping")
            continue
        shutil.copy2(src, dest)
        click.echo(f"· Copied {dest.name}")

# ──────────────────────────────────────────────────────────────────────────────
@click.group(help="Swara command-line interface – run `swara download` etc.")
def cli() -> None:  # pragma: no cover
    pass

@cli.command("init", help="Create ~/.config/swara and copy template files")
def cli_init() -> None:
    click.secho("Initialising Swara", fg="cyan")
    copy_templates()
    click.secho("Done.", fg="green")

@cli.command("download", help="Scan your Spotify library then download pending tracks")
@click.option("--dry-run",      is_flag=True, help="List URLs without downloading")
@click.option("-v", "--verbose", is_flag=True, help="Show playlists while scanning")
@click.option("--clear-cache",  is_flag=True, help="Delete ~/.spotdl/ before downloading")
def cli_download(dry_run: bool, verbose: bool, clear_cache: bool) -> None:
    from swara.downloader import main as run_dl
    run_dl(dry_run=dry_run, verbose=verbose, clear_cache=clear_cache)

@cli.group("db", help="SQLite / Postgres housekeeping")
def db_group(): ...

@db_group.command("ls")
@click.argument("table", required=False)
@click.option("--filter")
@click.option("--full", is_flag=True)
@click.option("--head", is_flag=True)
@click.option("--head-n", default=20, show_default=True)
def db_ls(table, filter, full, head, head_n):
    text = db_cli.ls(table, filter, full, head, head_n)

    # ── use pager when the output is “big” and we’re in a TTY ──
    lines = text.count("\n")
    if lines > 60 and sys.stdout.isatty() and not head:
        pydoc.pager(text)
    else:
        click.echo(text)

@db_group.command("schema")
def db_schema():
    db_cli.schema_report()

@db_group.command("create")
def db_create():
    db_cli.create_db()

@db_group.command("import-exclusions")
@click.argument("json_path", type=click.Path(exists=True))
def db_import_exc(json_path):
    db_cli.import_exclusions(json_path)

@cli.command(help="Reconcile DB ↔ Spotify.  DB mutates, files optional.")
@click.option("--remove-files", is_flag=True,
              help="Delete audio files as soon as their DB row is dropped.")
@click.option("--prune", is_flag=True,
              help="Also delete orphan mp3 that are no longer in DB.")
def sync(remove_files, prune):
    report = sync_db(remove_files=remove_files, prune=prune)
    click.echo(report)

@cli.command(help="Remove audio files whose track is no longer in the DB")
@click.option("--yes", is_flag=True, help="Do not ask for confirmation")
def prune(yes):
    n = prune_orphans(ask=not yes)
    if n:
        click.secho(f"Deleted {n} files.", fg="yellow")
    else:
        click.secho("✓ No orphan files found.", fg="green")


cli.add_command(spotify, name="spotify")

if __name__ == "__main__":
    cli()
