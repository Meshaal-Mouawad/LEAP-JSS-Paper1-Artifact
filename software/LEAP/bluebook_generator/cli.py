import os
import sys
from pathlib import Path
import click

# Local import: rely on package-relative path
from .main import generate_bluebook


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
def main():
    """AI-Powered KPI Extractor & Bluebook Generator CLI.

    Common usage:
      bluebook generate PATH/TO/SOURCE
    """


@main.command()
@click.argument(
    "source",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    required=False,
)
@click.option(
    "--clean-build/--no-clean-build",
    default=False,
    help="Delete docs/_build before building.",
)
@click.option(
    "--workers",
    type=int,
    default=lambda: int(os.environ.get("KPI_AI_WORKERS", "4")),
    show_default=True,
    help="Number of parallel detail workers (overrides KPI_AI_WORKERS env var).",
)
def generate(source: Path | None, clean_build: bool, workers: int):
    """Scan SOURCE for KPIs and build the documentation Bluebook.

    SOURCE defaults to the current working directory if omitted.
    """
    src = source or Path.cwd()
    if not src.exists() or not src.is_dir():
        click.echo(f"[bluebook] Source directory not found: {src}", err=True)
        sys.exit(2)

    # Propagate settings via env vars used by the pipeline
    if clean_build:
        os.environ["CLEAN_BUILD"] = "1"
    if workers and workers > 0:
        os.environ["KPI_AI_WORKERS"] = str(workers)

    click.echo(f"[bluebook] Generating Bluebook from: {src}")
    try:
        for msg in generate_bluebook(str(src)):
            click.echo(f"[bluebook] {msg}")
    except KeyboardInterrupt:
        click.echo("[bluebook] Interrupted.", err=True)
        sys.exit(130)
    except Exception as e:
        click.echo(f"[bluebook] Failed: {e}", err=True)
        sys.exit(1)

    repo_root = Path(__file__).resolve().parents[1]
    build_index = repo_root / "docs" / "_build" / "index.html"
    if build_index.exists():
        click.echo(f"[bluebook] Done. Open: {build_index}")
    else:
        click.echo(
            "[bluebook] Done. Note: Sphinx HTML build may have been skipped if 'sphinx-build' is not installed."
        )


if __name__ == "__main__":  # pragma: no cover
    main()
