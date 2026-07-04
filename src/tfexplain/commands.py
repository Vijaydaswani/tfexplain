from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict
from pathlib import Path

from .errors import AnalysisError
from .models import CodeAnalysis, PlanAnalysis
from .render import count_missing, markdown_values


DEFAULT_CONFIG = {
    "format": "text",
    "group_by": "action",
    "fail_on": ["delete", "replace", "critical"],
    "ai": {
        "enabled": False,
        "provider": "openai",
        "model": None,
    },
}


def render_review(
    code_analysis: CodeAnalysis | None,
    plan_analysis: PlanAnalysis | None,
    output_format: str = "text",
) -> str:
    if output_format == "json":
        return json.dumps(
            {
                "code": code_analysis.to_dict() if code_analysis else None,
                "plan": plan_analysis.to_dict() if plan_analysis else None,
                "focus": review_focus_items(code_analysis, plan_analysis),
            },
            indent=2,
            sort_keys=True,
        )
    if output_format == "github":
        return render_review_github(code_analysis, plan_analysis)
    if output_format == "markdown":
        return render_review_markdown(code_analysis, plan_analysis)
    return render_review_text(code_analysis, plan_analysis)


def render_review_text(code_analysis: CodeAnalysis | None, plan_analysis: PlanAnalysis | None) -> str:
    lines = ["Terraform Review Summary", ""]

    if plan_analysis:
        lines.extend(
            [
                f"Plan risk: {plan_analysis.risk_level.title()} ({plan_analysis.risk_score})",
                f"Create: {plan_analysis.counts.get('create', 0)}",
                f"Update: {plan_analysis.counts.get('update', 0)}",
                f"Replace: {plan_analysis.counts.get('replace', 0)}",
                f"Delete: {plan_analysis.counts.get('delete', 0)}",
            ]
        )

    if code_analysis:
        if plan_analysis:
            lines.append("")
        lines.extend(
            [
                f"Code path: {code_analysis.path}",
                f"Providers: {', '.join(code_analysis.providers) if code_analysis.providers else 'none'}",
                f"Resources: {len(code_analysis.resources)}",
                f"Variables without descriptions: {count_missing(code_analysis.variables, 'has_description')}",
                f"Variables without validation: {count_missing(code_analysis.variables, 'has_validation')}",
                f"Findings: {len(code_analysis.findings)}",
            ]
        )

    focus = review_focus_items(code_analysis, plan_analysis)
    lines.append("")
    lines.append("Review Focus:")
    if focus:
        lines.extend(f"- {item}" for item in focus)
    else:
        lines.append("- No high-attention review items detected.")

    return "\n".join(lines)


def render_review_markdown(code_analysis: CodeAnalysis | None, plan_analysis: PlanAnalysis | None) -> str:
    lines = ["# Terraform Review Summary", ""]

    if plan_analysis:
        lines.extend(
            [
                f"- Plan risk: **{plan_analysis.risk_level.title()}** (`{plan_analysis.risk_score}`)",
                f"- Create: `{plan_analysis.counts.get('create', 0)}`",
                f"- Update: `{plan_analysis.counts.get('update', 0)}`",
                f"- Replace: `{plan_analysis.counts.get('replace', 0)}`",
                f"- Delete: `{plan_analysis.counts.get('delete', 0)}`",
            ]
        )

    if code_analysis:
        if plan_analysis:
            lines.append("")
        lines.extend(
            [
                f"- Code path: `{code_analysis.path}`",
                f"- Providers: {markdown_values(code_analysis.providers)}",
                f"- Resources: `{len(code_analysis.resources)}`",
                f"- Variables without descriptions: `{count_missing(code_analysis.variables, 'has_description')}`",
                f"- Variables without validation: `{count_missing(code_analysis.variables, 'has_validation')}`",
                f"- Findings: `{len(code_analysis.findings)}`",
            ]
        )

    focus = review_focus_items(code_analysis, plan_analysis)
    lines.append("")
    lines.append("## Review Focus")
    lines.append("")
    if focus:
        lines.extend(f"- {item}" for item in focus)
    else:
        lines.append("- No high-attention review items detected.")

    return "\n".join(lines)


def render_review_github(code_analysis: CodeAnalysis | None, plan_analysis: PlanAnalysis | None) -> str:
    lines = ["## tfexplain Review", ""]

    if plan_analysis:
        lines.extend(
            [
                "### Plan",
                "",
                "| Risk | Create | Update | Replace | Delete |",
                "| --- | ---: | ---: | ---: | ---: |",
                (
                    f"| **{plan_analysis.risk_level.title()}** (`{plan_analysis.risk_score}`) "
                    f"| {plan_analysis.counts.get('create', 0)} "
                    f"| {plan_analysis.counts.get('update', 0)} "
                    f"| {plan_analysis.counts.get('replace', 0)} "
                    f"| {plan_analysis.counts.get('delete', 0)} |"
                ),
                "",
            ]
        )

    if code_analysis:
        lines.extend(
            [
                "### Code",
                "",
                f"- Path: `{code_analysis.path}`",
                f"- Providers: {markdown_values(code_analysis.providers)}",
                f"- Resources: `{len(code_analysis.resources)}`",
                f"- Findings: `{len(code_analysis.findings)}`",
                "",
            ]
        )

    focus = review_focus_items(code_analysis, plan_analysis)
    lines.extend(["### Reviewer Focus", ""])
    if focus:
        lines.extend(f"- {item}" for item in focus)
    else:
        lines.append("- No high-attention review items detected.")

    lines.extend(
        [
            "",
            "<details>",
            "<summary>About tfexplain</summary>",
            "",
            "Generated by `bna-tools/tfexplain`, an open-source Build & Automate Terraform explainer.",
            "",
            "</details>",
        ]
    )
    return "\n".join(lines)


def review_focus_items(code_analysis: CodeAnalysis | None, plan_analysis: PlanAnalysis | None) -> list[str]:
    items: list[str] = []

    if plan_analysis:
        for change in plan_analysis.high_attention()[:15]:
            items.append(f"{change.address} is being {action_phrase(change.action)} with {change.risk_level} risk.")

    if code_analysis:
        high_findings = [finding for finding in code_analysis.findings if finding.level in {"high", "critical"}]
        for finding in high_findings[:10]:
            items.append(f"{finding.target}: {finding.message}")

        missing_descriptions = count_missing(code_analysis.variables, "has_description")
        if missing_descriptions:
            items.append(f"{missing_descriptions} variables are missing descriptions.")

        missing_validations = count_missing(code_analysis.variables, "has_validation")
        if missing_validations:
            items.append(f"{missing_validations} variables have no validation block.")

    return items


def render_docs(analysis: CodeAnalysis, output_format: str = "markdown") -> str:
    if output_format == "json":
        return json.dumps(analysis.to_dict(), indent=2, sort_keys=True)
    if output_format == "text":
        return render_docs_text(analysis)
    return render_docs_markdown(analysis)


def render_docs_markdown(analysis: CodeAnalysis) -> str:
    lines = [
        "# Terraform Module Documentation",
        "",
        f"- Path: `{analysis.path}`",
        f"- Required Terraform version: `{analysis.required_version or 'not specified'}`",
        f"- Providers: {markdown_values(analysis.providers)}",
        f"- Backends: {markdown_values(analysis.backends)}",
        "",
        "## Resources",
        "",
    ]

    if analysis.resources:
        for resource_type, count in sorted(Counter(item["type"] for item in analysis.resources).items()):
            lines.append(f"- `{resource_type}`: `{count}`")
    else:
        lines.append("No managed resources found.")

    lines.extend(["", "## Inputs", ""])
    if analysis.variables:
        lines.append("| Name | Type | Default | Description | Validation |")
        lines.append("| --- | --- | --- | --- | --- |")
        for variable in analysis.variables:
            lines.append(
                "| "
                + " | ".join(
                    [
                        f"`{variable['name']}`",
                        f"`{variable.get('type') or 'any'}`",
                        "yes" if variable.get("has_default") else "no",
                        "yes" if variable.get("has_description") else "no",
                        "yes" if variable.get("has_validation") else "no",
                    ]
                )
                + " |"
            )
    else:
        lines.append("No inputs found.")

    lines.extend(["", "## Outputs", ""])
    if analysis.outputs:
        lines.append("| Name | Description |")
        lines.append("| --- | --- |")
        for output in analysis.outputs:
            lines.append(f"| `{output['name']}` | {'yes' if output.get('has_description') else 'no'} |")
    else:
        lines.append("No outputs found.")

    lines.extend(["", "## Findings", ""])
    if analysis.findings:
        for finding in analysis.findings[:30]:
            location = f" (`{finding.file}:{finding.line}`)" if finding.file and finding.line else ""
            lines.append(f"- **{finding.level}** `{finding.target}`: {finding.message}{location}")
    else:
        lines.append("No findings.")

    return "\n".join(lines)


def render_docs_text(analysis: CodeAnalysis) -> str:
    lines = [
        "Terraform Module Documentation",
        "",
        f"Path: {analysis.path}",
        f"Required Terraform version: {analysis.required_version or 'not specified'}",
        f"Providers: {', '.join(analysis.providers) if analysis.providers else 'none'}",
        f"Resources: {len(analysis.resources)}",
        f"Inputs: {len(analysis.variables)}",
        f"Outputs: {len(analysis.outputs)}",
        f"Findings: {len(analysis.findings)}",
    ]
    return "\n".join(lines)


def render_graph(analysis: CodeAnalysis, output_format: str = "text") -> str:
    graph = graph_payload(analysis)
    if output_format == "json":
        return json.dumps(graph, indent=2, sort_keys=True)
    if output_format == "ascii":
        return render_graph_ascii(graph)
    if output_format == "mermaid":
        return render_graph_mermaid(graph)
    if output_format == "dot":
        return render_graph_dot(graph)
    return render_graph_text(graph)


def graph_payload(analysis: CodeAnalysis) -> dict[str, object]:
    providers = [{"id": f"provider.{provider}", "label": provider} for provider in analysis.providers]
    modules = [{"id": f"module.{module['name']}", "label": module["name"], "source": module.get("source")} for module in analysis.modules]
    resources = [
        {
            "id": f"{resource['type']}.{resource['name']}",
            "label": f"{resource['type']}.{resource['name']}",
            "provider": resource.get("provider") or "unknown",
        }
        for resource in analysis.resources
    ]
    data_sources = [
        {
            "id": f"data.{data['type']}.{data['name']}",
            "label": f"data.{data['type']}.{data['name']}",
            "provider": data.get("provider") or "unknown",
        }
        for data in analysis.data_sources
    ]
    edges = [
        {"from": f"provider.{resource['provider']}", "to": resource["id"], "label": "manages"}
        for resource in resources
        if resource["provider"] != "unknown"
    ]
    edges.extend(
        {"from": f"provider.{data['provider']}", "to": data["id"], "label": "reads"}
        for data in data_sources
        if data["provider"] != "unknown"
    )
    return {
        "path": analysis.path,
        "providers": providers,
        "modules": modules,
        "resources": resources,
        "data_sources": data_sources,
        "edges": edges,
    }


def render_graph_text(graph: dict[str, object]) -> str:
    lines = ["Terraform Graph", "", f"Path: {graph['path']}", ""]
    lines.append("Nodes:")
    for section in ["providers", "modules", "resources", "data_sources"]:
        for node in graph[section]:
            lines.append(f"- {node['id']}")
    lines.append("")
    lines.append("Edges:")
    edges = graph["edges"]
    if edges:
        for edge in edges:
            lines.append(f"- {edge['from']} -> {edge['to']} ({edge['label']})")
    else:
        lines.append("- none")
    return "\n".join(lines)


def render_graph_ascii(graph: dict[str, object]) -> str:
    provider_children: dict[str, list[dict[str, str]]] = {}
    unlinked_nodes: list[dict[str, str]] = []

    for node in graph["providers"]:
        provider_children[node["id"]] = []

    nodes_by_id = {
        node["id"]: node
        for section in ["modules", "resources", "data_sources"]
        for node in graph[section]
    }

    linked_ids: set[str] = set()
    for edge in graph["edges"]:
        child = nodes_by_id.get(edge["to"])
        if not child:
            continue
        linked_ids.add(edge["to"])
        provider_children.setdefault(edge["from"], []).append({"label": child["label"], "edge": edge["label"]})

    for section in ["modules", "resources", "data_sources"]:
        for node in graph[section]:
            if node["id"] not in linked_ids:
                unlinked_nodes.append({"label": node["label"], "edge": "node"})

    lines = ["Terraform Graph", "", f"Path: {graph['path']}", ""]

    if provider_children:
        for provider in graph["providers"]:
            lines.append(f"provider.{provider['label']}")
            children = sorted(provider_children.get(provider["id"], []), key=lambda item: item["label"])
            if children:
                lines.extend(ascii_children(children))
            else:
                lines.append("`-- no linked resources")

    if unlinked_nodes:
        if provider_children:
            lines.append("")
        lines.append("unlinked")
        lines.extend(ascii_children(sorted(unlinked_nodes, key=lambda item: item["label"])))

    if not provider_children and not unlinked_nodes:
        lines.append("No graph nodes found.")

    return "\n".join(lines)


def ascii_children(children: list[dict[str, str]]) -> list[str]:
    lines: list[str] = []
    for index, child in enumerate(children):
        connector = "`--" if index == len(children) - 1 else "|--"
        lines.append(f"{connector} {child['edge']} -> {child['label']}")
    return lines


def render_graph_mermaid(graph: dict[str, object]) -> str:
    lines = ["flowchart TD"]
    for section in ["providers", "modules", "resources", "data_sources"]:
        for node in graph[section]:
            lines.append(f"  {node_id(node['id'])}[\"{node['label']}\"]")
    for edge in graph["edges"]:
        lines.append(f"  {node_id(edge['from'])} -->|{edge['label']}| {node_id(edge['to'])}")
    return "\n".join(lines)


def render_graph_dot(graph: dict[str, object]) -> str:
    lines = ["digraph terraform {", "  rankdir=LR;"]
    for section in ["providers", "modules", "resources", "data_sources"]:
        for node in graph[section]:
            lines.append(f"  \"{node['id']}\" [label=\"{node['label']}\"];")
    for edge in graph["edges"]:
        lines.append(f"  \"{edge['from']}\" -> \"{edge['to']}\" [label=\"{edge['label']}\"];")
    lines.append("}")
    return "\n".join(lines)


def node_id(value: str) -> str:
    return "".join(char if char.isalnum() else "_" for char in value)


def action_phrase(action: str) -> str:
    return {
        "create": "created",
        "update": "updated",
        "replace": "replaced",
        "delete": "deleted",
        "read": "read",
    }.get(action, action)


def init_config(path: str | Path = ".", force: bool = False) -> Path:
    root = Path(path)
    if not root.exists():
        raise AnalysisError(f"Directory not found: {root}")
    if not root.is_dir():
        raise AnalysisError(f"Init path must be a directory: {root}")

    config_path = root / ".tfexplain.json"
    if config_path.exists() and not force:
        raise AnalysisError(f"Config already exists: {config_path}. Use --force to overwrite it.")

    config_path.write_text(json.dumps(DEFAULT_CONFIG, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return config_path
