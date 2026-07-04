from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tfexplain.code import analyze_code
from tfexplain.render import render_code


class CodeAnalysisTest(unittest.TestCase):
    def test_analyzes_terraform_code_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "main.tf").write_text(
                '''
terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = {
      source = "hashicorp/aws"
    }
  }
  backend "s3" {}
}

provider "aws" {
  region = var.region
}

module "network" {
  source = "./modules/network"
}

resource "aws_security_group" "web" {
  name = "web"
}

data "aws_caller_identity" "current" {}
''',
                encoding="utf-8",
            )
            (root / "variables.tf").write_text(
                '''
variable "region" {
  type = string
  description = "AWS region."
  validation {
    condition = length(var.region) > 0
    error_message = "region is required."
  }
}

variable "environment" {
  type = string
}
''',
                encoding="utf-8",
            )
            (root / "outputs.tf").write_text(
                '''
output "caller" {
  value = data.aws_caller_identity.current.account_id
}
''',
                encoding="utf-8",
            )

            analysis = analyze_code(root)

        self.assertIn("aws", analysis.providers)
        self.assertEqual(analysis.required_version, ">= 1.6.0")
        self.assertEqual(analysis.backends, ["s3"])
        self.assertEqual(len(analysis.modules), 1)
        self.assertEqual(len(analysis.resources), 1)
        self.assertEqual(len(analysis.data_sources), 1)
        self.assertEqual(len(analysis.variables), 2)
        self.assertTrue(any(finding.target == "var.environment" for finding in analysis.findings))
        self.assertTrue(any(finding.target == "aws_security_group.web" for finding in analysis.findings))

    def test_renders_text(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "main.tf").write_text('resource "random_id" "suffix" {}\n', encoding="utf-8")
            analysis = analyze_code(root)

        rendered = render_code(analysis)
        self.assertIn("Terraform Code Summary", rendered)
        self.assertIn("random_id", rendered)
        self.assertIn("Module Quality", rendered)
