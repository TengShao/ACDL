from __future__ import annotations

import json
import os
import subprocess
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
AGENT_WORKFLOW_DOC = Path("docs/acdl-agent-workflow.md")
ACDL_BLOCK_BEGIN = "<!-- ACDL:BEGIN -->"
ACDL_BLOCK_END = "<!-- ACDL:END -->"
SUPPORTED_AGENTS = ("codex", "claude", "opencode")

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


def setup(root: Path, agents: str = "", yes: bool = False) -> CommandResult:
    ensure_root(root)
    selected, error = parse_agents(agents)
    if error:
        return CommandResult(error, [], exit_code=1)
    targets = setup_targets(selected)
    if not yes and not confirm_setup(selected, targets):
        return CommandResult("Setup cancelled.", [], exit_code=1)

    failures = validate_managed_targets(root, targets)
    if failures:
        return CommandResult("Setup failed: " + "; ".join(failures), [], exit_code=1)

    written: list[Path] = []
    written.extend(write_markdown(root / AGENT_WORKFLOW_DOC, render_agent_workflow_doc(), force=True))
    for relative, content in targets.items():
        written.extend(write_managed_block(root / relative, content))

    return CommandResult(
        f"Agent setup complete for: {', '.join(selected)}.",
        display_paths(root, written),
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


def preflight(root: Path, strict: bool = False) -> CommandResult:
    ensure_root(root)
    failures: list[str] = []
    warnings: list[str] = []
    check_results: list[dict[str, Any]] = []
    task_contract: dict[str, Any] = {}

    required = [Path("AGENTS.md"), *DOC_FILES.values()]
    for relative in required:
        if not (root / relative).exists():
            failures.append(f"Missing required fact source: {relative}")

    task_contract_path = root / ".acdl/task-contract.json"
    if not task_contract_path.exists():
        add_preflight_issue(
            "Missing .acdl/task-contract.json. Run `acdl contract` before task work.",
            failures,
            warnings,
            strict,
        )
    else:
        task_contract = load_task_contract(task_contract_path, failures)
        check_results = run_required_checks(
            root,
            task_contract.get("required_checks", []),
            failures,
            warnings,
            strict=strict,
        )

    changed = git_changed_files(root)
    impact = analyze_change_impact(changed)
    required_updates = required_updates_for_impact(impact)
    for target in required_updates:
        if target not in changed:
            add_preflight_issue(
                f"Potential fact-source drift: {target} must be updated in this change.",
                failures,
                warnings,
                strict,
            )

    if task_contract:
        validate_task_scope(task_contract, changed, required_updates, failures, warnings, strict)

    open_questions = root / "docs/open-questions.md"
    if open_questions.exists() and has_unresolved_questions(open_questions):
        warnings.append("docs/open-questions.md contains unresolved questions.")

    report = {
        "generated_at": now(),
        "status": "failed" if failures else "passed",
        "failures": failures,
        "warnings": warnings,
        "check_results": check_results,
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


def parse_agents(raw: str) -> tuple[list[str], str | None]:
    if not raw.strip():
        return list(SUPPORTED_AGENTS), None
    selected: list[str] = []
    for item in raw.split(","):
        agent = item.strip().lower()
        if not agent:
            continue
        if agent not in SUPPORTED_AGENTS:
            return [], f"Unknown agent: {agent}. Supported agents: {', '.join(SUPPORTED_AGENTS)}."
        if agent not in selected:
            selected.append(agent)
    if not selected:
        return [], "No agents selected."
    return selected, None


def confirm_setup(selected: list[str], targets: dict[Path, str]) -> bool:
    print("ACDL will configure these agents: " + ", ".join(selected))
    print("Files may be created or updated with an ACDL managed block:")
    print(f"- {AGENT_WORKFLOW_DOC}")
    for path in targets:
        print(f"- {path}")
    answer = input("Continue? [Y/n] ").strip().lower()
    return answer in {"", "y", "yes"}


def setup_targets(selected: list[str]) -> dict[Path, str]:
    targets: dict[Path, str] = {}
    if "codex" in selected or "opencode" in selected:
        targets[Path("AGENTS.md")] = render_agents_bridge_block(selected)
    if "claude" in selected:
        targets[Path("CLAUDE.md")] = render_claude_bridge_block()
    return targets


def validate_managed_targets(root: Path, targets: dict[Path, str]) -> list[str]:
    failures: list[str] = []
    for relative in targets:
        text = read_text(root / relative)
        if has_incomplete_managed_block(text):
            failures.append(f"Incomplete ACDL managed block in {relative}")
    return failures


def has_incomplete_managed_block(text: str) -> bool:
    return text.count(ACDL_BLOCK_BEGIN) != text.count(ACDL_BLOCK_END)


def write_managed_block(path: Path, block_content: str) -> list[Path]:
    existing = read_text(path)
    replacement = render_managed_block(block_content)
    if not existing:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(replacement, encoding="utf-8")
        return [path]

    start = existing.find(ACDL_BLOCK_BEGIN)
    end = existing.find(ACDL_BLOCK_END)
    if start == -1 and end == -1:
        separator = "" if existing.endswith("\n") else "\n"
        updated = existing + separator + "\n" + replacement
    else:
        end_after = end + len(ACDL_BLOCK_END)
        updated = existing[:start] + replacement.rstrip("\n") + existing[end_after:]

    if updated == existing:
        return []
    path.write_text(updated, encoding="utf-8")
    return [path]


def render_managed_block(content: str) -> str:
    return f"{ACDL_BLOCK_BEGIN}\n{content.rstrip()}\n{ACDL_BLOCK_END}\n"


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


def add_preflight_issue(
    message: str,
    failures: list[str],
    warnings: list[str],
    strict: bool,
) -> None:
    if strict:
        failures.append(message)
    else:
        warnings.append(message)


def validate_task_scope(
    task_contract: dict[str, Any],
    changed: list[str],
    required_updates: list[str],
    failures: list[str],
    warnings: list[str],
    strict: bool,
) -> None:
    allowed_scope = normalize_scope_list(task_contract.get("allowed_scope"))
    forbidden_scope = normalize_scope_list(task_contract.get("forbidden_scope"))

    if not allowed_scope or any(is_todo_scope(scope) for scope in allowed_scope):
        add_preflight_issue(
            "Task contract allowed_scope is not declared.",
            failures,
            warnings,
            strict,
        )
        return

    for path in changed:
        if is_scope_exempt(path, required_updates):
            continue
        if not any(path_matches_scope(path, scope) for scope in allowed_scope):
            add_preflight_issue(
                f"Changed file outside allowed scope: {path}",
                failures,
                warnings,
                strict,
            )

    for path in changed:
        for scope in forbidden_scope:
            if is_todo_scope(scope) or is_default_forbidden_scope(scope):
                continue
            if path_matches_scope(path, scope):
                add_preflight_issue(
                    f"Changed file matches forbidden scope: {path} ({scope})",
                    failures,
                    warnings,
                    strict,
                )


def normalize_scope_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def is_todo_scope(value: str) -> bool:
    return value.upper().startswith("TODO")


def is_default_forbidden_scope(value: str) -> bool:
    return value == "Unrelated files outside the task"


def is_scope_exempt(path: str, required_updates: list[str]) -> bool:
    return path.startswith(".acdl/") or path in required_updates


def path_matches_scope(path: str, scope: str) -> bool:
    normalized_scope = scope.strip().lstrip("./")
    normalized_path = path.strip().lstrip("./")
    if normalized_scope in {".", "*"}:
        return True
    if normalized_scope.endswith("/"):
        return normalized_path.startswith(normalized_scope)
    return normalized_path == normalized_scope or normalized_path.startswith(normalized_scope.rstrip("/") + "/")


def load_task_contract(path: Path, failures: list[str]) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        failures.append(f"Invalid task contract JSON: {path} ({exc})")
        return {}
    except OSError as exc:
        failures.append(f"Cannot read task contract: {path} ({exc})")
        return {}
    if not isinstance(payload, dict):
        failures.append(f"Invalid task contract shape: {path} must contain a JSON object.")
        return {}
    return payload


def run_required_checks(
    root: Path,
    checks: Any,
    failures: list[str],
    warnings: list[str],
    strict: bool = False,
) -> list[dict[str, Any]]:
    if not isinstance(checks, list):
        failures.append("Invalid task contract: required_checks must be a list.")
        return []

    results: list[dict[str, Any]] = []
    for raw_command in checks:
        command = str(raw_command).strip()
        if not command:
            warnings.append("Skipping empty required check.")
            continue
        if command.startswith("TODO"):
            add_preflight_issue(f"Required check is not declared: {command}", failures, warnings, strict)
            results.append({"command": command, "status": "skipped", "reason": "TODO placeholder"})
            continue

        try:
            completed = subprocess.run(
                command,
                cwd=root,
                shell=True,
                check=False,
                text=True,
                capture_output=True,
                timeout=600,
            )
        except subprocess.TimeoutExpired as exc:
            failures.append(f"Required check timed out after 600s: {command}")
            results.append(
                {
                    "command": command,
                    "status": "timeout",
                    "returncode": None,
                    "stdout": trim_output(exc.stdout),
                    "stderr": trim_output(exc.stderr),
                }
            )
            continue
        except OSError as exc:
            failures.append(f"Required check could not start: {command} ({exc})")
            results.append({"command": command, "status": "error", "error": str(exc)})
            continue

        status = "passed" if completed.returncode == 0 else "failed"
        if completed.returncode != 0:
            failures.append(f"Required check failed ({completed.returncode}): {command}")
        results.append(
            {
                "command": command,
                "status": status,
                "returncode": completed.returncode,
                "stdout": trim_output(completed.stdout),
                "stderr": trim_output(completed.stderr),
            }
        )
    return results


def trim_output(value: str | bytes | None, limit: int = 4000) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace")
    return value if len(value) <= limit else value[:limit] + "\n... [truncated]"


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


def render_agent_workflow_doc() -> str:
    return """# ACDL Agent Workflow

This file is the shared workflow for coding agents in this repository.

## Required Lifecycle

1. Read `AGENTS.md` and the relevant files under `docs/` before editing code.
2. Run `acdl bootstrap` before task work when task context is missing or stale.
3. Run `acdl contract` before implementation and keep changes inside the declared scope.
4. Run `acdl sync` after edits to analyze fact-source impact.
5. Run `acdl preflight` before review or handoff.
6. Run `acdl handoff` before ending the task when another person or agent may continue.

## Failure Rule

If an ACDL command fails, stop and report the failure instead of continuing silently.
"""


def render_agents_bridge_block(selected: list[str]) -> str:
    names = ", ".join(agent for agent in selected if agent in {"codex", "opencode"})
    return f"""## ACDL Agent Workflow

This repository uses ACDL for agent collaboration. Agents configured through this file: {names}.

Read and follow `docs/acdl-agent-workflow.md` before editing code. Keep task work inside `.acdl/task-contract.json`, run `acdl sync` after edits, and run `acdl preflight` before handoff or review.
"""


def render_claude_bridge_block() -> str:
    return """@AGENTS.md

## ACDL Agent Workflow

Follow the shared ACDL workflow in `docs/acdl-agent-workflow.md`. Treat `AGENTS.md` as the cross-agent source of truth for repository instructions.
"""


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
    checks = markdown_list(
        [
            f"`{item['command']}`: {item['status']}"
            for item in report.get("check_results", [])
        ]
    ) or "- None"
    return f"""# Preflight Report

- Status: {report["status"]}
- Generated at: {report["generated_at"]}

## Required Checks

{checks}

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
