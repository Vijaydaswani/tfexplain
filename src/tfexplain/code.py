from __future__ import annotations

import re
from pathlib import Path

from .errors import AnalysisError
from .models import CodeAnalysis, CodeFinding, TfBlock, display_path
from .risk import is_sensitive_resource

BLOCK_HEADER = re.compile(
    r'(?m)^\s*(resource|data|module|variable|output|provider|locals|terraform)\s*((?:"[^"]+"\s*)*)\{'
)
ATTR_RE = r'(?m)^\s*{name}\s*=\s*("[^"]*"|[^\n#]+)'


def analyze_code(path: str | Path) -> CodeAnalysis:
    root = Path(path).resolve()
    if not root.exists():
        raise AnalysisError(f"Code path not found: {root}")
    if not root.is_dir():
        raise AnalysisError(f"Code path must be a directory: {root}")

    tf_files = terraform_files(root)
    blocks: list[TfBlock] = []
    for file_path in tf_files:
        blocks.extend(parse_blocks(file_path, root))

    providers: set[str] = set()
    required_providers: set[str] = set()
    inferred_providers: set[str] = set()
    required_version: str | None = None
    backends: set[str] = set()
    modules: list[dict[str, str | None]] = []
    resources: list[dict[str, str | None]] = []
    data_sources: list[dict[str, str | None]] = []
    variables: list[dict[str, str | bool | int | None]] = []
    outputs: list[dict[str, str | bool | int | None]] = []
    locals_count = 0
    findings: list[CodeFinding] = []

    for block in blocks:
        if block.kind == "provider" and block.labels:
            providers.add(block.labels[0])
        elif block.kind == "terraform":
            required_version = required_version or attr_value(block.body, "required_version")
            backends.update(re.findall(r'(?m)^\s*backend\s+"([^"]+)"\s*\{', block.body))
            required_providers.update(required_provider_names(block.body))
        elif block.kind == "module" and block.labels:
            modules.append(
                {
                    "name": block.labels[0],
                    "source": attr_value(block.body, "source"),
                    "file": block.file,
                    "line": str(block.line),
                }
            )
        elif block.kind == "resource" and len(block.labels) >= 2:
            resource_type = block.labels[0]
            provider = provider_from_resource_type(resource_type)
            if provider:
                inferred_providers.add(provider)
            resource = {
                "type": resource_type,
                "name": block.labels[1],
                "provider": provider,
                "file": block.file,
                "line": str(block.line),
            }
            resources.append(resource)
            if is_sensitive_resource(resource_type, f"{resource_type}.{block.labels[1]}"):
                findings.append(
                    CodeFinding(
                        level="high",
                        message="Resource type usually deserves reviewer attention.",
                        target=f"{resource_type}.{block.labels[1]}",
                        file=block.file,
                        line=block.line,
                    )
                )
        elif block.kind == "data" and len(block.labels) >= 2:
            provider = provider_from_resource_type(block.labels[0])
            if provider:
                inferred_providers.add(provider)
            data_sources.append(
                {
                    "type": block.labels[0],
                    "name": block.labels[1],
                    "provider": provider,
                    "file": block.file,
                    "line": str(block.line),
                }
            )
        elif block.kind == "variable" and block.labels:
            has_description = has_attr(block.body, "description")
            has_validation = bool(re.search(r'(?m)^\s*validation\s*\{', block.body))
            variables.append(
                {
                    "name": block.labels[0],
                    "type": attr_value(block.body, "type"),
                    "has_default": has_attr(block.body, "default"),
                    "has_description": has_description,
                    "has_validation": has_validation,
                    "file": block.file,
                    "line": block.line,
                }
            )
            if not has_description:
                findings.append(
                    CodeFinding(
                        level="medium",
                        message="Variable is missing a description.",
                        target=f"var.{block.labels[0]}",
                        file=block.file,
                        line=block.line,
                    )
                )
            if not has_validation:
                findings.append(
                    CodeFinding(
                        level="low",
                        message="Variable has no validation block.",
                        target=f"var.{block.labels[0]}",
                        file=block.file,
                        line=block.line,
                    )
                )
        elif block.kind == "output" and block.labels:
            has_description = has_attr(block.body, "description")
            outputs.append(
                {
                    "name": block.labels[0],
                    "has_description": has_description,
                    "file": block.file,
                    "line": block.line,
                }
            )
            if not has_description:
                findings.append(
                    CodeFinding(
                        level="low",
                        message="Output is missing a description.",
                        target=f"output.{block.labels[0]}",
                        file=block.file,
                        line=block.line,
                    )
                )
        elif block.kind == "locals":
            locals_count += len(re.findall(r"(?m)^\s*[A-Za-z_][A-Za-z0-9_]*\s*=", block.body))

    if not tf_files:
        findings.append(
            CodeFinding(
                level="medium",
                message="No Terraform .tf files were found.",
                target=root.as_posix(),
            )
        )

    has_readme = any((root / name).exists() for name in ["README.md", "README.markdown", "readme.md"])
    has_examples = (root / "examples").is_dir() or (root / "example").is_dir()
    has_variables_tf = (root / "variables.tf").exists()
    has_outputs_tf = (root / "outputs.tf").exists()

    if not has_readme:
        findings.append(CodeFinding(level="medium", message="README is missing.", target=root.as_posix()))
    if variables and not has_variables_tf:
        findings.append(CodeFinding(level="low", message="Variables exist but variables.tf is missing.", target=root.as_posix()))
    if outputs and not has_outputs_tf:
        findings.append(CodeFinding(level="low", message="Outputs exist but outputs.tf is missing.", target=root.as_posix()))
    if modules and not has_examples:
        findings.append(CodeFinding(level="low", message="Module examples directory is missing.", target=root.as_posix()))
    external_inferred_providers = inferred_providers - {"terraform"}
    if (providers or external_inferred_providers) and not required_providers:
        findings.append(CodeFinding(level="low", message="required_providers block was not found.", target=root.as_posix()))
    if tf_files and not required_version:
        findings.append(CodeFinding(level="low", message="required_version was not found.", target=root.as_posix()))

    providers.update(inferred_providers)
    providers.update(required_providers)

    return CodeAnalysis(
        path=root.as_posix(),
        terraform_files=[display_path(file_path, root) for file_path in tf_files],
        providers=sorted(providers),
        required_providers=sorted(required_providers),
        required_version=required_version,
        backends=sorted(backends),
        modules=modules,
        resources=resources,
        data_sources=data_sources,
        variables=variables,
        outputs=outputs,
        locals_count=locals_count,
        has_readme=has_readme,
        has_examples=has_examples,
        has_variables_tf=has_variables_tf,
        has_outputs_tf=has_outputs_tf,
        findings=findings,
    )


def terraform_files(root: Path) -> list[Path]:
    ignored = {".terraform", ".git", ".venv", "venv", "__pycache__"}
    files: list[Path] = []
    for path in root.rglob("*.tf"):
        if any(part in ignored for part in path.parts):
            continue
        files.append(path)
    return sorted(files)


def parse_blocks(path: Path, root: Path) -> list[TfBlock]:
    original = path.read_text(encoding="utf-8")
    clean = strip_comments_preserve_layout(original)
    blocks: list[TfBlock] = []

    for match in BLOCK_HEADER.finditer(clean):
        brace_index = match.end() - 1
        end_index = find_matching_brace(clean, brace_index)
        if end_index is None:
            continue

        labels = tuple(re.findall(r'"([^"]+)"', match.group(2)))
        body = original[brace_index + 1 : end_index]
        line = clean.count("\n", 0, match.start()) + 1
        blocks.append(
            TfBlock(
                kind=match.group(1),
                labels=labels,
                body=body,
                file=display_path(path, root),
                line=line,
            )
        )

    return blocks


def strip_comments_preserve_layout(text: str) -> str:
    chars = list(text)
    i = 0
    in_string = False
    heredoc_marker: str | None = None

    while i < len(chars):
        current = chars[i]
        next_char = chars[i + 1] if i + 1 < len(chars) else ""

        if heredoc_marker:
            line_start = i
            line_end = text.find("\n", i)
            if line_end == -1:
                line_end = len(chars)
            line = text[line_start:line_end].strip()
            if line == heredoc_marker:
                heredoc_marker = None
            i = line_end + 1
            continue

        if not in_string and current == "<" and text[i : i + 2] == "<<":
            marker_match = re.match(r"<<-?\s*([A-Za-z_][A-Za-z0-9_]*)", text[i:])
            if marker_match:
                heredoc_marker = marker_match.group(1)
            i += 2
            continue

        if current == '"' and (i == 0 or chars[i - 1] != "\\"):
            in_string = not in_string
            i += 1
            continue

        if not in_string and current == "/" and next_char == "/":
            i = blank_until_newline(chars, i)
            continue
        if not in_string and current == "#":
            i = blank_until_newline(chars, i)
            continue
        if not in_string and current == "/" and next_char == "*":
            chars[i] = " "
            chars[i + 1] = " "
            i += 2
            while i + 1 < len(chars) and not (chars[i] == "*" and chars[i + 1] == "/"):
                if chars[i] != "\n":
                    chars[i] = " "
                i += 1
            if i + 1 < len(chars):
                chars[i] = " "
                chars[i + 1] = " "
                i += 2
            continue

        i += 1

    return "".join(chars)


def blank_until_newline(chars: list[str], start: int) -> int:
    i = start
    while i < len(chars) and chars[i] != "\n":
        chars[i] = " "
        i += 1
    return i


def find_matching_brace(text: str, start: int) -> int | None:
    depth = 0
    in_string = False
    i = start

    while i < len(text):
        current = text[i]
        if current == '"' and (i == 0 or text[i - 1] != "\\"):
            in_string = not in_string
        elif not in_string and current == "{":
            depth += 1
        elif not in_string and current == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1

    return None


def attr_value(body: str, name: str) -> str | None:
    match = re.search(ATTR_RE.format(name=re.escape(name)), body)
    if not match:
        return None
    value = match.group(1).strip()
    if value.startswith('"') and value.endswith('"'):
        return value[1:-1]
    return value


def has_attr(body: str, name: str) -> bool:
    return re.search(ATTR_RE.format(name=re.escape(name)), body) is not None


def required_provider_names(body: str) -> set[str]:
    clean = strip_comments_preserve_layout(body)
    match = re.search(r"(?m)^\s*required_providers\s*\{", clean)
    if not match:
        return set()
    brace_index = match.end() - 1
    end_index = find_matching_brace(clean, brace_index)
    if end_index is None:
        return set()
    required_body = clean[brace_index + 1 : end_index]
    return set(re.findall(r"(?m)^\s*([A-Za-z_][A-Za-z0-9_-]*)\s*=\s*\{", required_body))


def provider_from_resource_type(resource_type: str) -> str | None:
    if "_" not in resource_type:
        return None
    return resource_type.split("_", maxsplit=1)[0]
