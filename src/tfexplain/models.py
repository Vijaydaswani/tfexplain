from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ResourceChange:
    address: str
    action: str
    resource_type: str
    name: str
    provider: str
    module: str | None
    risk_level: str
    risk_score: int
    reasons: list[str] = field(default_factory=list)
    replace_paths: list[str] = field(default_factory=list)
    changed_fields: list[str] = field(default_factory=list)
    unknown_fields: list[str] = field(default_factory=list)


@dataclass
class PlanAnalysis:
    path: str
    format_version: str | None
    terraform_version: str | None
    counts: dict[str, int]
    risk_level: str
    risk_score: int
    changes: list[ResourceChange]

    def high_attention(self) -> list[ResourceChange]:
        return [
            change
            for change in self.changes
            if change.risk_level in {"high", "critical"} or change.action in {"delete", "replace"}
        ]

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["high_attention"] = [asdict(change) for change in self.high_attention()]
        return result


@dataclass
class TfBlock:
    kind: str
    labels: tuple[str, ...]
    body: str
    file: str
    line: int

    @property
    def address(self) -> str:
        if self.kind in {"resource", "data"} and len(self.labels) >= 2:
            return f"{self.kind}.{self.labels[0]}.{self.labels[1]}"
        if self.labels:
            return f"{self.kind}.{'.'.join(self.labels)}"
        return self.kind


@dataclass
class CodeFinding:
    level: str
    message: str
    target: str
    file: str | None = None
    line: int | None = None


@dataclass
class CodeAnalysis:
    path: str
    terraform_files: list[str]
    providers: list[str]
    required_providers: list[str]
    required_version: str | None
    backends: list[str]
    modules: list[dict[str, str | None]]
    resources: list[dict[str, str | None]]
    data_sources: list[dict[str, str | None]]
    variables: list[dict[str, str | bool | int | None]]
    outputs: list[dict[str, str | bool | int | None]]
    locals_count: int
    has_readme: bool
    has_examples: bool
    has_variables_tf: bool
    has_outputs_tf: bool
    findings: list[CodeFinding] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def display_path(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()
