from __future__ import annotations

import argparse
import sys

from tools.harness.rules_manifest import DEFAULT_LINT_PATHS
from tools.harness.rules_manifest import run_rules


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m tools.harness")
    subparsers = parser.add_subparsers(dest="command")

    lint_parser = subparsers.add_parser("lint")
    lint_parser.add_argument("paths", nargs="*", default=list(DEFAULT_LINT_PATHS))

    args = parser.parse_args(argv)
    if args.command != "lint":
        parser.print_help()
        return 1

    diagnostics = run_rules(args.paths)
    if not diagnostics:
        print("Harness lint passed.")
        return 0

    for diagnostic in diagnostics:
        print(diagnostic.render())

    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
