from __future__ import annotations

import json
import os
import subprocess
import tomllib
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


DOC_FILES = {
    "architecture": Path("docs/architecture.md"),
    "contracts": Path("docs/contracts.md"),
    "workflows": Path("docs/workflows.md"),
    "active_work": Path("docs/active-work.md"),
    "open_questions": Path("docs/open-questions.md"),
    "decision": Path("docs/decisions/0001-current-architecture.md"),
}

EXCLUDED_DIRS = {
    ".git",
    ".acdl",
    ".venv",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    "target",
    ".next",
    ".cache",
}


@dataclass
class CommandResult:
    message: str
    paths: list[str]
    exit_code: int = 0


@dataclass
class ProjectScan:
    root: str
    generated_at: str
    tech_stack: list[str]
    commands: dict[str, str]
    docs: list[str]
    manifests: list[str]
    schemas: list[str]
    api_files: list[str]
    ci_files: list[str]
    tests: list[str]
    risk_areas: list[str]
    open_questions: list[str]


def retrofit(root: Path, force: bool = False) -> CommandResult:
    ensure_root(root)
    scan = scan_project(root)
    written: list[Path] = []

    written.extend(
        write_if_needed(
            root / "AGENTS.md",
            render_agents_md(scan),
            force=force,
        )
    )
    for name, relative in DOC_FILES.items():
        content = render_doc(name, scan)
        written.extend(write_if_needed(root / relative, content, force=force))

    written.extend(write_json(root / ".acdl/project-state.json", asdict(scan), force=True))
    written.extend(write_markdown(root / ".acdl/retrofit-summary.md", render_retrofit_summary(scan), force=True))

    return CommandResult(
        message=f"Retrofit complete. Generated or refreshed {len(written)} file(s).",
        paths=display_paths(root, written),
    )


def bootstrap(root: Path, task: str = "") -> CommandResult:
    ensure_root(root)
    state = load_or_scan_state(root)
    context = {
        "generated_at": now(),
        "task": task or "TODO: describe task",
        "project_state": state,
        "recent_changes": git_changed_files(root),
        "required_reads": required_reads(root),
    }
    written = []
    written.extend(write_json(root / ".acdl/context.json", context, force=True))
    written.extend(write_markdown(root / ".acdl/context.md", render_context_md(context), force=True))
    return CommandResult("Bootstrap context generated.", display_paths(root, written))


def contract(
    root: Path,
    task: str = "",
    scope: list[str] | None = None,
    forbid: list[str] | None = None,
    checks: list[str] | None = None,
) -> CommandResult:
    ensure_root(root)
    scope = scope or []
    forbid = forbid or []
    checks = checks or []
    payload = {
        "generated_at": now(),
        "task": task or "TODO: describe task",
        "allowed_scope": scope or ["TODO: declare allowed paths or modules"],
        "forbidden_scope": forbid or ["Unrelated files outside the task"],
        "acceptance_criteria": [
            "Implementation matches the task goal",
            "Relevant tests or checks pass",
            "Shared facts are synchronized when contracts change",
        ],
        "required_checks": checks or infer_default_checks(root),
        "required_sync_targets": [
            "AGENTS.md when commands or core rules change",
            "docs/contracts.md when API, schema, config, permission, or data contracts change",
            "docs/architecture.md when module responsibilities or data flow change",
            "docs/workflows.md when local, test, release, or deployment workflows change",
            "docs/active-work.md when collaborative task status or risk areas change",
        ],
    }
    written = []
    written.extend(write_json(root / ".acdl/task-contract.json", payload, force=True))
    written.extend(write_markdown(root / ".acdl/task-contract.md", render_task_contract_md(payload), force=True))
    return CommandResult("Task contract generated.", display_paths(root, written))


def sync(root: Path) -> CommandResult:
    ensure_root(root)
    changed = git_changed_files(root)
    impact = analyze_change_impact(changed)
    payload = {
        "generated_at": now(),
        "changed_files": changed,
        "impact": impact,
        "required_updates": required_updates_for_impact(impact),
    }
    written = []
    written.extend(write_json(root / ".acdl/change-impact.json", payload, force=True))
    written.extend(write_markdown(root / ".acdl/change-impact.md", render_change_impact_md(payload), force=True))
    return CommandResult("Change impact analyzed.", display_paths(root, written))


def preflight(root: Path) -> CommandResult:
    ensure_root(root)
    failures: list[str] = []
    warnings: list[str] = []

    required = [Path("AGENTS.md"), *DOC_FILES.values()]
    for relative in required:
        if not (root / relative).exists():
            failures.append(f"Missing required fact source: {relative}")

    if not (root / ".acdl/task-contract.json").exists():
        warnings.append("Missing .acdl/task-contract.json. Run `acdl contract` before task work.")

    changed = git_changed_files(root)
    impact = analyze_change_impact(changed)
    required_updates = required_updates_for_impact(impact)
    for target in required_updates:
        if not changed_or_exists(root, changed, target):
            warnings.append(f"Potential fact-source drift: {target} may need an update.")

    open_questions = root / "docs/open-questions.md"
    if open_questions.exists() and has_unresolved_questions(open_questions):
        warnings.append("docs/open-questions.md contains unresolved questions.")

    report = {
        "generated_at": now(),
        "status": "failed" if failures else "passed",
        "failures": failures,
        "warnings": warnings,
        "changed_files": changed,
        "impact": impact,
    }
    written = []
    written.extend(write_json(root / ".acdl/preflight-report.json", report, force=True))
    written.extend(write_markdown(root / ".acdl/preflight-report.md", render_preflight_md(report), force=True))
    exit_code = 1 if failures else 0
    return CommandResult(
        "Preflight failed." if failures else "Preflight passed with warnings." if warnings else "Preflight passed.",
        display_paths(root, written),
        exit_code=exit_code,
    )


def handoff(root: Path) -> CommandResult:
    ensure_root(root)
    context = read_text(root / ".acdl/context.md")
    contract_text = read_text(root / ".acdl/task-contract.md")
    impact_text = read_text(root / ".acdl/change-impact.md")
    payload = render_handoff_md(root, context, contract_text, impact_text)
    written = write_markdown(root / ".acdl/handoff-pack.md", payload, force=True)
    return CommandResult("Handoff pack generated.", display_paths(root, written))


def maintain(root: Path) -> CommandResult:
    ensure_root(root)
    findings: list[str] = []
    for relative in [Path("AGENTS.md"), *DOC_FILES.values()]:
        path = root / relative
        if not path.exists():
            findings.append(f"Missing {relative}")
        elif path.stat().st_size == 0:
            findings.append(f"Empty fact source: {relative}")

    duplicates = duplicated_headings(root)
    findings.extend(f"Repeated heading across docs: {heading}" for heading in duplicates)

    payload = {
        "generated_at": now(),
        "findings": findings,
        "status": "needs_attention" if findings else "healthy",
    }
    written = []
    written.extend(write_json(root / ".acdl/maintenance-report.json", payload, force=True))
    written.extend(write_markdown(root / ".acdl/maintenance-report.md", render_maintenance_md(payload), force=True))
    return CommandResult("Maintenance report generated.", display_paths(root, written))


def scan_project(root: Path) -> ProjectScan:
    files = list_project_files(root)
    manifests = detect_manifests(files)
    commands = detect_commands(root, manifests)
    tech_stack = detect_tech_stack(manifests, files)
    docs = [str(path) for path in files if path.name.lower().startswith("readme") or "docs" in path.parts]
    schemas = [str(path) for path in files if looks_like_schema(path)]
    api_files = [str(path) for path in files if looks_like_api(path)]
    ci_files = [str(path) for path in files if looks_like_ci(path)]
    tests = [str(path) for path in files if looks_like_test(path)]
    risk_areas = infer_risk_areas(schemas, api_files, ci_files)
    open_questions = infer_open_questions(commands, tech_stack, schemas, api_files)
    return ProjectScan(
        root=str(root),
        generated_at=now(),
        tech_stack=tech_stack,
        commands=commands,
        docs=docs[:80],
        manifests=[str(path) for path in manifests],
        schemas=schemas[:80],
        api_files=api_files[:120],
        ci_files=ci_files[:40],
        tests=tests[:120],
        risk_areas=risk_areas,
        open_questions=open_questions,
    )


def list_project_files(root: Path) -> list[Path]:
    results: list[Path] = []
    for current, dirs, files in os.walk(root):
        dirs[:] = [name for name in dirs if name not in EXCLUDED_DIRS]
        base = Path(current)
        for filename in files:
            path = base / filename
            try:
                relative = path.relative_to(root)
            except ValueError:
                continue
            results.append(relative)
    return sorted(results)


def detect_manifests(files: list[Path]) -> list[Path]:
    manifest_names = {
        "package.json",
        "pyproject.toml",
        "requirements.txt",
        "Cargo.toml",
        "go.mod",
        "pom.xml",
        "build.gradle",
        "composer.json",
        "Gemfile",
    }
    return [path for path in files if path.name in manifest_names]


def detect_commands(root: Path, manifests: list[Path]) -> dict[str, str]:
    commands: dict[str, str] = {}
    package_json = root / "package.json"
    if package_json.exists():
        try:
            scripts = json.loads(package_json.read_text(encoding="utf-8")).get("scripts", {})
            for name in ("dev", "test", "build", "lint", "start"):
                if name in scripts:
                    commands[name] = f"npm run {name}"
        except (OSError, json.JSONDecodeError):
            pass
    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        commands.setdefault("test", "python3 -m unittest discover -s tests")
    if Path("Cargo.toml") in manifests:
        commands.setdefault("test", "cargo test")
        commands.setdefault("build", "cargo build")
    if Path("go.mod") in manifests:
        commands.setdefault("test", "go test ./...")
    return commands


def detect_tech_stack(manifests: list[Path], files: list[Path]) -> list[str]:
    stack: list[str] = []
    names = {path.name for path in manifests}
    if "package.json" in names:
        stack.append("Node.js / JavaScript")
    if "pyproject.toml" in names or "requirements.txt" in names:
        stack.append("Python")
    if "Cargo.toml" in names:
        stack.append("Rust")
    if "go.mod" in names:
        stack.append("Go")
    if "pom.xml" in names or "build.gradle" in names:
        stack.append("Java")
    if any("prisma" in path.parts for path in files):
        stack.append("Prisma")
    return stack or ["Unknown"]


def looks_like_schema(path: Path) -> bool:
    lower = str(path).lower()
    return any(token in lower for token in ("schema", "migration", "migrations", "prisma", "database", "db/"))


def looks_like_api(path: Path) -> bool:
    lower = str(path).lower()
    return any(token in lower for token in ("api", "route", "router", "controller", "handler", "endpoint"))


def looks_like_ci(path: Path) -> bool:
    lower = str(path).lower()
    return lower.startswith(".github/workflows") or lower in {".gitlab-ci.yml", "jenkinsfile"}


def looks_like_test(path: Path) -> bool:
    lower = str(path).lower()
    return "test" in lower or "spec" in lower


def infer_risk_areas(schemas: list[str], api_files: list[str], ci_files: list[str]) -> list[str]:
    risks = []
    if schemas:
        risks.append("Data/schema changes require contract synchronization.")
    if api_files:
        risks.append("API or route changes require contract synchronization.")
    if ci_files:
        risks.append("CI workflow changes can affect merge gates.")
    return risks or ["No high-risk areas inferred yet. Confirm with the project owner."]


def infer_open_questions(
    commands: dict[str, str],
    tech_stack: list[str],
    schemas: list[str],
    api_files: list[str],
) -> list[str]:
    questions = []
    if not commands:
        questions.append("Confirm the canonical local development, test, build, and lint commands.")
    if tech_stack == ["Unknown"]:
        questions.append("Confirm the project technology stack.")
    if not schemas:
        questions.append("Confirm whether the project has persistent data schemas or migrations.")
    if not api_files:
        questions.append("Confirm whether the project exposes APIs, routes, events, or integration contracts.")
    return questions


def infer_default_checks(root: Path) -> list[str]:
    commands = detect_commands(root, detect_manifests(list_project_files(root)))
    return [commands[key] for key in ("lint", "test", "build") if key in commands] or ["TODO: declare validation command"]


def analyze_change_impact(changed: list[str]) -> dict[str, bool]:
    return {
        "api": any(looks_like_api(Path(path)) for path in changed),
        "schema": any(looks_like_schema(Path(path)) for path in changed),
        "ci": any(looks_like_ci(Path(path)) for path in changed),
        "docs": any(path.startswith("docs/") or path == "AGENTS.md" for path in changed),
        "tests": any(looks_like_test(Path(path)) for path in changed),
        "commands": any(Path(path).name in {"package.json", "pyproject.toml", "Cargo.toml", "go.mod"} for path in changed),
    }


def required_updates_for_impact(impact: dict[str, bool]) -> list[str]:
    updates = []
    if impact.get("api") or impact.get("schema"):
        updates.append("docs/contracts.md")
    if impact.get("commands") or impact.get("ci"):
        updates.append("docs/workflows.md")
        updates.append("AGENTS.md")
    return updates


def git_changed_files(root: Path) -> list[str]:
    if not (root / ".git").exists():
        return []
    commands = [
        ["git", "diff", "--name-only"],
        ["git", "diff", "--name-only", "--cached"],
        ["git", "ls-files", "--others", "--exclude-standard"],
    ]
    changed: set[str] = set()
    for command in commands:
        try:
            completed = subprocess.run(command, cwd=root, check=False, text=True, capture_output=True)
        except OSError:
            continue
        if completed.returncode == 0:
            changed.update(line.strip() for line in completed.stdout.splitlines() if line.strip())
    return sorted(changed)


def changed_or_exists(root: Path, changed: list[str], target: str) -> bool:
    return target in changed or (root / target).exists()


def has_unresolved_questions(path: Path) -> bool:
    text = read_text(path)
    return "- [ ]" in text or "TODO" in text or "Confirm " in text or "确认" in text


def duplicated_headings(root: Path) -> list[str]:
    headings: dict[str, int] = {}
    for path in [root / "AGENTS.md", *(root / relative for relative in DOC_FILES.values())]:
        if not path.exists() or path.is_dir():
            continue
        for line in read_text(path).splitlines():
            if line.startswith("#"):
                headings[line.strip()] = headings.get(line.strip(), 0) + 1
    return sorted(heading for heading, count in headings.items() if count > 2)


def load_or_scan_state(root: Path) -> dict[str, Any]:
    state_path = root / ".acdl/project-state.json"
    if state_path.exists():
        try:
            return json.loads(state_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return asdict(scan_project(root))


def required_reads(root: Path) -> list[str]:
    candidates = [Path("AGENTS.md"), *DOC_FILES.values()]
    return [str(path) for path in candidates if (root / path).exists()]


def render_agents_md(scan: ProjectScan) -> str:
    commands = "\n".join(f"- `{name}`: `{command}`" for name, command in scan.commands.items()) or "- TODO: confirm project commands."
    risks = "\n".join(f"- {risk}" for risk in scan.risk_areas)
    return f"""# AGENTS.md

This file is the entry point for coding agents working in this repository.

## Project Overview

- Root: `{scan.root}`
- Tech stack: {", ".join(scan.tech_stack)}
- Generated by: `acdl retrofit`
- Generated at: {scan.generated_at}

## Commands

{commands}

## Agent Collaboration Rules

- Read this file and the relevant files under `docs/` before editing code.
- Create or refresh a task contract before implementation work.
- Keep changes inside the declared task scope.
- Record out-of-scope findings as follow-ups instead of changing unrelated code.
- Synchronize shared facts when API, schema, config, permission, workflow, or architecture contracts change.
- Run `acdl preflight` before handoff or review.

## Risk Areas

{risks}

## Core Docs

- `docs/architecture.md`
- `docs/contracts.md`
- `docs/workflows.md`
- `docs/active-work.md`
- `docs/open-questions.md`
"""


def render_doc(name: str, scan: ProjectScan) -> str:
    if name == "architecture":
        manifests = "\n".join(f"- `{path}`" for path in scan.manifests) or "- No manifest detected."
        api = "\n".join(f"- `{path}`" for path in scan.api_files[:30]) or "- No API files inferred."
        return f"""# Architecture

## Overview

- Tech stack: {", ".join(scan.tech_stack)}
- Generated at: {scan.generated_at}

## Manifests

{manifests}

## Inferred API / Routing Surfaces

{api}

## Agent Notes

- Treat this as a generated first pass.
- Update this file when module responsibilities, dependency direction, or data flow changes.
"""
    if name == "contracts":
        schemas = "\n".join(f"- `{path}`" for path in scan.schemas[:40]) or "- No schema files inferred."
        api = "\n".join(f"- `{path}`" for path in scan.api_files[:40]) or "- No API files inferred."
        return f"""# Contracts

## API / Integration Surfaces

{api}

## Data / Schema Surfaces

{schemas}

## Agent Notes

- Update this file when API, schema, config, permission, event, or data model contracts change.
- Do not invent missing contracts. Add uncertain items to `docs/open-questions.md`.
"""
    if name == "workflows":
        commands = "\n".join(f"- `{command}`" for command in scan.commands.values()) or "- TODO: confirm commands."
        ci = "\n".join(f"- `{path}`" for path in scan.ci_files) or "- No CI files inferred."
        return f"""# Workflows

## Commands

{commands}

## CI / Automation

{ci}

## Agent Notes

- Update this file when local development, testing, release, deployment, or CI workflows change.
"""
    if name == "active_work":
        risks = "\n".join(f"- {risk}" for risk in scan.risk_areas)
        return f"""# Active Work

## Current Coordination State

- Generated at: {scan.generated_at}
- Owner confirmation required for active tasks and occupied modules.

## Risk Areas

{risks}

## Agent Notes

- Update this file when parallel work, high-risk areas, or task ownership changes.
"""
    if name == "open_questions":
        questions = "\n".join(f"- [ ] {question}" for question in scan.open_questions) or "- [ ] Project owner to confirm there are no unresolved setup questions."
        return f"""# Open Questions

{questions}
"""
    if name == "decision":
        return f"""# 0001 Current Architecture Baseline

## Status

Proposed

## Context

`acdl retrofit` generated an initial architecture baseline at {scan.generated_at}.

## Decision

Use `AGENTS.md` and `docs/` as the repository-level shared state source for coding agents.

## Consequences

- Agents must read project facts before implementation.
- Contract-changing work must synchronize the relevant fact source.
- Uncertain generated facts must remain visible in `docs/open-questions.md`.
"""
    raise ValueError(f"Unknown doc name: {name}")


def render_retrofit_summary(scan: ProjectScan) -> str:
    return f"""# Retrofit Summary

- Generated at: {scan.generated_at}
- Tech stack: {", ".join(scan.tech_stack)}
- Manifest count: {len(scan.manifests)}
- API surface count: {len(scan.api_files)}
- Schema surface count: {len(scan.schemas)}
- Open question count: {len(scan.open_questions)}
"""


def render_context_md(context: dict[str, Any]) -> str:
    reads = "\n".join(f"- `{path}`" for path in context["required_reads"]) or "- No project fact sources found."
    changes = "\n".join(f"- `{path}`" for path in context["recent_changes"]) or "- No changed files detected."
    return f"""# ACDL Context

## Task

{context["task"]}

## Required Reads

{reads}

## Recent Changes

{changes}
"""


def render_task_contract_md(payload: dict[str, Any]) -> str:
    return f"""# Task Contract

## Task

{payload["task"]}

## Allowed Scope

{markdown_list(payload["allowed_scope"])}

## Forbidden Scope

{markdown_list(payload["forbidden_scope"])}

## Acceptance Criteria

{markdown_list(payload["acceptance_criteria"])}

## Required Checks

{markdown_list(payload["required_checks"])}

## Required Sync Targets

{markdown_list(payload["required_sync_targets"])}
"""


def render_change_impact_md(payload: dict[str, Any]) -> str:
    changed = markdown_list([f"`{path}`" for path in payload["changed_files"]]) or "- No changed files detected."
    impacts = markdown_list([f"{key}: {value}" for key, value in payload["impact"].items()])
    updates = markdown_list([f"`{target}`" for target in payload["required_updates"]]) or "- No required updates inferred."
    return f"""# Change Impact

## Changed Files

{changed}

## Impact Flags

{impacts}

## Required Updates

{updates}
"""


def render_preflight_md(report: dict[str, Any]) -> str:
    failures = markdown_list(report["failures"]) or "- None"
    warnings = markdown_list(report["warnings"]) or "- None"
    return f"""# Preflight Report

- Status: {report["status"]}
- Generated at: {report["generated_at"]}

## Failures

{failures}

## Warnings

{warnings}
"""


def render_handoff_md(root: Path, context: str, contract_text: str, impact_text: str) -> str:
    changed = markdown_list([f"`{path}`" for path in git_changed_files(root)]) or "- No changed files detected."
    return f"""# Handoff Pack

Generated at: {now()}

## Changed Files

{changed}

## Current Context

{context or "No context generated yet. Run `acdl bootstrap`."}

## Task Contract

{contract_text or "No task contract generated yet. Run `acdl contract`."}

## Change Impact

{impact_text or "No change impact generated yet. Run `acdl sync`."}

## Recommended Next Step

- Run `acdl preflight` before review or merge.
"""


def render_maintenance_md(payload: dict[str, Any]) -> str:
    findings = markdown_list(payload["findings"]) or "- None"
    return f"""# Maintenance Report

- Status: {payload["status"]}
- Generated at: {payload["generated_at"]}

## Findings

{findings}
"""


def ensure_root(root: Path) -> None:
    if not root.exists():
        raise FileNotFoundError(f"Project root does not exist: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"Project root is not a directory: {root}")


def write_if_needed(path: Path, content: str, force: bool) -> list[Path]:
    if path.exists() and not force:
        return []
    return write_markdown(path, content, force=True)


def write_markdown(path: Path, content: str, force: bool) -> list[Path]:
    if path.exists() and not force:
        return []
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.rstrip() + "\n", encoding="utf-8")
    return [path]


def write_json(path: Path, payload: Any, force: bool) -> list[Path]:
    if path.exists() and not force:
        return []
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return [path]


def read_text(path: Path) -> str:
    if not path.exists() or path.is_dir():
        return ""
    return path.read_text(encoding="utf-8")


def markdown_list(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def display_paths(root: Path, paths: list[Path]) -> list[str]:
    result = []
    for path in paths:
        try:
            result.append(str(path.relative_to(root)))
        except ValueError:
            result.append(str(path))
    return result


def now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()
