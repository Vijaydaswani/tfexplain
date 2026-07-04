from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import asdict
from typing import Iterable

from .models import CodeAnalysis, CodeFinding, PlanAnalysis, ResourceChange


def render_plan(analysis: PlanAnalysis, output_format: str = "text", group_by: str = "action") -> str:
    if output_format == "json":
        return json.dumps(analysis.to_dict(), indent=2, sort_keys=True)
    if output_format == "markdown":
        return render_plan_markdown(analysis, group_by)
    return render_plan_text(analysis, group_by)


def render_code(analysis: CodeAnalysis, output_format: str = "text") -> str:
    if output_format == "json":
        return json.dumps(analysis.to_dict(), indent=2, sort_keys=True)
    if output_format == "markdown":
        return render_code_markdown(analysis)
    return render_code_text(analysis)


def render_combined(
    code_analysis: CodeAnalysis,
    plan_analysis: PlanAnalysis,
    output_format: str = "text",
    group_by: str = "action",
) -> str:
    if output_format == "json":
        payload = {
            "code": code_analysis.to_dict(),
            "plan": plan_analysis.to_dict(),
        }
        return json.dumps(payload, indent=2, sort_keys=True)
    if output_format == "markdown":
        return "\n\n".join(
            [
                "# Terraform Explanation",
                render_plan_markdown(plan_analysis, group_by, include_title=False),
                render_code_markdown(code_analysis, include_title=False),
            ]
        )
    return "\n\n".join(
        [
            "Terraform Explanation",
            "=" * 23,
            render_plan_text(plan_analysis, group_by, include_title=False),
            render_code_text(code_analysis, include_title=False),
        ]
    )


def render_plan_text(analysis: PlanAnalysis, group_by: str = "action", include_title: bool = True) -> str:
    lines: list[str] = []
    if include_title:
        lines.append("Terraform Plan Summary")
        lines.append("")
    lines.extend(plan_header_lines(analysis))

    high_attention = analysis.high_attention()
    if high_attention:
        lines.append("")
        lines.append("High Attention:")
        for change in sorted_changes(high_attention):
            lines.append(f"- {change.address} will be {past_tense(change.action)} ({change.risk_level})")
            if change.reasons:
                lines.append(f"  Reason: {change.reasons[0]}")

    actionable = [change for change in analysis.changes if change.action != "no-op"]
    if actionable:
        lines.append("")
        lines.append(f"Resource Changes by {group_by.title()}:")
        for label, changes in group_changes(actionable, group_by):
            lines.append(f"{label}:")
            for change in sorted_changes(changes):
                lines.extend(render_change_text(change))
    else:
        lines.append("")
        lines.append("No resource changes detected.")

    return "\n".join(lines)


def render_plan_markdown(analysis: PlanAnalysis, group_by: str = "action", include_title: bool = True) -> str:
    lines: list[str] = []
    if include_title:
        lines.append("# Terraform Plan Summary")
        lines.append("")
    lines.extend(markdown_plan_header_lines(analysis))

    high_attention = analysis.high_attention()
    if high_attention:
        lines.append("")
        lines.append("## High Attention")
        lines.append("")
        for change in sorted_changes(high_attention):
            reason = f" - {change.reasons[0]}" if change.reasons else ""
            lines.append(f"- `{change.address}` will be **{past_tense(change.action)}** (`{change.risk_level}`){reason}")

    actionable = [change for change in analysis.changes if change.action != "no-op"]
    if actionable:
        lines.append("")
        lines.append(f"## Resource Changes by {group_by.title()}")
        lines.append("")
        for label, changes in group_changes(actionable, group_by):
            lines.append(f"### {label}")
            lines.append("")
            for change in sorted_changes(changes):
                lines.extend(render_change_markdown(change))
    else:
        lines.append("")
        lines.append("No resource changes detected.")

    return "\n".join(lines)


def render_code_text(analysis: CodeAnalysis, include_title: bool = True) -> str:
    lines: list[str] = []
    if include_title:
        lines.append("Terraform Code Summary")
        lines.append("")

    lines.append(f"Path: {analysis.path}")
    lines.append(f"Terraform files: {len(analysis.terraform_files)}")
    lines.append(f"Providers: {join_or_none(analysis.providers)}")
    lines.append(f"Required version: {analysis.required_version or 'not specified'}")
    lines.append(f"Backends: {join_or_none(analysis.backends)}")
    lines.append(f"Modules: {len(analysis.modules)}")
    lines.append(f"Resources: {len(analysis.resources)}")
    lines.append(f"Data sources: {len(analysis.data_sources)}")
    lines.append(f"Variables: {len(analysis.variables)}")
    lines.append(f"Outputs: {len(analysis.outputs)}")
    lines.append(f"Locals: {analysis.locals_count}")

    if analysis.modules:
        lines.append("")
        lines.append("Modules:")
        for module in analysis.modules:
            source = f" source={module['source']}" if module.get("source") else ""
            lines.append(f"- module.{module['name']}{source}")

    resource_counts = count_by(analysis.resources, "type")
    if resource_counts:
        lines.append("")
        lines.append("Resources:")
        for resource_type, count in resource_counts:
            lines.append(f"- {resource_type}: {count}")

    lines.append("")
    lines.append("Module Quality:")
    lines.append(f"- README: {'found' if analysis.has_readme else 'missing'}")
    lines.append(f"- examples directory: {'found' if analysis.has_examples else 'missing'}")
    lines.append(f"- variables.tf: {'found' if analysis.has_variables_tf else 'missing'}")
    lines.append(f"- outputs.tf: {'found' if analysis.has_outputs_tf else 'missing'}")
    lines.append(f"- variables without descriptions: {count_missing(analysis.variables, 'has_description')}")
    lines.append(f"- variables without validation: {count_missing(analysis.variables, 'has_validation')}")
    lines.append(f"- outputs without descriptions: {count_missing(analysis.outputs, 'has_description')}")

    lines.extend(render_findings_text(analysis.findings))
    return "\n".join(lines)


def render_code_markdown(analysis: CodeAnalysis, include_title: bool = True) -> str:
    lines: list[str] = []
    if include_title:
        lines.append("# Terraform Code Summary")
        lines.append("")

    lines.append(f"- Path: `{analysis.path}`")
    lines.append(f"- Terraform files: `{len(analysis.terraform_files)}`")
    lines.append(f"- Providers: {markdown_values(analysis.providers)}")
    lines.append(f"- Required version: `{analysis.required_version or 'not specified'}`")
    lines.append(f"- Backends: {markdown_values(analysis.backends)}")
    lines.append(f"- Modules: `{len(analysis.modules)}`")
    lines.append(f"- Resources: `{len(analysis.resources)}`")
    lines.append(f"- Data sources: `{len(analysis.data_sources)}`")
    lines.append(f"- Variables: `{len(analysis.variables)}`")
    lines.append(f"- Outputs: `{len(analysis.outputs)}`")
    lines.append(f"- Locals: `{analysis.locals_count}`")

    if analysis.modules:
        lines.append("")
        lines.append("## Modules")
        lines.append("")
        for module in analysis.modules:
            source = f" source=`{module['source']}`" if module.get("source") else ""
            lines.append(f"- `module.{module['name']}`{source}")

    resource_counts = count_by(analysis.resources, "type")
    if resource_counts:
        lines.append("")
        lines.append("## Resources")
        lines.append("")
        for resource_type, count in resource_counts:
            lines.append(f"- `{resource_type}`: `{count}`")

    lines.append("")
    lines.append("## Module Quality")
    lines.append("")
    lines.append(f"- README: **{'found' if analysis.has_readme else 'missing'}**")
    lines.append(f"- examples directory: **{'found' if analysis.has_examples else 'missing'}**")
    lines.append(f"- variables.tf: **{'found' if analysis.has_variables_tf else 'missing'}**")
    lines.append(f"- outputs.tf: **{'found' if analysis.has_outputs_tf else 'missing'}**")
    lines.append(f"- variables without descriptions: `{count_missing(analysis.variables, 'has_description')}`")
    lines.append(f"- variables without validation: `{count_missing(analysis.variables, 'has_validation')}`")
    lines.append(f"- outputs without descriptions: `{count_missing(analysis.outputs, 'has_description')}`")

    lines.extend(render_findings_markdown(analysis.findings))
    return "\n".join(lines)


def plan_header_lines(analysis: PlanAnalysis) -> list[str]:
    return [
        f"Plan file: {analysis.path}",
        f"Terraform version: {analysis.terraform_version or 'unknown'}",
        f"Create: {analysis.counts.get('create', 0)}",
        f"Update: {analysis.counts.get('update', 0)}",
        f"Replace: {analysis.counts.get('replace', 0)}",
        f"Delete: {analysis.counts.get('delete', 0)}",
        f"Read: {analysis.counts.get('read', 0)}",
        f"No-op: {analysis.counts.get('no-op', 0)}",
        f"Risk Score: {analysis.risk_level.title()} ({analysis.risk_score})",
    ]


def markdown_plan_header_lines(analysis: PlanAnalysis) -> list[str]:
    return [
        f"- Plan file: `{analysis.path}`",
        f"- Terraform version: `{analysis.terraform_version or 'unknown'}`",
        f"- Create: `{analysis.counts.get('create', 0)}`",
        f"- Update: `{analysis.counts.get('update', 0)}`",
        f"- Replace: `{analysis.counts.get('replace', 0)}`",
        f"- Delete: `{analysis.counts.get('delete', 0)}`",
        f"- Read: `{analysis.counts.get('read', 0)}`",
        f"- No-op: `{analysis.counts.get('no-op', 0)}`",
        f"- Risk Score: **{analysis.risk_level.title()}** (`{analysis.risk_score}`)",
    ]


def render_change_text(change: ResourceChange) -> list[str]:
    lines = [
        f"- {change.address}: {change.action} ({change.risk_level}, score {change.risk_score})",
    ]
    if change.provider != "unknown":
        lines.append(f"  Provider: {change.provider}")
    if change.module:
        lines.append(f"  Module: {change.module}")
    if change.replace_paths:
        lines.append(f"  Replace paths: {', '.join(change.replace_paths)}")
    if change.changed_fields:
        lines.append(f"  Changed fields: {', '.join(change.changed_fields)}")
    if change.unknown_fields:
        lines.append(f"  Known after apply: {', '.join(change.unknown_fields)}")
    for reason in change.reasons:
        lines.append(f"  Reason: {reason}")
    return lines


def render_change_markdown(change: ResourceChange) -> list[str]:
    lines = [
        f"- `{change.address}`: **{change.action}** (`{change.risk_level}`, score `{change.risk_score}`)",
    ]
    details: list[str] = []
    if change.provider != "unknown":
        details.append(f"provider `{change.provider}`")
    if change.module:
        details.append(f"module `{change.module}`")
    if details:
        lines.append(f"  - {'; '.join(details)}")
    if change.replace_paths:
        lines.append(f"  - Replace paths: {markdown_values(change.replace_paths)}")
    if change.changed_fields:
        lines.append(f"  - Changed fields: {markdown_values(change.changed_fields)}")
    if change.unknown_fields:
        lines.append(f"  - Known after apply: {markdown_values(change.unknown_fields)}")
    for reason in change.reasons:
        lines.append(f"  - {reason}")
    return lines


def render_findings_text(findings: Iterable[CodeFinding]) -> list[str]:
    findings = list(findings)
    if not findings:
        return ["", "Findings: none"]
    lines = ["", "Findings:"]
    for finding in findings[:30]:
        location = ""
        if finding.file:
            location = f" ({finding.file}:{finding.line})" if finding.line else f" ({finding.file})"
        lines.append(f"- [{finding.level}] {finding.target}: {finding.message}{location}")
    if len(findings) > 30:
        lines.append(f"- ... {len(findings) - 30} more findings")
    return lines


def render_findings_markdown(findings: Iterable[CodeFinding]) -> list[str]:
    findings = list(findings)
    if not findings:
        return ["", "## Findings", "", "None."]
    lines = ["", "## Findings", ""]
    for finding in findings[:30]:
        location = ""
        if finding.file:
            location = f" (`{finding.file}:{finding.line}`)" if finding.line else f" (`{finding.file}`)"
        lines.append(f"- **{finding.level}** `{finding.target}`: {finding.message}{location}")
    if len(findings) > 30:
        lines.append(f"- ... `{len(findings) - 30}` more findings")
    return lines


def group_changes(changes: Iterable[ResourceChange], group_by: str) -> list[tuple[str, list[ResourceChange]]]:
    grouped: dict[str, list[ResourceChange]] = defaultdict(list)
    for change in changes:
        if group_by == "provider":
            label = change.provider or "unknown"
        elif group_by == "module":
            label = change.module or "root"
        elif group_by == "risk":
            label = change.risk_level
        else:
            label = change.action
        grouped[label].append(change)
    return sorted(grouped.items(), key=lambda item: item[0])


def sorted_changes(changes: Iterable[ResourceChange]) -> list[ResourceChange]:
    return sorted(changes, key=lambda change: (change.action, change.risk_level, change.address))


def count_by(items: Iterable[dict[str, object]], key: str) -> list[tuple[str, int]]:
    counter = Counter(str(item.get(key) or "unknown") for item in items)
    return sorted(counter.items(), key=lambda item: (-item[1], item[0]))


def count_missing(items: Iterable[dict[str, object]], key: str) -> int:
    return sum(1 for item in items if not item.get(key))


def join_or_none(values: Iterable[str]) -> str:
    values = list(values)
    return ", ".join(values) if values else "none"


def markdown_values(values: Iterable[str]) -> str:
    values = list(values)
    if not values:
        return "`none`"
    return ", ".join(f"`{value}`" for value in values)


def past_tense(action: str) -> str:
    return {
        "create": "created",
        "update": "updated",
        "delete": "deleted",
        "replace": "replaced",
        "read": "read",
        "no-op": "unchanged",
    }.get(action, action)
