from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tfexplain.code import analyze_code


ROOT = Path(__file__).resolve().parents[1]
TFPLAN_SAMPLES = ROOT / "samples" / "tfplans"


class TfplanSamplesTest(unittest.TestCase):
    def test_tfplan_generator_files_are_present(self) -> None:
        generator = TFPLAN_SAMPLES / "generate.sh"
        readme = TFPLAN_SAMPLES / "README.md"

        self.assertTrue(generator.exists())
        self.assertTrue(readme.exists())

        script = generator.read_text(encoding="utf-8")
        self.assertIn("terraform -chdir=", script)
        self.assertIn("show -json", script)
        self.assertIn("tfexplain plan", script)
        self.assertIn("create.tfplan", script)
        self.assertIn("update-replace.tfplan", script)

    def test_tfplan_source_project_is_parseable(self) -> None:
        source_dir = TFPLAN_SAMPLES / "source" / "terraform-data"

        analysis = analyze_code(source_dir)

        self.assertEqual(len(analysis.terraform_files), 3)
        self.assertEqual(len(analysis.resources), 3)
        self.assertEqual(len(analysis.variables), 6)
        self.assertEqual(len(analysis.outputs), 3)

    def test_tfplan_var_files_are_present(self) -> None:
        vars_dir = TFPLAN_SAMPLES / "vars"

        self.assertTrue((vars_dir / "create.tfvars").exists())
        self.assertTrue((vars_dir / "base.tfvars").exists())
        self.assertTrue((vars_dir / "changed.tfvars").exists())

        changed = (vars_dir / "changed.tfvars").read_text(encoding="utf-8")
        self.assertIn("release_version", changed)
        self.assertIn("replicas", changed)
