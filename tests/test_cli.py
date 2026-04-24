from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from acdl.cli import main


def run_git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, text=True, capture_output=True)


class ACDLCliTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
