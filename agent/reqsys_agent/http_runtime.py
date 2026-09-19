from __future__ import annotations

import json
import os
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

SERVICE_NAME = "reqsys-vscode-agent"
SERVICE_VERSION = "0.7.0"
VALID_ENVIRONMENTS = {"dev", "staging", "production"}
SMOKE_PATHS = ["/health", "/ready", "/runtime-deploy", "/runtime-artifact", "/runtime-public"]


def correlation_id() -> str:
    return str(uuid.uuid4())


def normalize_environment(value: str | None) -> str:
    if value in VALID_ENVIRONMENTS:
        return value
    return "dev"


def runtime_setting(primary_name: str, default: str = "") -> str:
    return os.environ.get(primary_name) or default


def normalize_provider(value: str | None) -> str:
    provider = (value or "pc24x7").strip().lower()
    if provider in {"fly.io", "flyio"}:
        return "legacy-flyio"
    return provider or "pc24x7"


def health_payload() -> dict:
    return {
        "status": "ok",
        "correlation_id": correlation_id(),
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "mode": "safe-readonly",
        "runtime": "http",
        "endpoints": SMOKE_PATHS,
    }


def readiness_payload(environment: str) -> dict:
    return {
        "status": "ok",
        "correlation_id": correlation_id(),
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "environment": environment,
        "startup_health": True,
        "production_blocked_without_explicit_approval": True,
    }


def runtime_deploy_payload(environment: str) -> dict:
    return {
        "status": "ok",
        "correlation_id": correlation_id(),
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "domain": "REQSYS#002.RUNTIME_PUBLICO.DEPLOY_RUNTIME",
        "environment": environment,
        "promotion_order": ["dev", "staging", "production"],
        "runtime_routing": {
            "active_policy": "pc24x7-first",
            "flyio_active": False,
            "external_provider_requires_explicit_decision": True,
        },
        "required_gates": ["ci", "container-artifact", "runtime-routing", "http-smoke", "rollback-evidence"],
        "cannot_do": [
            "claim production readiness without HTTP smoke test",
            "publish without selected runtime evidence",
            "bypass explicit approval for production",
            "use legacy Fly.io workflow as active deployment route",
        ],
    }


def runtime_artifact_payload(environment: str) -> dict:
    return {
        "status": "ok",
        "correlation_id": correlation_id(),
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "domain": "REQSYS#002.RUNTIME_PUBLICO.CONTAINER_ARTIFACT",
        "environment": environment,
        "image_name": "reqsys-vscode-agent-runtime",
        "dockerfile": "runtime/Dockerfile.agent",
        "runs_as_non_root": True,
    }


def runtime_public_payload(environment: str) -> dict:
    provider = normalize_provider(runtime_setting("REQSYS_RUNTIME_PROVIDER", "pc24x7"))
    base_url = runtime_setting("REQSYS_PUBLIC_BASE_URL", "http://localhost:8080").rstrip("/")
    return {
        "status": "ok",
        "correlation_id": correlation_id(),
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "domain": "REQSYS#002.RUNTIME_PUBLICO.RUNTIME_ROUTING",
        "environment": environment,
        "target": {
            "provider": provider,
            "base_url": base_url,
            "health_url": f"{base_url}/health",
            "runtime_public_url": f"{base_url}/runtime-public",
        },
        "smoke_paths": SMOKE_PATHS,
        "runtime_configuration": {
            "provider_variable": "REQSYS_RUNTIME_PROVIDER",
            "base_url_variable": "REQSYS_PUBLIC_BASE_URL",
            "flyio_active": False,
            "legacy_flyio_fallback_enabled": False,
        },
        "constraints": [
            "does not configure secrets in code",
            "does not create DNS records automatically",
            "does not claim production without smoke evidence",
            "does not use Fly.io as active route",
        ],
    }


class RuntimeRequestHandler(BaseHTTPRequestHandler):
    server_version = f"ReqSysRuntime/{SERVICE_VERSION}"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        environment = normalize_environment(
            params.get("environment", [os.environ.get("REQSYS_RUNTIME_ENVIRONMENT", "dev")])[0]
        )

        routes = {
            "/": health_payload,
            "/health": health_payload,
            "/ready": lambda: readiness_payload(environment),
            "/runtime-deploy": lambda: runtime_deploy_payload(environment),
            "/runtime-artifact": lambda: runtime_artifact_payload(environment),
            "/runtime-public": lambda: runtime_public_payload(environment),
        }

        handler = routes.get(parsed.path)
        if handler is None:
            self._write_json(HTTPStatus.NOT_FOUND, {
                "status": "blocked",
                "correlation_id": correlation_id(),
                "message": "endpoint not found",
                "path": parsed.path,
            })
            return

        self._write_json(HTTPStatus.OK, handler())

    def log_message(self, format: str, *args: object) -> None:
        print(json.dumps({
            "event": "http_access",
            "client": self.address_string(),
            "message": format % args,
        }, ensure_ascii=False))

    def _write_json(self, status_code: HTTPStatus, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status_code.value)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def serve_runtime(host: str, port: int) -> int:
    server = ThreadingHTTPServer((host, port), RuntimeRequestHandler)
    print(json.dumps({
        "status": "ok",
        "event": "runtime_http_started",
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "host": host,
        "port": port,
    }, ensure_ascii=False))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 0
    finally:
        server.server_close()
    return 0
