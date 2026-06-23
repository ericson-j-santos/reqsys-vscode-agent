from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_ALLOWED_PATHS = ["README.md", "docs", ".github/workflows"]
DEFAULT_BLOCKED_NAMES = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "dist",
    "build",
    "coverage",
    "__pycache__",
    ".reqsys",
}
DEFAULT_BLOCKED_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".ico",
    ".pdf",
    ".zip",
    ".7z",
    ".tar",
    ".gz",
    ".exe",
    ".dll",
    ".so",
    ".pyc",
}
DEFAULT_BLOCKED_FILENAMES = {
    ".env",
    ".env.local",
    ".env.production",
    "id_rsa",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
}


@dataclass(frozen=True)
class WorkspaceFile:
    path: str
    size_bytes: int
    sha256: str
    preview: str
    modified_at: str


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_config(workspace: Path) -> dict[str, Any]:
    candidates = [workspace / ".reqsys-agent.json", workspace / "reqsys-agent.json"]
    for candidate in candidates:
        if candidate.exists():
            return json.loads(candidate.read_text(encoding="utf-8"))
    return {
        "project": workspace.name,
        "mode": "safe-readonly",
        "allowedPaths": DEFAULT_ALLOWED_PATHS,
        "blockedActions": ["merge", "push", "production-change", "read-secrets"],
        "evidencePolicy": {
            "requireCorrelationId": True,
            "requireFileEvidence": True,
            "allowAnswerWithoutContext": False,
        },
    }


def _is_relative_to(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def _is_blocked(path: Path) -> bool:
    if any(part in DEFAULT_BLOCKED_NAMES for part in path.parts):
        return True
    if path.name in DEFAULT_BLOCKED_FILENAMES:
        return True
    if path.suffix.lower() in DEFAULT_BLOCKED_SUFFIXES:
        return True
    return False


def _safe_preview(content: str, max_chars: int) -> str:
    compact = "\n".join(line.rstrip() for line in content.splitlines()[:40])
    return compact[:max_chars]


def discover_files(workspace: Path, config: dict[str, Any], max_files: int = 200, max_bytes: int = 120_000) -> list[WorkspaceFile]:
    workspace = workspace.resolve()
    allowed_paths = config.get("allowedPaths") or DEFAULT_ALLOWED_PATHS
    discovered: list[WorkspaceFile] = []

    for allowed in allowed_paths:
        root = (workspace / str(allowed)).resolve()
        if not root.exists() or not _is_relative_to(root, workspace):
            continue

        candidates = [root] if root.is_file() else sorted(p for p in root.rglob("*") if p.is_file())
        for candidate in candidates:
            if len(discovered) >= max_files:
                return discovered
            if not _is_relative_to(candidate, workspace) or _is_blocked(candidate):
                continue
            stat = candidate.stat()
            if stat.st_size > max_bytes:
                continue
            try:
                raw = candidate.read_bytes()
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                continue

            rel_path = candidate.relative_to(workspace).as_posix()
            discovered.append(
                WorkspaceFile(
                    path=rel_path,
                    size_bytes=stat.st_size,
                    sha256=hashlib.sha256(raw).hexdigest(),
                    preview=_safe_preview(text, max_chars=2_000),
                    modified_at=datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                )
            )

    return discovered


def build_index(workspace: Path) -> dict[str, Any]:
    config = read_config(workspace)
    files = discover_files(workspace, config)
    index = {
        "schema_version": "0.2.0",
        "generated_at": utc_now(),
        "project": config.get("project", workspace.name),
        "mode": config.get("mode", "safe-readonly"),
        "workspace": str(workspace.resolve()),
        "file_count": len(files),
        "files": [file.__dict__ for file in files],
        "restrictions": [
            "safe-readonly",
            "allowed paths only",
            "sensitive names blocked",
            "binary files ignored",
            "large files skipped",
        ],
    }

    output_dir = workspace / ".reqsys"
    output_dir.mkdir(exist_ok=True)
    (output_dir / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")
    return index


def load_index(workspace: Path) -> dict[str, Any] | None:
    index_path = workspace / ".reqsys" / "index.json"
    if not index_path.exists():
        return None
    return json.loads(index_path.read_text(encoding="utf-8"))


def ask_index(workspace: Path, question: str) -> dict[str, Any]:
    index = load_index(workspace)
    if index is None:
        index = build_index(workspace)

    terms = [term.lower() for term in question.replace("?", " ").replace(",", " ").split() if len(term) >= 3]
    matches: list[dict[str, Any]] = []
    for file in index.get("files", []):
        haystack = f"{file.get('path', '')}\n{file.get('preview', '')}".lower()
        score = sum(1 for term in terms if term in haystack)
        if score > 0:
            matches.append({
                "path": file.get("path"),
                "score": score,
                "sha256": file.get("sha256"),
                "preview": file.get("preview", "")[:700],
            })

    matches.sort(key=lambda item: (-int(item["score"]), str(item["path"])))
    return {
        "question": question,
        "answer_mode": "local-index-keyword",
        "file_count": index.get("file_count", 0),
        "matches": matches[:10],
        "limitations": [
            "no LLM used",
            "keyword matching only",
            "answers must be validated against file evidence",
        ],
    }
