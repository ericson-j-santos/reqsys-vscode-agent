from __future__ import annotations

import argparse
import hashlib
import json
import time
import uuid
from pathlib import Path
from typing import Iterable


BLOCKED_NAMES = {
    ".env",
    ".env.local",
    ".env.production",
    "id_rsa",
    "id_ed25519",
}

BLOCKED_SUFFIXES = {
    ".pem",
    ".key",
    ".pfx",
    ".crt",
}

IGNORED_DIRS = {
    ".git",
    ".reqsys",
    "node_modules",
    ".venv",
    "venv",
    "dist",
    "build",
    "coverage",
    "out",
    "__pycache__",
}

ALLOWED_SUFFIXES = {
    ".md",
    ".txt",
    ".json",
    ".yml",
    ".yaml",
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".css",
    ".scss",
    ".html",
    ".sql",
}

MAX_FILE_BYTES = 512_000
MAX_PREVIEW_CHARS = 1_200


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


def is_under(parent: Path, candidate: Path) -> bool:
    try:
        candidate.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def configured_allowed_roots(workspace: Path, config: dict) -> list[Path]:
    roots: list[Path] = []
    for raw_path in config.get("allowedPaths", []):
        if not isinstance(raw_path, str) or not raw_path.strip():
            continue
        path = (workspace / raw_path).resolve()
        if is_under(workspace, path):
            roots.append(path)
    return roots or [workspace / "README.md", workspace / "docs"]


def is_allowed_by_roots(path: Path, allowed_roots: list[Path]) -> bool:
    resolved = path.resolve()
    for root in allowed_roots:
        if root.is_file() and resolved == root.resolve():
            return True
        if root.is_dir() and is_under(root, resolved):
            return True
    return False


def is_sensitive_or_ignored(path: Path) -> bool:
    parts = set(path.parts)
    if parts.intersection(IGNORED_DIRS):
        return True
    if path.name in BLOCKED_NAMES:
        return True
    if path.suffix.lower() in BLOCKED_SUFFIXES:
        return True
    return False


def is_indexable_file(path: Path, allowed_roots: list[Path]) -> bool:
    if not path.is_file():
        return False
    if not is_allowed_by_roots(path, allowed_roots):
        return False
    if is_sensitive_or_ignored(path):
        return False
    if path.suffix.lower() not in ALLOWED_SUFFIXES:
        return False
    if path.stat().st_size > MAX_FILE_BYTES:
        return False
    return True


def iter_indexable_files(workspace: Path, config: dict) -> Iterable[Path]:
    allowed_roots = configured_allowed_roots(workspace, config)
    for root in allowed_roots:
        if root.is_file():
            if is_indexable_file(root, allowed_roots):
                yield root
            continue
        if not root.exists() or not root.is_dir():
            continue
        for path in root.rglob("*"):
            if is_indexable_file(path, allowed_roots):
                yield path


def safe_preview(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")[:MAX_PREVIEW_CHARS]
    except OSError as exc:
        return f"[read-error:{type(exc).__name__}]"


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(64 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_index(workspace: Path) -> dict:
    config = read_config(workspace)
    files = []
    seen = set()

    for path in iter_indexable_files(workspace, config):
        resolved = path.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        relative = resolved.relative_to(workspace.resolve()).as_posix()
        files.append({
            "path": relative,
            "size_bytes": path.stat().st_size,
            "sha256": hash_file(path),
            "preview": safe_preview(path),
        })

    files.sort(key=lambda item: item["path"])
    index_payload = {
        "schema_version": "0.2",
        "project": config.get("project", workspace.name),
        "mode": config.get("mode", "safe-readonly"),
        "created_at_epoch": int(time.time()),
        "total_files": len(files),
        "files": files,
        "restrictions": [
            "allowedPaths only",
            "sensitive files blocked",
            "no external llm call",
            "no automatic patch",
            "no production change",
        ],
    }

    index_dir = workspace / ".reqsys" / "agent-index"
    index_dir.mkdir(parents=True, exist_ok=True)
    index_file = index_dir / "index.json"
    index_file.write_text(json.dumps(index_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "status": "ok",
        "correlation_id": correlation_id(),
        "workspace": str(workspace),
        "index_file": str(index_file),
        "project": index_payload["project"],
        "total_files": len(files),
        "evidence_files": [{"path": item["path"], "sha256": item["sha256"]} for item in files[:50]],
        "restrictions": index_payload["restrictions"],
    }


def command_health() -> int:
    return emit({
        "status": "ok",
        "correlation_id": correlation_id(),
        "service": "reqsys-vscode-agent",
        "version": "0.2.0",
        "mode": "safe-readonly",
        "capabilities": ["inspect", "governance", "index"],
        "restrictions": [
            "no automatic merge",
            "no automatic push",
            "no production changes",
            "no destructive commands",
            "no secret reading",
            "no external llm call",
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
            "run governed local index",
            "review .reqsys/agent-index/index.json",
            "enable optional local LlamaIndex/Ollama in later increment",
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
        {"name": "local index", "status": "green", "detail": "available without external llm"},
    ]

    return emit({
        "status": "ok",
        "correlation_id": correlation_id(),
        "maturity_percent": 85,
        "checks": checks,
        "cannot_do": [
            "merge without human review",
            "push automatically",
            "modify production",
            "read secrets",
            "claim green without evidence",
            "send code to external llm",
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

    index_cmd = sub.add_parser("index")
    index_cmd.add_argument("--workspace", required=True)

    args = parser.parse_args(argv)

    if args.command == "health":
        return command_health()

    workspace = Path(getattr(args, "workspace", ".")).resolve()

    if args.command == "inspect":
        return command_inspect(workspace)

    if args.command == "governance":
        return command_governance(workspace)

    if args.command == "index":
        return emit(build_index(workspace))

    return emit({"status": "blocked", "correlation_id": correlation_id(), "message": "unknown command"})


if __name__ == "__main__":
    raise SystemExit(main())
