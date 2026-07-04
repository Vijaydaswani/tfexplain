from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tfexplain.code import analyze_code
from tfexplain.plan import analyze_plan
from tfexplain.render import render_code, render_combined, render_plan


ROOT = Path(__file__).resolve().parents[1]
CODE_SAMPLES = ROOT / "samples" / "terraform-code"
PLAN_SAMPLES = ROOT / "samples" / "plans"


class SamplesTest(unittest.TestCase):
    def test_all_code_samples_are_parseable(self) -> None:
        sample_dirs = sorted(path for path in CODE_SAMPLES.iterdir() if path.is_dir())

        self.assertGreaterEqual(len(sample_dirs), 6)

        providers: set[str] = set()
        for sample_dir in sample_dirs:
            with self.subTest(sample=sample_dir.name):
                analysis = analyze_code(sample_dir)
                rendered_text = render_code(analysis)
                rendered_json = json.loads(render_code(analysis, "json"))

                self.assertGreater(len(analysis.terraform_files), 0)
                self.assertGreater(len(analysis.providers), 0)
                self.assertIn("Terraform Code Summary", rendered_text)
                self.assertEqual(rendered_json["path"], sample_dir.as_posix())
                providers.update(analysis.providers)

        self.assertTrue({"aws", "azurerm", "google", "kubernetes", "helm", "cloudflare"}.issubset(providers))

    def test_all_plan_samples_are_parseable(self) -> None:
        plan_files = sorted(PLAN_SAMPLES.glob("*.json"))

        self.assertGreaterEqual(len(plan_files), 10)
        self.assertLessEqual(len(plan_files), 15)

        action_counts: dict[str, int] = {}
        providers: set[str] = set()
        replacements = 0
        deletes = 0

        for plan_file in plan_files:
            with self.subTest(sample=plan_file.name):
                analysis = analyze_plan(plan_file, show_fields=True)
                rendered_text = render_plan(analysis)
                rendered_markdown = render_plan(analysis, "markdown", "provider")
                rendered_json = json.loads(render_plan(analysis, "json"))

                self.assertGreater(len(analysis.changes), 0)
                self.assertIn("Terraform Plan Summary", rendered_text)
                self.assertIn("Terraform Plan Summary", rendered_markdown)
                self.assertEqual(rendered_json["path"], plan_file.as_posix())

                for action, count in analysis.counts.items():
                    action_counts[action] = action_counts.get(action, 0) + count
                providers.update(change.provider for change in analysis.changes)
                replacements += analysis.counts.get("replace", 0)
                deletes += analysis.counts.get("delete", 0)

        self.assertGreater(action_counts.get("create", 0), 0)
        self.assertGreater(action_counts.get("update", 0), 0)
        self.assertGreater(deletes, 0)
        self.assertGreater(replacements, 0)
        self.assertTrue({"aws", "azurerm", "google", "kubernetes", "helm", "cloudflare"}.issubset(providers))

    def test_combined_output_with_samples(self) -> None:
        code_analysis = analyze_code(CODE_SAMPLES / "azurerm-aks")
        plan_analysis = analyze_plan(PLAN_SAMPLES / "03-azurerm-aks-update.json", show_fields=True)

        rendered = render_combined(code_analysis, plan_analysis, "markdown", "risk")

        self.assertIn("# Terraform Explanation", rendered)
        self.assertIn("azurerm_kubernetes_cluster.main", rendered)
        self.assertIn("Module Quality", rendered)
