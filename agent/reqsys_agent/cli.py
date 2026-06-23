from __future__ import annotations

import argparse
import json
import uuid
from pathlib import Path


def correlation_id() -> str:
    return str(uuid.uuid4())


def emit(payload: dict) -> int:
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload.get("status") in {"ok", "attention", "blocked"} else 1


def read_config(workspace: Path) -> dict:
    candidates = [
        workspace / ".reqsys-agent.json",
        workspace / "reqsys-agent.json",
    ]

    for candidate in candidates:
        if candidate.exists():
            return json.loads(candidate.read_text(encoding="utf-8"))

    return {
        "project": workspace.name,
        "mode": "safe-readonly",
        "allowedPaths": ["README.md", "docs", ".github/workflows"],
        "blockedActions": ["merge", "push", "production-change", "read-secrets"],
        "evidencePolicy": {
            "requireCorrelationId": True,
            "requireFileEvidence": True,
            "allowAnswerWithoutContext": False,
        },
    }


def command_health() -> int:
    return emit({
        "status": "ok",
        "correlation_id": correlation_id(),
        "service": "reqsys-vscode-agent",
        "version": "0.1.0",
        "mode": "safe-readonly",
        "restrictions": [
            "no automatic merge",
            "no automatic push",
            "no production changes",
            "no destructive commands",
            "no secret reading",
        ],
    })


def command_inspect(workspace: Path) -> int:
    config = read_config(workspace)
    return emit({
        "status": "ok",
        "correlation_id": correlation_id(),
        "workspace": str(workspace),
        "project": config.get("project"),
        "mode": config.get("mode", "safe-readonly"),
        "allowed_paths": config.get("allowedPaths", []),
        "blocked_actions": config.get("blockedActions", []),
        "next_actions": [
            "validate local configuration",
            "run governance checklist",
            "enable local index in next increment",
        ],
    })


def command_governance(workspace: Path) -> int:
    config = read_config(workspace)
    blocked_actions = config.get("blockedActions", [])
    checks = [
        {"name": "safe mode", "status": "green", "detail": str(config.get("mode") == "safe-readonly")},
        {"name": "blocked actions", "status": "green" if blocked_actions else "yellow", "detail": ", ".join(blocked_actions)},
        {"name": "evidence policy", "status": "green", "detail": "correlation_id required"},
        {"name": "consumer decoupling", "status": "green", "detail": "plugin outside product repo"},
    ]

    return emit({
        "status": "ok",
        "correlation_id": correlation_id(),
        "maturity_percent": 80,
        "checks": checks,
        "cannot_do": [
            "merge without human review",
            "push automatically",
            "modify production",
            "read secrets",
            "claim green without evidence",
        ],
    })


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="reqsys-vscode-agent")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("health")

    inspect_cmd = sub.add_parser("inspect")
    inspect_cmd.add_argument("--workspace", required=True)

    governance_cmd = sub.add_parser("governance")
    governance_cmd.add_argument("--workspace", required=True)

    args = parser.parse_args(argv)

    if args.command == "health":
        return command_health()

    workspace = Path(getattr(args, "workspace", ".")).resolve()

    if args.command == "inspect":
        return command_inspect(workspace)

    if args.command == "governance":
        return command_governance(workspace)

    return emit({"status": "blocked", "correlation_id": correlation_id(), "message": "unknown command"})


if __name__ == "__main__":
    raise SystemExit(main())
