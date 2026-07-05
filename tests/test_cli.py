from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tfexplain.cli import main


class CliTest(unittest.TestCase):
    def test_version_includes_author_company_and_website(self) -> None:
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            code = main(["version"])

        self.assertEqual(code, 0)
        rendered = stdout.getvalue()
        self.assertIn("tfexplain 0.1.3", rendered)
        self.assertIn("Open-source CLI for explaining Terraform code and plans.", rendered)
        self.assertIn("Package: bna-tools/tfexplain", rendered)
        self.assertIn("Author: Vijay Daswani", rendered)
        self.assertIn("Company: Build & Automate", rendered)
        self.assertIn("Website: buildnautomate.com", rendered)

    def test_global_version_includes_author_company_and_website(self) -> None:
        stdout = io.StringIO()
        with self.assertRaises(SystemExit) as raised:
            with contextlib.redirect_stdout(stdout):
                main(["--version"])

        self.assertEqual(raised.exception.code, 0)
        rendered = stdout.getvalue()
        self.assertIn("Open-source CLI for explaining Terraform code and plans.", rendered)
        self.assertIn("Package: bna-tools/tfexplain", rendered)
        self.assertIn("Author: Vijay Daswani", rendered)
        self.assertIn("Company: Build & Automate", rendered)
        self.assertIn("Website: buildnautomate.com", rendered)

    def test_plan_fail_on_returns_two_after_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "plan.json"
            path.write_text(
                json.dumps(
                    {
                        "resource_changes": [
                            {
                                "address": "aws_db_instance.main",
                                "type": "aws_db_instance",
                                "name": "main",
                                "change": {"actions": ["delete", "create"]},
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                code = main(["plan", str(path), "--fail-on", "replace"])

        self.assertEqual(code, 2)
        self.assertIn("aws_db_instance.main", stdout.getvalue())

    def test_code_command_outputs_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "main.tf").write_text('resource "random_id" "suffix" {}\n', encoding="utf-8")
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                code = main(["code", str(root), "--format", "json"])

        self.assertEqual(code, 0)
        payload = json.loads(stdout.getvalue())
        self.assertEqual(len(payload["resources"]), 1)

    def test_ai_flag_requires_provider_credentials(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "main.tf").write_text('resource "random_id" "suffix" {}\n', encoding="utf-8")
            stderr = io.StringIO()
            with patch.dict("os.environ", {}, clear=True), contextlib.redirect_stderr(stderr):
                code = main(["code", str(root), "--ai", "--provider", "openai"])

        self.assertEqual(code, 1)
        self.assertIn("OpenAI requires OPENAI_API_KEY", stderr.getvalue())

    def test_ai_flag_appends_openai_response(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "main.tf").write_text('resource "random_id" "suffix" {}\n', encoding="utf-8")
            stdout = io.StringIO()
            with patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}, clear=True):
                with patch("tfexplain.ai.urllib.request.urlopen", return_value=FakeResponse(openai_response())):
                    with contextlib.redirect_stdout(stdout):
                        code = main(["code", str(root), "--ai", "--provider", "openai"])

        self.assertEqual(code, 0)
        self.assertIn("AI-Assisted Explanation", stdout.getvalue())
        self.assertIn("mock AI explanation", stdout.getvalue())

    def test_plan_reads_json_from_stdin(self) -> None:
        plan = {
            "resource_changes": [
                {
                    "address": "aws_instance.web",
                    "type": "aws_instance",
                    "name": "web",
                    "provider_name": "registry.terraform.io/hashicorp/aws",
                    "change": {"actions": ["create"]},
                }
            ]
        }
        stdout = io.StringIO()
        with patch("sys.stdin", io.StringIO(json.dumps(plan))), contextlib.redirect_stdout(stdout):
            code = main(["plan", "-"])

        self.assertEqual(code, 0)
        self.assertIn("aws_instance.web", stdout.getvalue())

    def test_plan_reads_human_plan_text_from_stdin(self) -> None:
        stdout = io.StringIO()
        with patch("sys.stdin", io.StringIO(sample_plan_text())), contextlib.redirect_stdout(stdout):
            code = main(["plan", "-"])

        self.assertEqual(code, 0)
        self.assertIn("terraform_data.service_config", stdout.getvalue())
        self.assertIn("Parsed from human-readable Terraform plan text", stdout.getvalue())

    def test_no_args_reads_human_plan_text_from_stdin(self) -> None:
        stdout = io.StringIO()
        with patch("sys.stdin", io.StringIO(sample_plan_text())), contextlib.redirect_stdout(stdout):
            code = main([])

        self.assertEqual(code, 0)
        self.assertIn("Terraform Plan Summary", stdout.getvalue())
        self.assertIn("terraform_data.release_gate", stdout.getvalue())


def sample_plan_text() -> str:
    return """
Terraform will perform the following actions:

  # terraform_data.service_config will be created
  + resource "terraform_data" "service_config" {
      + id = (known after apply)
    }

  # terraform_data.release_gate must be replaced
-/+ resource "terraform_data" "release_gate" {
      id = "existing"
    }

Plan: 2 to add, 0 to change, 1 to destroy.
"""


def openai_response() -> dict[str, object]:
    return {
        "choices": [
            {
                "message": {
                    "content": "mock AI explanation",
                }
            }
        ]
    }


class FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")
