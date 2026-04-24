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

Clone or copy this repository, then install the global launcher:

```bash
sh scripts/install.sh
```

Verify:

```bash
acdl --help
```

By default, the installer writes the launcher to:

```bash
$HOME/.local/bin/acdl
```

If your shell cannot find `acdl`, make sure this directory is on `PATH`:

```bash
export PATH="$HOME/.local/bin:$PATH"
```

Uninstall:

```bash
sh scripts/uninstall.sh
```

Optional Python package install is also supported when the target machine has Python packaging tools available:

```bash
python3 -m pip install --user .
```

## Usage

After installation, run:

```bash
acdl retrofit --root /path/to/project
acdl bootstrap --root /path/to/project --task "Implement login"
acdl contract --root /path/to/project --task "Implement login"
acdl sync --root /path/to/project
acdl preflight --root /path/to/project
acdl handoff --root /path/to/project
acdl maintain --root /path/to/project
```

You can also run directly from the source checkout without installing:

```bash
python3 -m acdl --help
```

## Distribution

For a small team, the simplest distribution path is:

1. Put this repository in a shared Git location.
2. Team members clone it.
3. Team members run `sh scripts/install.sh`.
4. Everyone uses the global `acdl` command against their project repositories.

See [docs/distribution.md](docs/distribution.md) for install, upgrade, and release options.

## Development

```bash
python3 -m unittest discover -s tests
```
