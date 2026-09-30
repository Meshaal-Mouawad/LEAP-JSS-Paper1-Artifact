#!/usr/bin/env python3
"""
Simple verification runner for the KPI Bluebook generator.
It executes the pipeline against the bundled demonstration workspace and prints progress lines.
Usage:
  python run_generation.py [<source_dir>]
The public ``sample_project`` alias resolves to the bundled demonstration workspace.
"""

import sys
import pathlib

from bluebook_generator.main import generate_bluebook
from bluebook_generator.paths import DEMO_PROJECT_DIR, resolve_workspace_path


def main(argv: list[str]) -> int:
    source = resolve_workspace_path(argv[1]) if len(argv) > 1 else DEMO_PROJECT_DIR
    for msg in generate_bluebook(str(source)):
        print(msg)
    # success exit - errors are printed by the generator and pipeline continues
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
