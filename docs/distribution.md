# ACDL Distribution Guide

This guide explains how to share ACDL with teammates so they can use the global `acdl` command instead of running `python3 -m acdl` from this source directory.

## Recommended Team Distribution

Use a shared Git repository as the distribution source.

```bash
git clone <your-acdl-repo-url>
cd co-op-skills
sh scripts/install.sh
acdl --help
```

The installer creates a lightweight launcher at:

```bash
$HOME/.local/bin/acdl
```

The launcher points at the cloned source directory by setting `PYTHONPATH` and running `python3 -m acdl`. This keeps distribution dependency-free: teammates do not need setuptools, wheel, pipx, or a package registry.

For active ACDL development, keep using the same launcher. Changes in the checkout are immediately reflected in the `acdl` command.

## Upgrade

From the local checkout:

```bash
git pull
```

No reinstall is required after `git pull` because the launcher points at the checkout.

If the checkout moved to another directory:

```bash
sh scripts/install.sh
```

## Uninstall

```bash
sh scripts/uninstall.sh
```

## PATH Notes

The default installer writes to:

```bash
$HOME/.local/bin
```

If `acdl --help` says command not found, add the scripts directory to your shell profile:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

To install the launcher somewhere else:

```bash
ACDL_INSTALL_BIN=/usr/local/bin sh scripts/install.sh
```

## Optional Pip Installation

ACDL also has Python package metadata in `pyproject.toml`.

Use this path when the target machine has Python packaging tools available:

```bash
python3 -m pip install --user .
```

This creates a normal Python console script entry point named `acdl`. If packaging tools are not available, prefer `sh scripts/install.sh`.

## Wheel / Archive Distribution

For teams that do not want every member to clone the source repository:

1. Build a wheel in a clean environment.
2. Share the `.whl` file through an internal file server or artifact registry.
3. Team members install the wheel with pip.

Install from a wheel:

```bash
python3 -m pip install --user acdl-0.1.0-py3-none-any.whl
```

## Current Release Contract

ACDL v0.1.0 exposes these commands:

```bash
acdl retrofit
acdl bootstrap
acdl contract
acdl sync
acdl preflight
acdl handoff
acdl maintain
```

The CLI is still an MVP. Treat generated docs and reports as agent-readable drafts that need project-owner confirmation for business intent, high-risk boundaries, and ambiguous project facts.
