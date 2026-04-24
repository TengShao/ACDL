# ACDL

ACDL (**Agent Collaborative Development Lifecycle**) is a CLI for stabilizing multi-agent software collaboration.

It is designed for teams where multiple people use different coding agents against the same projects. The goal is not to “write more docs”; the goal is to maintain a shared project state that agents can read, humans can review, machines can verify, and future agents can resume from.

## Core Model

ACDL treats each repository as a small collaboration operating system:

```text
project repository
→ acdl CLI
→ shared state source
→ agent task workflow
→ preflight / CI checks
→ maintained project knowledge
```

The shared state source is expressed through `AGENTS.md`, `docs/`, `.acdl/` task artifacts, preflight reports, and handoff packs.

ACDL protects five collaboration invariants:

- **Context**: agents start from the same project facts.
- **Boundary**: every task has an explicit allowed and forbidden scope.
- **Contract**: API, schema, config, permission, and data model changes are synchronized.
- **Verification**: critical rules are checked by commands, not memory.
- **Continuity**: the next agent can continue without rediscovering the project state.

## Lifecycle

ACDL maintains that shared state through a fixed lifecycle:

```bash
acdl retrofit
acdl bootstrap
acdl contract
acdl sync
acdl preflight
acdl handoff
acdl maintain
```

- `retrofit`: agent-led onboarding for existing projects. Scans the repository and generates the first `AGENTS.md` plus baseline docs.
- `bootstrap`: creates task context before an agent starts work.
- `contract`: defines task goal, allowed scope, forbidden scope, checks, and sync expectations.
- `sync`: analyzes changed files and reports which shared facts may need updates.
- `preflight`: runs required checks and detects missing fact-source updates before review.
- `handoff`: creates a continuation pack for the next agent or teammate.
- `maintain`: checks long-term knowledge drift and stale shared state.

The project is currently an MVP implemented with Python standard library only.

## Install

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

This generates the baseline collaboration state:

```text
AGENTS.md
docs/architecture.md
docs/contracts.md
docs/workflows.md
docs/active-work.md
docs/open-questions.md
docs/decisions/0001-current-architecture.md
.acdl/project-state.json
```

Per-task flow:

```bash
acdl bootstrap --root /path/to/project --task "Implement login"
acdl contract --root /path/to/project --task "Implement login" --scope src/ --check "npm run test"
acdl sync --root /path/to/project
acdl preflight --root /path/to/project
acdl handoff --root /path/to/project
```

During development, agents should stay inside the task contract. Out-of-scope bugs, refactors, or architecture concerns should be recorded as follow-ups unless the task contract explicitly allows expanding scope.

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
