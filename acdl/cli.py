from __future__ import annotations

import argparse
from pathlib import Path

from .core import (
    bootstrap,
    contract,
    handoff,
    maintain,
    preflight,
    retrofit,
    sync,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="acdl",
        description="Agent Collaborative Development Lifecycle CLI",
    )
    command_parent = argparse.ArgumentParser(add_help=False)
    command_parent.add_argument(
        "--root",
        default=".",
        help="Project root to operate on. Defaults to the current directory.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    retrofit_parser = subparsers.add_parser(
        "retrofit",
        parents=[command_parent],
        help="Generate first-pass ACDL project state and docs.",
    )
    retrofit_parser.add_argument("--force", action="store_true", help="Overwrite existing generated files.")

    bootstrap_parser = subparsers.add_parser(
        "bootstrap",
        parents=[command_parent],
        help="Create task context from project facts.",
    )
    bootstrap_parser.add_argument("--task", default="", help="Task description for this agent session.")

    contract_parser = subparsers.add_parser(
        "contract",
        parents=[command_parent],
        help="Create or validate a task contract.",
    )
    contract_parser.add_argument("--task", default="", help="Task goal.")
    contract_parser.add_argument("--scope", action="append", default=[], help="Allowed path or module. Repeatable.")
    contract_parser.add_argument("--forbid", action="append", default=[], help="Forbidden path or module. Repeatable.")
    contract_parser.add_argument("--check", action="append", default=[], help="Validation command. Repeatable.")

    subparsers.add_parser("sync", parents=[command_parent], help="Analyze changed files and write change impact.")
    subparsers.add_parser("preflight", parents=[command_parent], help="Run ACDL consistency checks.")
    subparsers.add_parser("handoff", parents=[command_parent], help="Generate a handoff pack.")
    subparsers.add_parser("maintain", parents=[command_parent], help="Check long-term knowledge maintenance risks.")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()

    if args.command == "retrofit":
        result = retrofit(root, force=args.force)
    elif args.command == "bootstrap":
        result = bootstrap(root, task=args.task)
    elif args.command == "contract":
        result = contract(root, task=args.task, scope=args.scope, forbid=args.forbid, checks=args.check)
    elif args.command == "sync":
        result = sync(root)
    elif args.command == "preflight":
        result = preflight(root)
    elif args.command == "handoff":
        result = handoff(root)
    elif args.command == "maintain":
        result = maintain(root)
    else:
        parser.error(f"Unknown command: {args.command}")

    print(result.message)
    for path in result.paths:
        print(f"- {path}")
    return result.exit_code
