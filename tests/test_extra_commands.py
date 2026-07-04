from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tfexplain.cli import main


ROOT = Path(__file__).resolve().parents[1]
CODE_SAMPLE = ROOT / "samples" / "terraform-code" / "local-pipe-plan"
PLAN_SAMPLE = ROOT / "samples" / "plans" / "12-mixed-multicloud-module.json"


class ExtraCommandsTest(unittest.TestCase):
    def test_review_command_with_code_and_plan(self) -> None:
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = main(["review", "--code", str(CODE_SAMPLE), "--plan", str(PLAN_SAMPLE), "--format", "markdown"])

        self.assertEqual(code, 0)
        rendered = stdout.getvalue()
        self.assertIn("Terraform Review Summary", rendered)
        self.assertIn("Review Focus", rendered)
        self.assertIn("module.edge.cloudflare_record.api", rendered)

    def test_review_command_outputs_github_format(self) -> None:
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = main(["review", "--code", str(CODE_SAMPLE), "--plan", str(PLAN_SAMPLE), "--format", "github"])

        self.assertEqual(code, 0)
        rendered = stdout.getvalue()
        self.assertIn("## tfexplain Review", rendered)
        self.assertIn("| Risk | Create | Update | Replace | Delete |", rendered)
        self.assertIn("<details>", rendered)
        self.assertIn("bna-tools/tfexplain", rendered)

    def test_review_requires_code_or_plan(self) -> None:
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code = main(["review"])

        self.assertEqual(code, 1)
        self.assertIn("review requires --code, --plan, or both", stderr.getvalue())

    def test_docs_command_outputs_markdown(self) -> None:
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = main(["docs", str(CODE_SAMPLE)])

        self.assertEqual(code, 0)
        rendered = stdout.getvalue()
        self.assertIn("Terraform Module Documentation", rendered)
        self.assertIn("terraform_data", rendered)
        self.assertIn("Inputs", rendered)

    def test_graph_command_outputs_mermaid(self) -> None:
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = main(["graph", str(CODE_SAMPLE), "--format", "mermaid"])

        self.assertEqual(code, 0)
        rendered = stdout.getvalue()
        self.assertIn("flowchart TD", rendered)
        self.assertIn("terraform_data.service_config", rendered)

    def test_graph_command_outputs_ascii(self) -> None:
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = main(["graph", str(CODE_SAMPLE), "--format", "ascii"])

        self.assertEqual(code, 0)
        rendered = stdout.getvalue()
        self.assertIn("provider.terraform", rendered)
        self.assertIn("|-- manages -> terraform_data.generated_name", rendered)
        self.assertIn("`-- manages -> terraform_data.service_config", rendered)

    def test_graph_command_outputs_json(self) -> None:
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = main(["graph", str(CODE_SAMPLE), "--format", "json"])

        self.assertEqual(code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(payload["path"], CODE_SAMPLE.as_posix())
        self.assertGreaterEqual(len(payload["resources"]), 1)

    def test_init_command_creates_config_and_respects_force(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                code = main(["init", tmp])

            self.assertEqual(code, 0)
            config_path = Path(tmp) / ".tfexplain.json"
            self.assertTrue(config_path.exists())

            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                second_code = main(["init", tmp])

            self.assertEqual(second_code, 1)
            self.assertIn("Config already exists", stderr.getvalue())

            with contextlib.redirect_stdout(io.StringIO()):
                forced_code = main(["init", tmp, "--force"])

            self.assertEqual(forced_code, 0)
