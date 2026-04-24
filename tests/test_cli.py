from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from acdl.cli import main


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
                        "python3 -m unittest discover -s tests",
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


if __name__ == "__main__":
    unittest.main()
