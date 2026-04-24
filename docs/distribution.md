# ACDL Distribution Guide

This guide explains how to share ACDL with teammates without asking them to clone the ACDL source repository.

## Recommended Team Distribution

Use GitHub Releases as the distribution source.

```bash
python3 -m pip install --user "https://github.com/TengShao/ACDL/releases/download/v0.1.0/acdl-0.1.0-py3-none-any.whl"
acdl --help
```

This installs a normal Python console command named `acdl`.

Teammates do not need the ACDL source checkout. They only need Python and pip.

## Upgrade

Install the newer wheel URL:

```bash
python3 -m pip install --user --upgrade "https://github.com/TengShao/ACDL/releases/download/v0.1.1/acdl-0.1.1-py3-none-any.whl"
```

## Uninstall

```bash
python3 -m pip uninstall acdl
```

## PATH Notes

`pip install --user` writes the `acdl` executable into Python's user scripts directory.

On macOS this is commonly:

```bash
$HOME/Library/Python/<python-version>/bin
```

For example:

```bash
export PATH="$HOME/Library/Python/3.14/bin:$PATH"
```

On Linux this is commonly:

```bash
$HOME/.local/bin
```

For example:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

## Maintainer Build

Maintainers build the wheel from this repository:

```bash
python3 -m unittest discover -s tests
sh scripts/build.sh
```

The wheel is written to `dist/`:

```text
dist/acdl-0.1.0-py3-none-any.whl
```

The build script uses only Python standard library modules. It does not require `setuptools`, `wheel`, or `python -m build`.

## Release Flow

1. Update `version` in `pyproject.toml`.
2. Run tests and `sh scripts/build.sh`.
3. Commit the version change.
4. Create and push a tag, for example `v0.1.0`.
5. GitHub Actions builds and uploads the wheel to the GitHub Release.
6. Share the release wheel URL with teammates.

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
