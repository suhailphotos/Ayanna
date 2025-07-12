"""
Swara CLI
=========

$ swara init                 # one-time setup
$ swara download             # run the downloader
"""

from __future__ import annotations
import shutil, os, sys, subprocess, json
from pathlib import Path
import click

PKG_ROOT   = Path(__file__).resolve().parent
CONFIG_SRC = PKG_ROOT / ".config"
CONFIG_DIR = Path(os.getenv("XDG_CONFIG_HOME", Path.home() / ".config")) / "swara"
TEMPLATE_FILES = [("exclude.json", "exclude.json", False)]

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

@cli.command("download", help="Download all eligible Spotify tracks")
@click.option("--dry-run", is_flag=True, help="List tracks but don’t download")
def cli_download(dry_run: bool) -> None:
    from swara.downloader import main as run_dl
    run_dl(dry_run=dry_run)

if __name__ == "__main__":
    cli()
