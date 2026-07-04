from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tfexplain.errors import AnalysisError
from tfexplain.plan import analyze_plan
from tfexplain.render import render_plan


class PlanAnalysisTest(unittest.TestCase):
    def test_analyzes_plan_actions_and_risk(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "plan.json"
            path.write_text(json.dumps(sample_plan()), encoding="utf-8")

            analysis = analyze_plan(path, show_fields=True)

        self.assertEqual(analysis.counts["create"], 1)
        self.assertEqual(analysis.counts["update"], 1)
        self.assertEqual(analysis.counts["replace"], 1)
        self.assertEqual(analysis.counts["delete"], 1)
        self.assertIn(analysis.risk_level, {"high", "critical"})

        db_change = next(change for change in analysis.changes if change.address == "aws_db_instance.main")
        self.assertEqual(db_change.action, "replace")
        self.assertIn("engine_version", db_change.replace_paths)
        self.assertIn("engine_version", db_change.changed_fields)

    def test_renders_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "plan.json"
            path.write_text(json.dumps(sample_plan()), encoding="utf-8")
            analysis = analyze_plan(path)

        rendered = render_plan(analysis, "markdown", "risk")
        self.assertIn("# Terraform Plan Summary", rendered)
        self.assertIn("aws_db_instance.main", rendered)
        self.assertIn("Risk Score", rendered)

    def test_converts_saved_tfplan_with_terraform_show_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tfplan"
            path.write_bytes(b"\x00tfplan-binary-placeholder")

            with patch("tfexplain.plan.subprocess.run") as run:
                run.return_value = SimpleNamespace(
                    returncode=0,
                    stdout=json.dumps(sample_plan()),
                    stderr="",
                )

                analysis = analyze_plan(path)

        run.assert_called_once()
        self.assertEqual(run.call_args.args[0], ["terraform", "show", "-json", path.as_posix()])
        self.assertEqual(analysis.counts["replace"], 1)

    def test_reports_missing_terraform_for_saved_tfplan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tfplan"
            path.write_bytes(b"\x00tfplan-binary-placeholder")

            with patch("tfexplain.plan.subprocess.run", side_effect=FileNotFoundError):
                with self.assertRaisesRegex(AnalysisError, "Terraform executable was not found"):
                    analyze_plan(path)

    def test_reads_plan_json_from_stdin_marker(self) -> None:
        analysis = analyze_plan("-", stdin_text=json.dumps(sample_plan()))

        self.assertEqual(analysis.path, "-")
        self.assertEqual(analysis.counts["replace"], 1)

    def test_reads_human_plan_text_from_stdin_marker(self) -> None:
        analysis = analyze_plan("-", stdin_text=sample_plan_text())

        self.assertEqual(analysis.path, "stdin")
        self.assertEqual(analysis.counts["create"], 1)
        self.assertEqual(analysis.counts["update"], 1)
        self.assertEqual(analysis.counts["replace"], 1)
        self.assertEqual(analysis.changes[0].provider, "terraform")

    def test_rejects_unknown_stdin_text(self) -> None:
        with self.assertRaisesRegex(AnalysisError, "must be Terraform JSON"):
            analyze_plan("-", stdin_text="not a terraform plan\n")


def sample_plan() -> dict:
    return {
        "format_version": "1.2",
        "terraform_version": "1.8.0",
        "resource_changes": [
            {
                "address": "aws_instance.web",
                "type": "aws_instance",
                "name": "web",
                "provider_name": "registry.terraform.io/hashicorp/aws",
                "change": {
                    "actions": ["create"],
                    "before": None,
                    "after": {"ami": "ami-123", "instance_type": "t3.micro"},
                },
            },
            {
                "address": "aws_security_group.web",
                "type": "aws_security_group",
                "name": "web",
                "provider_name": "registry.terraform.io/hashicorp/aws",
                "change": {
                    "actions": ["delete"],
                    "before": {"name": "web"},
                    "after": None,
                },
            },
            {
                "address": "aws_db_instance.main",
                "type": "aws_db_instance",
                "name": "main",
                "provider_name": "registry.terraform.io/hashicorp/aws",
                "change": {
                    "actions": ["delete", "create"],
                    "replace_paths": [["engine_version"]],
                    "before": {"engine_version": "14.1", "allocated_storage": 20},
                    "after": {"engine_version": "15.1", "allocated_storage": 20},
                },
            },
            {
                "address": "aws_s3_bucket.logs",
                "type": "aws_s3_bucket",
                "name": "logs",
                "provider_name": "registry.terraform.io/hashicorp/aws",
                "change": {
                    "actions": ["update"],
                    "before": {"tags": {"env": "dev"}},
                    "after": {"tags": {"env": "prod"}},
                },
            },
        ],
    }


def sample_plan_text() -> str:
    return """
Terraform will perform the following actions:

  # terraform_data.service_config will be created
  + resource "terraform_data" "service_config" {
      + id = (known after apply)
    }

  # terraform_data.review_context will be updated in-place
  ~ resource "terraform_data" "review_context" {
      id = "existing"
    }

  # terraform_data.release_gate must be replaced
-/+ resource "terraform_data" "release_gate" {
      id = "existing"
    }

Plan: 2 to add, 1 to change, 1 to destroy.
"""
