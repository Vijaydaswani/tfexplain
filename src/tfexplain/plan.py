from __future__ import annotations

import json
import re
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

from .errors import AnalysisError
from .models import PlanAnalysis, ResourceChange
from .risk import highest_risk, normalize_action, risk_level_from_score, score_resource_change


def analyze_plan(path: str | Path, show_fields: bool = False, stdin_text: str | None = None) -> PlanAnalysis:
    plan_path = Path(path)
    if plan_path.as_posix() == "-" and stdin_text is not None and not stdin_text.lstrip().startswith("{"):
        return parse_terraform_plan_text(stdin_text, "stdin")

    raw = load_plan_json(plan_path, stdin_text=stdin_text)
    if isinstance(raw, PlanAnalysis):
        return raw

    resource_changes = raw.get("resource_changes")
    if not isinstance(resource_changes, list):
        raise AnalysisError("Terraform plan JSON must contain a resource_changes array.")

    changes: list[ResourceChange] = []
    counts: Counter[str] = Counter()

    for item in resource_changes:
        if not isinstance(item, dict):
            continue

        change_data = item.get("change") or {}
        if not isinstance(change_data, dict):
            change_data = {}

        action = normalize_action(change_data.get("actions"))
        counts[action] += 1

        address = str(item.get("address") or "")
        resource_type = str(item.get("type") or infer_resource_type(address))
        score, reasons = score_resource_change(action, resource_type, address)
        replace_paths = stringify_paths(change_data.get("replace_paths"))

        if replace_paths:
            reasons.append("Replacement is caused by immutable field changes.")
            score += min(2, len(replace_paths))

        changed_fields: list[str] = []
        unknown_fields: list[str] = []
        if show_fields:
            changed_fields = changed_paths(change_data.get("before"), change_data.get("after"))
            unknown_fields = paths_from_unknown(change_data.get("after_unknown"))

        risk_level = risk_level_from_score(score)
        changes.append(
            ResourceChange(
                address=address,
                action=action,
                resource_type=resource_type,
                name=str(item.get("name") or ""),
                provider=short_provider_name(str(item.get("provider_name") or "")),
                module=item.get("module_address"),
                risk_level=risk_level,
                risk_score=score,
                reasons=reasons,
                replace_paths=replace_paths,
                changed_fields=changed_fields,
                unknown_fields=unknown_fields,
            )
        )

    risk_score = max((change.risk_score for change in changes), default=0)
    risk_level = highest_risk(change.risk_level for change in changes)

    for action in ["create", "update", "replace", "delete", "read", "no-op"]:
        counts.setdefault(action, 0)

    return PlanAnalysis(
        path=plan_path.as_posix(),
        format_version=raw.get("format_version"),
        terraform_version=raw.get("terraform_version"),
        counts=dict(counts),
        risk_level=risk_level,
        risk_score=risk_score,
        changes=changes,
    )


def load_plan_json(plan_path: Path, stdin_text: str | None = None) -> dict[str, Any] | PlanAnalysis:
    if plan_path.as_posix() == "-":
        if stdin_text is None:
            raise AnalysisError("No stdin data was provided for plan path '-'.")
        return parse_plan_json_text(stdin_text, "stdin")

    try:
        plan_bytes = plan_path.read_bytes()
    except FileNotFoundError as exc:
        raise AnalysisError(f"Plan file not found: {plan_path}") from exc

    stripped = plan_bytes.lstrip()
    if stripped.startswith(b"{"):
        try:
            plan_text = plan_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise AnalysisError(f"Plan JSON is not valid UTF-8: {plan_path}") from exc
        return parse_plan_json_text(plan_text, plan_path.as_posix())

    plan_text = decode_text_plan(plan_bytes)
    if plan_text is not None:
        clean_text = strip_ansi(plan_text)
        if looks_like_terraform_plan_text(clean_text):
            return parse_terraform_plan_text(clean_text, plan_path.as_posix())
        if plan_path.suffix.lower() == ".json":
            try:
                return parse_show_json_output(plan_text, "plan file", plan_path)
            except AnalysisError:
                pass
            raise AnalysisError(
                f"Plan file is not valid Terraform JSON: {plan_path}. "
                "`terraform plan -out=json`, `tofu plan -out=json`, and `terragrunt plan -out=json` "
                "write a saved plan file named 'json'; they do not produce JSON. "
                "Create JSON with `terraform show -json <tfplan> > plan.json`, "
                "`tofu show -json <tfplan> > plan.json`, or "
                "`terragrunt show -json <tfplan> > plan.json`. "
                "For human-readable plan text, pipe it directly: "
                "`terragrunt plan -no-color | tfexplain`."
            )

    return terraform_show_json(plan_path)


def parse_plan_json_text(plan_text: str, source: str) -> dict[str, Any]:
    if not plan_text.lstrip().startswith("{"):
        raise AnalysisError(
            f"Plan input from {source} must be Terraform JSON from `terraform show -json`; "
            "raw `terraform plan` text is not supported."
        )

    try:
        raw = json.loads(plan_text)
    except json.JSONDecodeError as exc:
        raise AnalysisError(f"Plan file is not valid JSON: {source}: {exc}") from exc

    if not isinstance(raw, dict):
        raise AnalysisError(f"Plan JSON must be an object: {source}")
    return raw


PLAN_TEXT_ACTIONS = {
    "will be created": "create",
    "will be updated in-place": "update",
    "will be destroyed": "delete",
    "must be replaced": "replace",
    "will be read during apply": "read",
}

PLAN_TEXT_MARKERS = (
    "Terraform will perform the following actions:",
    "OpenTofu will perform the following actions:",
    "No changes.",
)

PLAN_TEXT_RESOURCE_RE = re.compile(
    r"#\s+(.+?)\s+"
    r"(will be created|will be updated in-place|will be destroyed|must be replaced|will be read during apply)\s*$"
)


def parse_terraform_plan_text(plan_text: str, source: str = "stdin") -> PlanAnalysis:
    clean_text = strip_ansi(plan_text)
    if not any(marker in clean_text for marker in PLAN_TEXT_MARKERS):
        raise AnalysisError(
            f"Plan input from {source} must be Terraform JSON from `terraform show -json` "
            "or human-readable `terraform plan`, `tofu plan`, or `terragrunt plan` text."
        )

    changes: list[ResourceChange] = []
    counts: Counter[str] = Counter()

    for line in clean_text.splitlines():
        match = PLAN_TEXT_RESOURCE_RE.search(line)
        if not match:
            continue

        address = match.group(1)
        action = PLAN_TEXT_ACTIONS[match.group(2)]
        counts[action] += 1

        resource_type = infer_resource_type(address)
        score, reasons = score_resource_change(action, resource_type, address)
        changes.append(
            ResourceChange(
                address=address,
                action=action,
                resource_type=resource_type,
                name=infer_resource_name(address),
                provider=infer_provider_from_type(resource_type),
                module=infer_module_address(address),
                risk_level=risk_level_from_score(score),
                risk_score=score,
                reasons=reasons + ["Parsed from human-readable Terraform plan text; use JSON or tfplan input for field-level details."],
            )
        )

    risk_score = max((change.risk_score for change in changes), default=0)
    risk_level = highest_risk(change.risk_level for change in changes)

    for action in ["create", "update", "replace", "delete", "read", "no-op"]:
        counts.setdefault(action, 0)

    return PlanAnalysis(
        path=source,
        format_version=None,
        terraform_version=None,
        counts=dict(counts),
        risk_level=risk_level,
        risk_score=risk_score,
        changes=changes,
    )


def strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", text)


def decode_text_plan(plan_bytes: bytes) -> str | None:
    for encoding in ("utf-8", "utf-16"):
        try:
            return plan_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
    return None


def looks_like_terraform_plan_text(plan_text: str) -> bool:
    return any(marker in plan_text for marker in PLAN_TEXT_MARKERS)


def infer_resource_name(address: str) -> str:
    parts = address.split(".")
    return parts[-1] if parts else ""


def infer_provider_from_type(resource_type: str) -> str:
    if resource_type == "terraform_data":
        return "terraform"
    if "_" in resource_type:
        return resource_type.split("_", maxsplit=1)[0]
    return "unknown"


def infer_module_address(address: str) -> str | None:
    parts = address.split(".")
    if not parts or parts[0] != "module":
        return None
    module_parts: list[str] = []
    index = 0
    while index + 1 < len(parts) and parts[index] == "module":
        module_parts.extend(parts[index : index + 2])
        index += 2
    return ".".join(module_parts) if module_parts else None


def terraform_show_json(plan_path: Path) -> dict[str, Any]:
    commands = [
        ("terraform", ["terraform", "show", "-json", plan_path.as_posix()]),
        ("tofu", ["tofu", "show", "-json", plan_path.as_posix()]),
        ("terragrunt", ["terragrunt", "show", "-json", plan_path.as_posix()]),
    ]
    failures: list[str] = []

    for name, command in commands:
        try:
            completed = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
        except FileNotFoundError:
            failures.append(f"{name}: executable not found")
            continue

        if completed.returncode != 0:
            stderr = completed.stderr.strip()
            detail = stderr if stderr else f"exited with code {completed.returncode}"
            failures.append(f"{name}: {detail}")
            continue

        return parse_show_json_output(completed.stdout, name, plan_path)

    if all("executable not found" in failure for failure in failures):
        raise AnalysisError(
            "Terraform, OpenTofu, or Terragrunt executable was not found. Install one of them, "
            "or pass JSON generated by `terraform show -json <tfplan> > plan.json`, "
            "`tofu show -json <tfplan> > plan.json`, or "
            "`terragrunt show -json <tfplan> > plan.json`."
        )

    raise AnalysisError(
        "Failed to convert saved Terraform/OpenTofu plan with `terraform show -json`, "
        "`tofu show -json`, or `terragrunt show -json`: "
        + "; ".join(failures)
    )


def parse_show_json_output(output: str, command_name: str, plan_path: Path) -> dict[str, Any]:
    text = output.lstrip()
    start = text.find("{")
    if start > 0:
        text = text[start:]

    try:
        raw, _ = json.JSONDecoder().raw_decode(text)
    except json.JSONDecodeError as exc:
        raise AnalysisError(f"`{command_name} show -json` did not return valid JSON for {plan_path}: {exc}") from exc

    if not isinstance(raw, dict):
        raise AnalysisError(f"`{command_name} show -json` must return a JSON object for {plan_path}")
    return raw


def infer_resource_type(address: str) -> str:
    parts = address.split(".")
    if not parts:
        return "unknown"
    if parts[0] == "module" and len(parts) >= 3:
        return parts[-2]
    if len(parts) >= 2:
        return parts[-2]
    return parts[0] or "unknown"


def short_provider_name(provider_name: str) -> str:
    if not provider_name:
        return "unknown"
    return provider_name.rsplit("/", maxsplit=1)[-1]


def stringify_paths(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        if isinstance(item, list):
            result.append(".".join(str(part) for part in item))
        elif isinstance(item, str):
            result.append(item)
    return result


def changed_paths(before: Any, after: Any, prefix: str = "", limit: int = 40) -> list[str]:
    if limit <= 0:
        return []
    if before == after:
        return []

    if isinstance(before, dict) and isinstance(after, dict):
        paths: list[str] = []
        keys = sorted(set(before) | set(after), key=str)
        for key in keys:
            next_prefix = dotted(prefix, key)
            paths.extend(changed_paths(before.get(key), after.get(key), next_prefix, limit - len(paths)))
            if len(paths) >= limit:
                return paths[:limit]
        return paths

    if isinstance(before, list) and isinstance(after, list):
        if len(before) != len(after):
            return [prefix or "<root>"]
        paths = []
        for index, (left, right) in enumerate(zip(before, after)):
            next_prefix = f"{prefix}[{index}]" if prefix else f"[{index}]"
            paths.extend(changed_paths(left, right, next_prefix, limit - len(paths)))
            if len(paths) >= limit:
                return paths[:limit]
        return paths

    return [prefix or "<root>"]


def paths_from_unknown(value: Any, prefix: str = "", limit: int = 40) -> list[str]:
    if limit <= 0:
        return []
    if value is True:
        return [prefix or "<root>"]
    if value in (False, None):
        return []
    if isinstance(value, dict):
        result: list[str] = []
        for key in sorted(value, key=str):
            result.extend(paths_from_unknown(value[key], dotted(prefix, key), limit - len(result)))
            if len(result) >= limit:
                return result[:limit]
        return result
    if isinstance(value, list):
        result = []
        for index, item in enumerate(value):
            next_prefix = f"{prefix}[{index}]" if prefix else f"[{index}]"
            result.extend(paths_from_unknown(item, next_prefix, limit - len(result)))
            if len(result) >= limit:
                return result[:limit]
        return result
    return []


def dotted(prefix: str, key: object) -> str:
    text = str(key)
    return f"{prefix}.{text}" if prefix else text
