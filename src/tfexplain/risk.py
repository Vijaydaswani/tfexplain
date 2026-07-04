from __future__ import annotations

from collections.abc import Iterable

RISK_LEVELS = ["info", "low", "medium", "high", "critical"]
ACTION_ORDER = ["create", "update", "replace", "delete", "read", "no-op"]

SENSITIVE_RESOURCE_HINTS = {
    "access_key",
    "acl",
    "aks",
    "app_service",
    "application_gateway",
    "authorization",
    "backup",
    "bucket",
    "certificate",
    "cluster",
    "database",
    "db",
    "dns",
    "eks",
    "firewall",
    "gke",
    "iam",
    "identity",
    "key",
    "key_vault",
    "kms",
    "kubernetes",
    "lb",
    "load_balancer",
    "mysql",
    "network",
    "policy",
    "postgres",
    "postgresql",
    "public_ip",
    "rds",
    "redis",
    "role",
    "route",
    "security_group",
    "sql",
    "storage",
    "subnet",
    "vault",
    "vpc",
}


def normalize_action(actions: Iterable[str] | None) -> str:
    action_set = list(actions or [])
    if not action_set:
        return "unknown"
    if action_set in (["delete", "create"], ["create", "delete"]):
        return "replace"
    if len(action_set) == 1:
        return action_set[0]
    if "delete" in action_set and "create" in action_set:
        return "replace"
    if "update" in action_set:
        return "update"
    return "+".join(action_set)


def risk_level_from_score(score: int) -> str:
    if score <= 0:
        return "info"
    if score <= 2:
        return "low"
    if score <= 5:
        return "medium"
    if score <= 8:
        return "high"
    return "critical"


def risk_rank(level: str) -> int:
    try:
        return RISK_LEVELS.index(level)
    except ValueError:
        return 0


def highest_risk(levels: Iterable[str]) -> str:
    return max(levels, key=risk_rank, default="info")


def is_sensitive_resource(resource_type: str, address: str = "") -> bool:
    haystack = f"{resource_type} {address}".lower()
    normalized = haystack.replace("-", "_").replace(".", "_")
    return any(hint in normalized for hint in SENSITIVE_RESOURCE_HINTS)


def score_resource_change(action: str, resource_type: str, address: str) -> tuple[int, list[str]]:
    score = {
        "no-op": 0,
        "read": 0,
        "create": 1,
        "update": 2,
        "delete": 5,
        "replace": 6,
    }.get(action, 1)
    reasons: list[str] = []

    if action == "delete":
        reasons.append("Resource deletion removes existing infrastructure.")
    elif action == "replace":
        reasons.append("Resource replacement deletes and recreates infrastructure.")
    elif action == "update":
        reasons.append("Resource will be changed in place.")
    elif action == "create":
        reasons.append("New infrastructure will be created.")

    if is_sensitive_resource(resource_type, address):
        score += 2
        reasons.append("Resource type is commonly sensitive for security, reliability, or availability.")

    return score, reasons


def fail_condition_matches(fail_on: str | None, changes: Iterable[object]) -> bool:
    if not fail_on:
        return False

    tokens = {token.strip().lower() for token in fail_on.split(",") if token.strip()}
    if not tokens:
        return False

    for change in changes:
        action = getattr(change, "action", "")
        level = getattr(change, "risk_level", "info")
        if action in tokens:
            return True
        for token in tokens:
            if token in RISK_LEVELS and risk_rank(level) >= risk_rank(token):
                return True
    return False
