# ACDL

ACDL (**Agent Collaborative Development Lifecycle**) is a repository-local CLI for stabilizing multi-agent software collaboration.

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

## Local Usage

Run commands directly from this repository:

```bash
python3 -m acdl retrofit --root /path/to/project
python3 -m acdl bootstrap --root /path/to/project --task "Implement login"
python3 -m acdl contract --root /path/to/project --task "Implement login"
python3 -m acdl sync --root /path/to/project
python3 -m acdl preflight --root /path/to/project
python3 -m acdl handoff --root /path/to/project
python3 -m acdl maintain --root /path/to/project
```

## Development

```bash
python3 -m unittest discover -s tests
```
