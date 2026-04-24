# ACDL

ACDL (**Agent Collaborative Development Lifecycle**) is a CLI for stabilizing multi-agent software collaboration.

It maintains a shared state source that coding agents can read, update, and verify through a fixed lifecycle:

```bash
acdl retrofit
acdl bootstrap
acdl contract
acdl sync
acdl preflight
acdl handoff
acdl maintain
```

The project is currently an MVP implemented with Python standard library only.

## Install

Install the published wheel. This does not require cloning the ACDL repository:

```bash
python3 -m pip install --user "https://github.com/TengShao/ACDL/releases/download/v0.1.0/acdl-0.1.0-py3-none-any.whl"
```

Verify:

```bash
acdl --help
```

If your shell cannot find `acdl`, make sure Python's user scripts directory is on `PATH`.

On macOS this is commonly:

```bash
$HOME/Library/Python/<python-version>/bin
```

For example:

```bash
export PATH="$HOME/Library/Python/3.14/bin:$PATH"
```

Uninstall:

```bash
python3 -m pip uninstall acdl
```

## Usage

After installation, run `acdl` from any project checkout.

First-time project onboarding:

```bash
acdl retrofit --root /path/to/project
```

Per-task flow:

```bash
acdl bootstrap --root /path/to/project --task "Implement login"
acdl contract --root /path/to/project --task "Implement login" --scope src/ --check "npm run test"
acdl sync --root /path/to/project
acdl preflight --root /path/to/project
acdl handoff --root /path/to/project
```

Long-term maintenance:

```bash
acdl maintain --root /path/to/project
```

## Distribution

For the team, the intended distribution path is:

1. Maintainer tags a release, for example `v0.1.0`.
2. GitHub Actions builds `acdl-0.1.0-py3-none-any.whl`.
3. GitHub Release stores the wheel.
4. Team members install the wheel URL directly.

See [docs/distribution.md](docs/distribution.md) for install, upgrade, and release options.

## Development

```bash
python3 -m unittest discover -s tests
sh scripts/build.sh
```
