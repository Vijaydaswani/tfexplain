from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __author__, __company__, __description__, __package_shortform__, __version__, __website__
from .ai import append_ai_to_output, explain_with_ai
from .code import analyze_code
from .commands import init_config, render_docs, render_graph, render_review
from .errors import AnalysisError, TfExplainError
from .plan import analyze_plan
from .render import render_code, render_combined, render_plan
from .risk import fail_condition_matches


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tfexplain",
        description="Explain Terraform code, Terraform plan JSON, and saved tfplan files.",
        epilog=cli_info(),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=version_info())

    subparsers = parser.add_subparsers(dest="command", required=True)

    plan_parser = subparsers.add_parser("plan", help="Explain a Terraform plan JSON or saved tfplan file.")
    add_plan_args(plan_parser)
    add_output_args(plan_parser)
    add_ai_args(plan_parser)

    code_parser = subparsers.add_parser("code", help="Explain Terraform code in a directory.")
    code_parser.add_argument("path", help="Terraform code directory.")
    add_output_args(code_parser)
    add_ai_args(code_parser)

    explain_parser = subparsers.add_parser("explain", help="Explain Terraform code and plan output together.")
    explain_parser.add_argument("--code", required=True, help="Terraform code directory.")
    explain_parser.add_argument("--plan", required=True, help="Terraform plan JSON, saved tfplan file, or '-' for stdin JSON.")
    explain_parser.add_argument("--show-fields", action="store_true", help="Show changed field paths from the plan.")
    explain_parser.add_argument(
        "--group-by",
        choices=["action", "provider", "module", "risk"],
        default="action",
        help="Group plan changes in the rendered output.",
    )
    explain_parser.add_argument(
        "--fail-on",
        help="Exit with code 2 when actions or risk levels are present, e.g. delete,replace,high.",
    )
    add_output_args(explain_parser)
    add_ai_args(explain_parser)

    risk_parser = subparsers.add_parser("risk", help="Summarize risk for a Terraform plan JSON or saved tfplan file.")
    add_plan_args(risk_parser)
    risk_parser.set_defaults(group_by="risk", risk=True)
    add_output_args(risk_parser)
    add_ai_args(risk_parser)

    review_parser = subparsers.add_parser("review", help="Generate a Terraform review summary.")
    review_parser.add_argument("--code", help="Terraform code directory.")
    review_parser.add_argument("--plan", help="Terraform plan JSON, saved tfplan file, or '-' for stdin.")
    review_parser.add_argument("--show-fields", action="store_true", help="Show changed field paths from the plan.")
    review_parser.add_argument(
        "--fail-on",
        help="Exit with code 2 when actions or risk levels are present, e.g. delete,replace,high.",
    )
    add_review_output_args(review_parser)
    add_ai_args(review_parser)

    docs_parser = subparsers.add_parser("docs", help="Generate Terraform module documentation.")
    docs_parser.add_argument("path", help="Terraform code directory.")
    docs_parser.add_argument(
        "--format",
        choices=["markdown", "text", "json"],
        default="markdown",
        help="Output format.",
    )
    docs_parser.add_argument("--output", help="Write output to a file instead of stdout.")

    graph_parser = subparsers.add_parser("graph", help="Generate a Terraform resource graph.")
    graph_parser.add_argument("path", help="Terraform code directory.")
    graph_parser.add_argument(
        "--format",
        choices=["text", "ascii", "mermaid", "dot", "json"],
        default="text",
        help="Output format.",
    )
    graph_parser.add_argument("--output", help="Write output to a file instead of stdout.")

    init_parser = subparsers.add_parser("init", help="Create a .tfexplain.json config file.")
    init_parser.add_argument("path", nargs="?", default=".", help="Directory to initialize.")
    init_parser.add_argument("--force", action="store_true", help="Overwrite an existing config file.")

    subparsers.add_parser("version", help="Print tfexplain version.")

    return parser


def add_plan_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("path", help="Terraform plan JSON file, saved tfplan file, or '-' for stdin JSON.")
    parser.add_argument("--risk", action="store_true", help="Include risk-focused details.")
    parser.add_argument("--show-fields", action="store_true", help="Show changed field paths without printing values.")
    parser.add_argument(
        "--group-by",
        choices=["action", "provider", "module", "risk"],
        default="action",
        help="Group plan changes in the rendered output.",
    )
    parser.add_argument(
        "--fail-on",
        help="Exit with code 2 when actions or risk levels are present, e.g. delete,replace,high.",
    )


def add_output_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--format",
        choices=["text", "markdown", "json"],
        default="text",
        help="Output format.",
    )
    parser.add_argument("--output", help="Write output to a file instead of stdout.")


def add_review_output_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--format",
        choices=["text", "markdown", "github", "json"],
        default="text",
        help="Output format.",
    )
    parser.add_argument("--output", help="Write output to a file instead of stdout.")


def add_ai_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--ai", action="store_true", help="Append an AI-assisted explanation. Sends analysis data to the selected provider.")
    parser.add_argument(
        "--provider",
        choices=["openai", "claude", "azure-openai", "ollama"],
        default="openai",
        help="AI provider.",
    )
    parser.add_argument("--model", help="AI model name or Azure deployment name.")


def main(argv: list[str] | None = None) -> int:
    actual_argv = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()

    if not actual_argv:
        if not sys.stdin.isatty():
            return explain_plan_from_stdin()
        parser.print_help(sys.stderr)
        return 1

    args = parser.parse_args(actual_argv)

    try:
        if args.command == "version":
            print(version_info())
            return 0

        if args.command in {"plan", "risk"}:
            analysis = analyze_plan(
                args.path,
                show_fields=args.show_fields,
                stdin_text=read_stdin_if_requested(args.path),
            )
            content = render_plan(analysis, args.format, args.group_by)
            content = apply_ai_if_requested(args, content, "Explain this Terraform plan risk and change summary.")
            write_output(content, args.output)
            return 2 if fail_condition_matches(args.fail_on, analysis.changes) else 0

        if args.command == "code":
            analysis = analyze_code(args.path)
            content = render_code(analysis, args.format)
            content = apply_ai_if_requested(args, content, "Explain this Terraform code analysis and module quality summary.")
            write_output(content, args.output)
            return 0

        if args.command == "explain":
            code_analysis = analyze_code(args.code)
            plan_analysis = analyze_plan(
                args.plan,
                show_fields=args.show_fields,
                stdin_text=read_stdin_if_requested(args.plan),
            )
            content = render_combined(code_analysis, plan_analysis, args.format, args.group_by)
            content = apply_ai_if_requested(args, content, "Explain this combined Terraform code and plan analysis.")
            write_output(content, args.output)
            return 2 if fail_condition_matches(args.fail_on, plan_analysis.changes) else 0

        if args.command == "review":
            if not args.code and not args.plan:
                raise AnalysisError("review requires --code, --plan, or both.")
            code_analysis = analyze_code(args.code) if args.code else None
            plan_analysis = (
                analyze_plan(
                    args.plan,
                    show_fields=args.show_fields,
                    stdin_text=read_stdin_if_requested(args.plan),
                )
                if args.plan
                else None
            )
            content = render_review(code_analysis, plan_analysis, args.format)
            content = apply_ai_if_requested(args, content, "Create a Terraform pull request review summary.")
            write_output(content, args.output)
            return 2 if plan_analysis and fail_condition_matches(args.fail_on, plan_analysis.changes) else 0

        if args.command == "docs":
            analysis = analyze_code(args.path)
            content = render_docs(analysis, args.format)
            write_output(content, args.output)
            return 0

        if args.command == "graph":
            analysis = analyze_code(args.path)
            content = render_graph(analysis, args.format)
            write_output(content, args.output)
            return 0

        if args.command == "init":
            config_path = init_config(args.path, force=args.force)
            print(f"Created {config_path}")
            return 0

    except AnalysisError as exc:
        print(f"tfexplain: {exc}", file=sys.stderr)
        return 1
    except TfExplainError as exc:
        print(f"tfexplain: {exc}", file=sys.stderr)
        return 1

    parser.print_help(sys.stderr)
    return 1


def apply_ai_if_requested(args: argparse.Namespace, content: str, task: str) -> str:
    if getattr(args, "ai", False):
        result = explain_with_ai(
            content=content,
            task=task,
            provider=args.provider,
            model=args.model,
        )
        return append_ai_to_output(content, result, args.format)
    return content


def version_info() -> str:
    return "\n".join(
        [
            f"tfexplain {__version__}",
            __description__,
            f"Package: {__package_shortform__}",
            f"Author: {__author__}",
            f"Company: {__company__}",
            f"Website: {__website__}",
        ]
    )


def cli_info() -> str:
    return (
        f"{__description__}\n"
        f"Package: {__package_shortform__} | Author: {__author__} | "
        f"Company: {__company__} | Website: {__website__}"
    )


def read_stdin_if_requested(path: str) -> str | None:
    if path == "-":
        return sys.stdin.read()
    return None


def explain_plan_from_stdin() -> int:
    try:
        analysis = analyze_plan("-", stdin_text=sys.stdin.read())
        print(render_plan(analysis))
        return 0
    except AnalysisError as exc:
        print(f"tfexplain: {exc}", file=sys.stderr)
        return 1


def write_output(content: str, output_path: str | None) -> None:
    if output_path:
        path = Path(output_path)
        path.write_text(content + "\n", encoding="utf-8")
    else:
        print(content)
