from __future__ import annotations

import argparse
import json
import uuid
from pathlib import Path

from reqsys_agent.semantic_search import semantic_search
from reqsys_agent.workspace_reader import ask_index, build_index, read_config


def correlation_id() -> str:
    return str(uuid.uuid4())


def emit(payload: dict) -> int:
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if payload.get("status") in {"ok", "attention", "blocked"} else 1


def command_health() -> int:
    return emit({
        "status": "ok",
        "correlation_id": correlation_id(),
        "service": "reqsys-vscode-agent",
        "version": "0.3.0",
        "mode": "safe-readonly",
        "capabilities": [
            "workspace inspection",
            "governance checklist",
            "local context index",
            "keyword-based local questions",
            "lightweight semantic local search",
        ],
        "restrictions": [
            "no automatic merge",
            "no automatic push",
            "no production changes",
            "no destructive commands",
            "no secret reading",
            "no external LLM required",
            "no vector database required",
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
            "build local context index",
            "ask keyword-based questions",
            "ask semantic local questions",
            "enable optional LlamaIndex/Ollama in future increment",
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
        {"name": "local context index", "status": "green", "detail": "available without LLM"},
        {"name": "semantic local search", "status": "green", "detail": "TF-IDF/cosine without external services"},
    ]

    return emit({
        "status": "ok",
        "correlation_id": correlation_id(),
        "maturity_percent": 88,
        "checks": checks,
        "cannot_do": [
            "merge without human review",
            "push automatically",
            "modify production",
            "read secrets",
            "claim green without evidence",
            "answer without local context when evidence is required",
            "treat TF-IDF ranking as full LLM reasoning",
        ],
    })


def command_build_index(workspace: Path) -> int:
    index = build_index(workspace)
    return emit({
        "status": "ok",
        "correlation_id": correlation_id(),
        "workspace": str(workspace),
        "project": index.get("project"),
        "file_count": index.get("file_count", 0),
        "index_path": str((workspace / ".reqsys" / "index.json").resolve()),
        "restrictions": index.get("restrictions", []),
    })


def command_ask(workspace: Path, question: str) -> int:
    result = ask_index(workspace, question)
    return emit({
        "status": "ok" if result.get("matches") else "attention",
        "correlation_id": correlation_id(),
        "workspace": str(workspace),
        **result,
    })


def command_semantic_ask(workspace: Path, question: str) -> int:
    result = semantic_search(workspace, question)
    return emit({
        "status": "ok" if result.get("matches") else "attention",
        "correlation_id": correlation_id(),
        "workspace": str(workspace),
        **result,
    })


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="reqsys-vscode-agent")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("health")

    inspect_cmd = sub.add_parser("inspect")
    inspect_cmd.add_argument("--workspace", required=True)

    governance_cmd = sub.add_parser("governance")
    governance_cmd.add_argument("--workspace", required=True)

    build_index_cmd = sub.add_parser("build-index")
    build_index_cmd.add_argument("--workspace", required=True)

    ask_cmd = sub.add_parser("ask")
    ask_cmd.add_argument("--workspace", required=True)
    ask_cmd.add_argument("--question", required=True)

    semantic_ask_cmd = sub.add_parser("semantic-ask")
    semantic_ask_cmd.add_argument("--workspace", required=True)
    semantic_ask_cmd.add_argument("--question", required=True)

    args = parser.parse_args(argv)

    if args.command == "health":
        return command_health()

    workspace = Path(getattr(args, "workspace", ".")).resolve()

    if args.command == "inspect":
        return command_inspect(workspace)

    if args.command == "governance":
        return command_governance(workspace)

    if args.command == "build-index":
        return command_build_index(workspace)

    if args.command == "ask":
        return command_ask(workspace, args.question)

    if args.command == "semantic-ask":
        return command_semantic_ask(workspace, args.question)

    return emit({"status": "blocked", "correlation_id": correlation_id(), "message": "unknown command"})


if __name__ == "__main__":
    raise SystemExit(main())
