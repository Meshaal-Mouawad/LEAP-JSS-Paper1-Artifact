"""Enable running the CLI via:

    python -m bluebook_generator --help

This works even if the `bluebook` console script hasn't been created
on your PATH yet (e.g., after an install glitch)."""

from .cli import main


if __name__ == "__main__":  # pragma: no cover
    main()
