from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from acdl.cli import main


def run_git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, text=True, capture_output=True)


class ACDLCliTests(unittest.TestCase):
    def test_setup_installs_selected_agent_instructions_non_destructively(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "AGENTS.md").write_text("# Team Rules\n\nKeep this.\n", encoding="utf-8")
            (root / "CLAUDE.md").write_text("# Claude Rules\n\nKeep this too.\n", encoding="utf-8")

            self.assertEqual(
                main(
                    [
                        "setup",
                        "--root",
                        str(root),
                        "--agents",
                        "codex,claude,opencode",
                        "--yes",
                    ]
                ),
                0,
            )

            agents = (root / "AGENTS.md").read_text(encoding="utf-8")
            claude = (root / "CLAUDE.md").read_text(encoding="utf-8")
            workflow = (root / "docs/acdl-agent-workflow.md").read_text(encoding="utf-8")
            self.assertIn("Keep this.", agents)
            self.assertIn("Keep this too.", claude)
            self.assertIn("<!-- ACDL:BEGIN -->", agents)
            self.assertIn("<!-- ACDL:END -->", agents)
            self.assertIn("@AGENTS.md", claude)
            self.assertIn("acdl preflight", workflow)

    def test_setup_is_idempotent_for_managed_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            self.assertEqual(main(["setup", "--root", str(root), "--agents", "codex,claude", "--yes"]), 0)
            self.assertEqual(main(["setup", "--root", str(root), "--agents", "codex,claude", "--yes"]), 0)

            agents = (root / "AGENTS.md").read_text(encoding="utf-8")
            claude = (root / "CLAUDE.md").read_text(encoding="utf-8")
            self.assertEqual(agents.count("<!-- ACDL:BEGIN -->"), 1)
            self.assertEqual(agents.count("<!-- ACDL:END -->"), 1)
            self.assertEqual(claude.count("<!-- ACDL:BEGIN -->"), 1)
            self.assertEqual(claude.count("<!-- ACDL:END -->"), 1)

    def test_setup_fails_without_modifying_incomplete_managed_block(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            agents_path = root / "AGENTS.md"
            original = "# Team Rules\n\n<!-- ACDL:BEGIN -->\nold content\n"
            agents_path.write_text(original, encoding="utf-8")

            self.assertEqual(main(["setup", "--root", str(root), "--agents", "codex", "--yes"]), 1)
            self.assertEqual(agents_path.read_text(encoding="utf-8"), original)

    def test_setup_fails_for_unknown_agent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            self.assertEqual(main(["setup", "--root", str(root), "--agents", "codex,unknown", "--yes"]), 1)
            self.assertFalse((root / "AGENTS.md").exists())

    def test_setup_without_root_discovers_project_root_from_nested_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            nested = root / "packages/app/src"
            nested.mkdir(parents=True)
            run_git(root, "init")

            with patch("pathlib.Path.cwd", return_value=nested):
                self.assertEqual(main(["setup", "--agents", "codex", "--yes"]), 0)

            self.assertTrue((root / "AGENTS.md").exists())
            self.assertTrue((root / "docs/acdl-agent-workflow.md").exists())
            self.assertFalse((nested / "AGENTS.md").exists())

    def test_lifecycle_commands_generate_expected_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")
            (root / "README.md").write_text("# Demo\n", encoding="utf-8")

            self.assertEqual(main(["retrofit", "--root", str(root)]), 0)
            self.assertTrue((root / "AGENTS.md").exists())
            self.assertTrue((root / "docs/architecture.md").exists())
            self.assertTrue((root / ".acdl/project-state.json").exists())

            self.assertEqual(main(["bootstrap", "--root", str(root), "--task", "Add feature"]), 0)
            self.assertTrue((root / ".acdl/context.md").exists())

            self.assertEqual(
                main(
                    [
                        "contract",
                        "--root",
                        str(root),
                        "--task",
                        "Add feature",
                        "--scope",
                        "src/",
                        "--check",
                        "python3 -c 'print(123)'",
                    ]
                ),
                0,
            )
            contract = json.loads((root / ".acdl/task-contract.json").read_text(encoding="utf-8"))
            self.assertEqual(contract["task"], "Add feature")
            self.assertEqual(contract["allowed_scope"], ["src/"])

            self.assertEqual(main(["sync", "--root", str(root)]), 0)
            self.assertTrue((root / ".acdl/change-impact.md").exists())

            self.assertEqual(main(["preflight", "--root", str(root)]), 0)
            self.assertTrue((root / ".acdl/preflight-report.md").exists())

            self.assertEqual(main(["handoff", "--root", str(root)]), 0)
            self.assertTrue((root / ".acdl/handoff-pack.md").exists())

            self.assertEqual(main(["maintain", "--root", str(root)]), 0)
            self.assertTrue((root / ".acdl/maintenance-report.md").exists())

    def test_preflight_fails_when_required_check_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "pyproject.toml").write_text("[project]\nname = 'demo'\n", encoding="utf-8")
            (root / "README.md").write_text("# Demo\n", encoding="utf-8")

            self.assertEqual(main(["retrofit", "--root", str(root)]), 0)
            self.assertEqual(
                main(
                    [
                        "contract",
                        "--root",
                        str(root),
                        "--task",
                        "Failing check",
                        "--check",
                        "python3 -c 'import sys; sys.exit(7)'",
                    ]
                ),
                0,
            )

            self.assertEqual(main(["preflight", "--root", str(root)]), 1)
            report = json.loads((root / ".acdl/preflight-report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["check_results"][0]["status"], "failed")
            self.assertTrue(any("Required check failed (7)" in item for item in report["failures"]))

    def test_preflight_warns_when_contract_source_not_changed_with_api_change(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_git(root, "init")
            run_git(root, "config", "user.name", "Test User")
            run_git(root, "config", "user.email", "test@example.com")

            (root / ".gitignore").write_text(".acdl/\n", encoding="utf-8")
            (root / "README.md").write_text("# Demo\n", encoding="utf-8")
            self.assertEqual(main(["retrofit", "--root", str(root)]), 0)
            run_git(root, "add", ".")
            run_git(root, "commit", "-m", "baseline")

            (root / "src").mkdir()
            (root / "src/api.py").write_text("def route():\n    return 'ok'\n", encoding="utf-8")
            self.assertEqual(
                main(
                    [
                        "contract",
                        "--root",
                        str(root),
                        "--task",
                        "Change API",
                        "--check",
                        "python3 -c 'print(123)'",
                    ]
                ),
                0,
            )

            self.assertEqual(main(["preflight", "--root", str(root)]), 0)
            report = json.loads((root / ".acdl/preflight-report.json").read_text(encoding="utf-8"))
            self.assertTrue(
                any("docs/contracts.md must be updated" in item for item in report["warnings"]),
                report["warnings"],
            )

    def test_preflight_warns_by_default_for_out_of_scope_change(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_git(root, "init")
            run_git(root, "config", "user.name", "Test User")
            run_git(root, "config", "user.email", "test@example.com")

            (root / ".gitignore").write_text(".acdl/\n", encoding="utf-8")
            (root / "README.md").write_text("# Demo\n", encoding="utf-8")
            self.assertEqual(main(["retrofit", "--root", str(root)]), 0)
            run_git(root, "add", ".")
            run_git(root, "commit", "-m", "baseline")

            (root / "other.py").write_text("print('outside')\n", encoding="utf-8")
            self.assertEqual(
                main(
                    [
                        "contract",
                        "--root",
                        str(root),
                        "--task",
                        "Change src",
                        "--scope",
                        "src/",
                        "--check",
                        "python3 -c 'print(123)'",
                    ]
                ),
                0,
            )

            self.assertEqual(main(["preflight", "--root", str(root)]), 0)
            report = json.loads((root / ".acdl/preflight-report.json").read_text(encoding="utf-8"))
            self.assertTrue(any("outside allowed scope" in item for item in report["warnings"]), report["warnings"])

    def test_preflight_strict_fails_for_out_of_scope_change(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_git(root, "init")
            run_git(root, "config", "user.name", "Test User")
            run_git(root, "config", "user.email", "test@example.com")

            (root / ".gitignore").write_text(".acdl/\n", encoding="utf-8")
            (root / "README.md").write_text("# Demo\n", encoding="utf-8")
            self.assertEqual(main(["retrofit", "--root", str(root)]), 0)
            run_git(root, "add", ".")
            run_git(root, "commit", "-m", "baseline")

            (root / "other.py").write_text("print('outside')\n", encoding="utf-8")
            self.assertEqual(
                main(
                    [
                        "contract",
                        "--root",
                        str(root),
                        "--task",
                        "Change src",
                        "--scope",
                        "src/",
                        "--check",
                        "python3 -c 'print(123)'",
                    ]
                ),
                0,
            )

            self.assertEqual(main(["preflight", "--root", str(root), "--strict"]), 1)
            report = json.loads((root / ".acdl/preflight-report.json").read_text(encoding="utf-8"))
            self.assertTrue(any("outside allowed scope" in item for item in report["failures"]), report["failures"])

    def test_preflight_strict_fails_for_forbidden_scope_change(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_git(root, "init")
            run_git(root, "config", "user.name", "Test User")
            run_git(root, "config", "user.email", "test@example.com")

            (root / ".gitignore").write_text(".acdl/\n", encoding="utf-8")
            (root / "README.md").write_text("# Demo\n", encoding="utf-8")
            self.assertEqual(main(["retrofit", "--root", str(root)]), 0)
            run_git(root, "add", ".")
            run_git(root, "commit", "-m", "baseline")

            (root / "src").mkdir()
            (root / "src/secret.py").write_text("TOKEN = 'x'\n", encoding="utf-8")
            self.assertEqual(
                main(
                    [
                        "contract",
                        "--root",
                        str(root),
                        "--task",
                        "Change src",
                        "--scope",
                        "src/",
                        "--forbid",
                        "src/secret.py",
                        "--check",
                        "python3 -c 'print(123)'",
                    ]
                ),
                0,
            )

            self.assertEqual(main(["preflight", "--root", str(root), "--strict"]), 1)
            report = json.loads((root / ".acdl/preflight-report.json").read_text(encoding="utf-8"))
            self.assertTrue(any("forbidden scope" in item for item in report["failures"]), report["failures"])

    def test_preflight_strict_fails_for_todo_required_check(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text("# Demo\n", encoding="utf-8")

            self.assertEqual(main(["retrofit", "--root", str(root)]), 0)
            self.assertEqual(main(["contract", "--root", str(root), "--task", "No checks", "--scope", "src/"]), 0)

            self.assertEqual(main(["preflight", "--root", str(root), "--strict"]), 1)
            report = json.loads((root / ".acdl/preflight-report.json").read_text(encoding="utf-8"))
            self.assertTrue(any("Required check is not declared" in item for item in report["failures"]))


if __name__ == "__main__":
    unittest.main()
