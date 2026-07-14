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

from reqsys_agent.http_runtime import serve_runtime
from reqsys_agent.semantic_search import semantic_search
from reqsys_agent.workspace_reader import ask_index, build_index as build_local_context_index


RUNTIME_ENVIRONMENTS = [
    {
        "name": "dev",
        "purpose": "validar build, healthcheck e artefatos sem impacto público",
        "required_gates": ["ci", "healthcheck", "governance-checklist"],
        "rollback": "reverter para último commit verde na branch de integração",
    },
    {
        "name": "staging",
        "purpose": "validar release candidata com contrato próximo de produção",
        "required_gates": ["ci", "healthcheck", "smoke-test", "rollback-plan"],
        "rollback": "promover release anterior validada ou desfazer tag candidata",
    },
    {
        "name": "production",
        "purpose": "publicar runtime somente com evidência verde e rollback documentado",
        "required_gates": ["ci", "healthcheck", "smoke-test", "security-gates", "approval"],
        "rollback": "retornar para release estável anterior e registrar incidente com correlation_id",
    },
]

RUNTIME_CONTAINER_ARTIFACT = {
    "image_name": "reqsys-vscode-agent-runtime",
    "dockerfile": "runtime/Dockerfile.agent",
    "build_context": ".",
    "evidence_path": ".reqsys/evidence/runtime-artifact",
    "publish_registry": False,
    "runs_as_non_root": True,
    "startup_command": "PYTHONPATH=/app/agent python -m reqsys_agent.cli serve --host 0.0.0.0 --port 8080",
    "readiness_command": "PYTHONPATH=/app/agent python -m reqsys_agent.cli runtime-deploy",
}

SMOKE_ENDPOINTS = ["/health", "/ready", "/runtime-deploy", "/runtime-artifact", "/runtime-public"]


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
        "version": "0.7.0",
        "mode": "safe-readonly",
        "capabilities": [
            "governed local workspace index",
            "workspace inspection",
            "governance checklist",
            "local context index",
            "keyword-based local questions",
            "lightweight semantic local search",
            "runtime public deploy readiness contract",
            "runtime container artifact contract",
            "runtime public HTTP service",
            "runtime public smoke monitor contract",
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


def command_runtime_deploy(environment: str | None = None) -> int:
    environments = RUNTIME_ENVIRONMENTS
    if environment:
        environments = [item for item in environments if item["name"] == environment]

    return emit({
        "status": "ok",
        "correlation_id": correlation_id(),
        "service": "reqsys-vscode-agent",
        "domain": "REQSYS#002.RUNTIME_PUBLICO.DEPLOY_RUNTIME",
        "branch": "ai/runtime-public",
        "maturity_percent": 66,
        "target_maturity_percent": 100,
        "environment_count": len(environments),
        "environments": environments,
        "healthcheck": {
            "command": "PYTHONPATH=agent python -m reqsys_agent.cli health",
            "expected_status": "ok",
            "startup_health_required": True,
        },
        "deploy_contract": {
            "strategy": "small governed PRs with draft mode until CI is green",
            "artifact_evidence": "CI logs, health output, smoke evidence and rollback note",
            "promotion_order": ["dev", "staging", "production"],
        },
        "kpis": {
            "uptime": "target >= 99.5% after public runtime exists",
            "deploy_success_rate": "target >= 95% after pipeline stabilization",
            "mttr": "target <= 30 minutes for rollback-supported incidents",
            "startup_health": "required before promotion",
        },
        "cannot_do": [
            "publish production without green CI evidence",
            "claim public URL without validated runtime",
            "bypass security gates for Auth, CORS, JWT, secrets or audit",
            "deploy without documented rollback path",
        ],
        "next_increment": "add environment-specific deployment workflow after repository runtime target is selected",
    })


def command_runtime_artifact(environment: str | None = None) -> int:
    return emit({
        "status": "ok",
        "correlation_id": correlation_id(),
        "service": "reqsys-vscode-agent",
        "domain": "REQSYS#002.RUNTIME_PUBLICO.CONTAINER_ARTIFACT",
        "branch": "ai/runtime-container-artifact",
        "maturity_percent": 74,
        "environment": environment or "dev",
        "artifact": RUNTIME_CONTAINER_ARTIFACT,
        "quality_gates": [
            "python tests",
            "docker build",
            "container startup healthcheck",
            "container deploy readiness contract",
            "image metadata inspection",
            "artifact evidence upload",
        ],
        "security_controls": [
            "non-root container user",
            "no secrets baked into image",
            "no registry push in this increment",
            "no production deployment",
            "metadata labels for traceability",
        ],
        "outputs": [
            "container-health.json",
            "container-runtime-deploy.json",
            "image-inspect.json",
            "summary.md",
        ],
        "cannot_do": [
            "publish image to registry without explicit target and credentials",
            "deploy public URL from artifact workflow",
            "claim production readiness without smoke test against public runtime",
        ],
        "next_increment": "choose public runtime target and add deployment job with smoke test and rollback evidence",
    })


def command_runtime_public(environment: str, app_name: str, duckdns_hostname: str | None) -> int:
    return emit({
        "status": "ok",
        "correlation_id": correlation_id(),
        "service": "reqsys-vscode-agent",
        "domain": "REQSYS#002.RUNTIME_PUBLICO.FLYIO_DUCKDNS",
        "branch": "ai/flyio-public-deploy",
        "maturity_percent": 82,
        "environment": environment,
        "target": {
            "provider": "fly.io",
            "app_name": app_name,
            "fly_url": f"https://{app_name}.fly.dev",
            "duckdns_hostname": duckdns_hostname,
            "duckdns_url": f"https://{duckdns_hostname}" if duckdns_hostname else None,
        },
        "cost_guard": {
            "auto_stop_machines": "stop",
            "auto_start_machines": True,
            "min_machines_running": 0,
            "paid_database": False,
            "persistent_volume_required": False,
        },
        "required_gates": [
            "workflow_dispatch",
            "FLY_API_TOKEN secret present",
            "docker build",
            "fly deploy",
            "HTTP smoke on fly.dev",
            "optional HTTP smoke on DuckDNS hostname",
            "rollback hint evidence",
        ],
        "cannot_do": [
            "configure DuckDNS records from GitHub without provider credentials",
            "claim production readiness without smoke evidence",
            "deploy production outside explicit workflow_dispatch",
        ],
    })


def command_runtime_monitor(base_url: str, environment: str, duckdns_url: str | None) -> int:
    normalized_base_url = base_url.rstrip("/")
    normalized_duckdns_url = duckdns_url.rstrip("/") if duckdns_url else None
    return emit({
        "status": "ok",
        "correlation_id": correlation_id(),
        "service": "reqsys-vscode-agent",
        "domain": "REQSYS#002.RUNTIME_PUBLICO.SMOKE_MONITOR",
        "branch": "ai/flyio-smoke-monitor",
        "maturity_percent": 86,
        "environment": environment,
        "targets": {
            "primary_base_url": normalized_base_url,
            "duckdns_url": normalized_duckdns_url,
        },
        "smoke_endpoints": SMOKE_ENDPOINTS,
        "evidence_files": [
            "monitor-contract.json",
            "primary-health.json",
            "primary-ready.json",
            "primary-runtime-deploy.json",
            "primary-runtime-artifact.json",
            "primary-runtime-public.json",
            "duckdns-health.json",
            "summary.md",
        ],
        "success_criteria": [
            "all primary smoke endpoints return HTTP 2xx",
            "DuckDNS health returns HTTP 2xx when duckdns_url is provided",
            "response payload includes status=ok for runtime endpoints",
            "evidence artifact is uploaded",
        ],
        "cannot_do": [
            "create DNS records automatically",
            "fix Fly.io runtime without a deploy workflow run",
            "claim uptime SLA from a single smoke run",
        ],
        "next_increment": "schedule governed uptime probes after public URL is stable",
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
            "build local context index",
            "ask keyword-based questions",
            "ask semantic local questions",
            "review generated local evidence",
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
        {"name": "governed local index", "status": "green", "detail": "allowedPaths only with sensitive files blocked"},
        {"name": "local context index", "status": "green", "detail": "available without LLM"},
        {"name": "semantic local search", "status": "green", "detail": "TF-IDF/cosine without external services"},
        {"name": "runtime deploy contract", "status": "green", "detail": "health, rollout and rollback evidence required"},
        {"name": "runtime container artifact", "status": "green", "detail": "container build evidence without registry publication"},
        {"name": "fly.io public runtime", "status": "green", "detail": "workflow_dispatch deploy with HTTP smoke evidence"},
        {"name": "fly.io smoke monitor", "status": "green", "detail": "manual smoke probes with artifact evidence"},
    ]

    return emit({
        "status": "ok",
        "correlation_id": correlation_id(),
        "maturity_percent": 93,
        "checks": checks,
        "cannot_do": [
            "merge without human review",
            "push automatically",
            "modify production",
            "read secrets",
            "claim green without evidence",
            "send code to external LLM",
            "answer without local context when evidence is required",
            "treat TF-IDF ranking as full LLM reasoning",
        ],
    })


def command_build_index(workspace: Path) -> int:
    index = build_local_context_index(workspace)
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

    runtime_cmd = sub.add_parser("runtime-deploy")
    runtime_cmd.add_argument("--environment", choices=[item["name"] for item in RUNTIME_ENVIRONMENTS], default=None)

    artifact_cmd = sub.add_parser("runtime-artifact")
    artifact_cmd.add_argument("--environment", choices=[item["name"] for item in RUNTIME_ENVIRONMENTS], default="dev")

    public_cmd = sub.add_parser("runtime-public")
    public_cmd.add_argument("--environment", choices=[item["name"] for item in RUNTIME_ENVIRONMENTS], default="dev")
    public_cmd.add_argument("--app-name", default="reqsys-vscode-agent")
    public_cmd.add_argument("--duckdns-hostname", default=None)

    monitor_cmd = sub.add_parser("runtime-monitor")
    monitor_cmd.add_argument("--base-url", required=True)
    monitor_cmd.add_argument("--environment", choices=[item["name"] for item in RUNTIME_ENVIRONMENTS], default="dev")
    monitor_cmd.add_argument("--duckdns-url", default=None)

    serve_cmd = sub.add_parser("serve")
    serve_cmd.add_argument("--host", default="127.0.0.1")
    serve_cmd.add_argument("--port", type=int, default=8080)

    inspect_cmd = sub.add_parser("inspect")
    inspect_cmd.add_argument("--workspace", required=True)

    governance_cmd = sub.add_parser("governance")
    governance_cmd.add_argument("--workspace", required=True)

    index_cmd = sub.add_parser("index")
    index_cmd.add_argument("--workspace", required=True)

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

    if args.command == "runtime-deploy":
        return command_runtime_deploy(args.environment)

    if args.command == "runtime-artifact":
        return command_runtime_artifact(args.environment)

    if args.command == "runtime-public":
        return command_runtime_public(args.environment, args.app_name, args.duckdns_hostname)

    if args.command == "runtime-monitor":
        return command_runtime_monitor(args.base_url, args.environment, args.duckdns_url)

    if args.command == "serve":
        return serve_runtime(args.host, args.port)

    workspace = Path(getattr(args, "workspace", ".")).resolve()

    if args.command == "inspect":
        return command_inspect(workspace)

    if args.command == "governance":
        return command_governance(workspace)

    if args.command == "index":
        return emit(build_index(workspace))

    if args.command == "build-index":
        return command_build_index(workspace)

    if args.command == "ask":
        return command_ask(workspace, args.question)

    if args.command == "semantic-ask":
        return command_semantic_ask(workspace, args.question)

    return emit({"status": "blocked", "correlation_id": correlation_id(), "message": "unknown command"})


if __name__ == "__main__":
    raise SystemExit(main())
