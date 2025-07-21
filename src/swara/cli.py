"""
Swara CLI – now with backup/restore helpers for Postgres
========================================================

```bash
# Examples
swara db backup                    # → ./.backup/swara-<UTC‑timestamp>.sql.gz
swara db backup ./dumps/foo.sql.gz # custom path
swara db restore ./dumps/foo.sql.gz --drop
```
$ swara init                 # one-time setup
$ swara download             # run the downloader


Notes
-----
* `pg_dump` / `pg_restore` must be on the PATH (they are in the official
  postgres Docker image and most distro packages).
* Environment variables come from **.env** (loaded via `python‑dotenv`) and
  then fall back to the live shell. This keeps the behaviour identical inside
  and outside a container.
* Works exclusively with `pg_dump --format=custom` compressed archives.
* Backups are stored under `<project>/.backup/` by default – a hidden dir so
  it doesn’t clutter the repo.
"""

from __future__ import annotations

import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

import click


from swara import db_cli
from swara.downloader import provider_snapshot
from swara.providers.spotify_cli import spotify
from swara.models import Track, Playlist, ExcludePlaylist, ExcludeTrack
from swara.db import get_session
from swara.sync import sync_db, prune_orphans
from sqlalchemy import delete, update, select
import shutil, sys, pydoc, json, re

# ---------------------------------------------------------------------------
# Project paths & env
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(os.getenv("PROJECT_ROOT", Path(__file__).resolve().parents[1]))
ENV_FILE     = PROJECT_ROOT / ".env"

# Load .env first so anything defined there is present for the rest of the file
if ENV_FILE.exists():
    load_dotenv(dotenv_path=ENV_FILE, override=False)  # leave already‑set vars intact

BACKUP_DIR   = PROJECT_ROOT / ".backup"
BACKUP_DIR.mkdir(exist_ok=True)

PKG_ROOT   = Path(__file__).resolve().parent
CONFIG_SRC = PKG_ROOT / ".config"
CONFIG_DIR = Path(os.getenv("XDG_CONFIG_HOME", Path.home() / ".config")) / "swara"
TEMPLATE_FILES = [("exclude.json", "exclude.json", False)]
RAW = Path(os.getenv("DATASET", PKG_ROOT.parents[1] / "data")) / "raw"

# =============================================================================
# Helper – dump & restore
# =============================================================================

def _run(cmd: list[str]) -> None:
    """Sub‑process wrapper with prettier error handling."""
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as exc:
        click.secho(f"✗ Command failed → {' '.join(cmd)}", fg="red")
        raise SystemExit(exc.returncode)


def _default_dump_name() -> Path:
    ts = datetime.utcnow().strftime("%Y%m%d-%H%M")
    return BACKUP_DIR / f"swara-{ts}.sql.gz"



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

def resolve_pg_url(db_url):
    """Return a plain Postgres URL for pg_dump/pg_restore."""
    if db_url is None:
        return None
    if db_url.startswith("postgresql+"):
        return re.sub(r"^postgresql\+\w+://", "postgresql://", db_url)
    return db_url

def resolve_sqlite_path(db_url):
    """Return SQLite DB path from the URL if present, else None."""
    if not db_url:
        return None
    if db_url.startswith("sqlite:///"):
        return db_url.replace("sqlite:///", "")
    elif db_url.startswith("sqlite:////"):  # for absolute path
        return db_url.replace("sqlite:////", "/")
    return None

# =============================================================================
# CLI
# =============================================================================

@click.group(help="Swara command-line interface – run `swara download` etc.")
def cli() -> None:  # pragma: no cover
    pass

@cli.command("init", help="Create ~/.config/swara and copy template files")
def cli_init() -> None:
    click.secho("Initialising Swara", fg="cyan")
    copy_templates()
    click.secho("Done.", fg="green")

# ---------------------------------------------------------------------------
# DB sub‑group – define *before* we decorate commands underneath.
# ---------------------------------------------------------------------------

@cli.group("db", help="SQLite / Postgres housekeeping")
def db_group():
    """Parent for db‑related commands"""
    pass


@db_group.command("backup", help="Dump the database to a backup file (.sql.gz for PG, .bak for SQLite)")
@click.argument("out", type=click.Path(dir_okay=False, path_type=Path), required=False)
def db_backup(out: Path | None):
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        click.secho("DATABASE_URL not set – cannot back up", fg="red")
        raise SystemExit(1)

    dump_path = out or _default_dump_name()
    dump_path.parent.mkdir(parents=True, exist_ok=True)

    if db_url.startswith("postgresql"):
        pg_url = resolve_pg_url(db_url)
        click.echo(f"Creating Postgres backup → {dump_path}")
        _run([
            "pg_dump",
            "--file", str(dump_path),
            "--dbname", pg_url,
            "--format=custom",
            "--no-owner", "--no-acl",
            "--compress=9",
        ])
    elif db_url.startswith("sqlite"):
        sqlite_path = resolve_sqlite_path(db_url)
        if not sqlite_path or not Path(sqlite_path).exists():
            click.secho("SQLite DB file not found.", fg="red")
            raise SystemExit(1)
        click.echo(f"Creating SQLite backup → {dump_path}")
        # Use the .backup command for safety, or just copy the file:
        _run([
            "sqlite3", sqlite_path, f".backup {dump_path}"
        ])
    else:
        click.secho(f"Unsupported database type: {db_url}", fg="red")
        raise SystemExit(1)

    click.secho("✓ Backup complete", fg="green")


@db_group.command("restore", help="Restore DB from a backup file")
@click.argument("dump", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--drop", is_flag=True, help="Drop existing objects before restore (pg only)")
def db_restore(dump: Path, drop: bool):
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        click.secho("DATABASE_URL not set – cannot restore", fg="red")
        raise SystemExit(1)

    if db_url.startswith("postgresql"):
        pg_url = resolve_pg_url(db_url)
        click.secho("Restoring Postgres database …", fg="yellow")
        cmd = [
            "pg_restore",
            "--dbname", pg_url,
            "--no-owner", "--no-acl",
        ]
        if drop:
            cmd.append("--clean")
        cmd.append(str(dump))
        _run(cmd)
    elif db_url.startswith("sqlite"):
        sqlite_path = resolve_sqlite_path(db_url)
        if not sqlite_path:
            click.secho("SQLite DB path could not be resolved.", fg="red")
            raise SystemExit(1)
        click.secho("Restoring SQLite database …", fg="yellow")
        # CAUTION: This will overwrite the SQLite database file!
        _run(["cp", str(dump), sqlite_path])
    else:
        click.secho(f"Unsupported database type: {db_url}", fg="red")
        raise SystemExit(1)

    click.secho("✓ Restore complete", fg="green")

@cli.command("download", help="Scan your Spotify library then download pending tracks")
@click.option("--dry-run",      is_flag=True, help="List URLs without downloading")
@click.option("-v", "--verbose", is_flag=True, help="Show playlists while scanning")
@click.option("--clear-cache",  is_flag=True, help="Delete ~/.spotdl/ before downloading")
def cli_download(dry_run: bool, verbose: bool, clear_cache: bool) -> None:
    from swara.downloader import main as run_dl
    run_dl(dry_run=dry_run, verbose=verbose, clear_cache=clear_cache)



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
