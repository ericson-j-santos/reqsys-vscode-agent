from __future__ import annotations

import json
import os
import uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

SERVICE_NAME = "reqsys-vscode-agent"
SERVICE_VERSION = "0.6.0"
VALID_ENVIRONMENTS = {"dev", "staging", "production"}


def correlation_id() -> str:
    return str(uuid.uuid4())


def normalize_environment(value: str | None) -> str:
    if value in VALID_ENVIRONMENTS:
        return value
    return "dev"


def health_payload() -> dict:
    return {
        "status": "ok",
        "correlation_id": correlation_id(),
        "service": SERVICE_NAME,
        "version": SERVICE_VERSION,
        "mode": "safe-readonly",
        "runtime": "http",
        "endpoints": ["/health", "/ready", "/runtime-deploy", "/runtime-artifact", "/runtime-public"],
    }


def readiness_payload(environment: str) -> dict:
    return {
        "status": "ok",
        "correlation_id": correlation_id(),
        "service": SERVICE_NAME,
        "environment": environment,
        "startup_health": True,
        "production_blocked_without_workflow_dispatch": True,
    }


def runtime_deploy_payload(environment: str) -> dict:
    return {
        "status": "ok",
        "correlation_id": correlation_id(),
        "service": SERVICE_NAME,
        "domain": "REQSYS#002.RUNTIME_PUBLICO.DEPLOY_RUNTIME",
        "environment": environment,
        "promotion_order": ["dev", "staging", "production"],
        "required_gates": ["ci", "container-artifact", "fly-deploy", "http-smoke", "rollback-evidence"],
        "cannot_do": [
            "claim production readiness without HTTP smoke test",
            "publish without FLY_API_TOKEN",
            "bypass workflow_dispatch for production",
        ],
    }


def runtime_artifact_payload(environment: str) -> dict:
    return {
        "status": "ok",
        "correlation_id": correlation_id(),
        "service": SERVICE_NAME,
        "domain": "REQSYS#002.RUNTIME_PUBLICO.CONTAINER_ARTIFACT",
        "environment": environment,
        "image_name": "reqsys-vscode-agent-runtime",
        "dockerfile": "runtime/Dockerfile.agent",
        "runs_as_non_root": True,
    }


def runtime_public_payload(environment: str) -> dict:
    fly_app_name = os.environ.get("FLY_APP_NAME", "reqsys-vscode-agent")
    duckdns_hostname = os.environ.get("DUCKDNS_HOSTNAME", "")
    duckdns_url = f"https://{duckdns_hostname}" if duckdns_hostname else None
    return {
        "status": "ok",
        "correlation_id": correlation_id(),
        "service": SERVICE_NAME,
        "domain": "REQSYS#002.RUNTIME_PUBLICO.FLYIO_DUCKDNS",
        "environment": environment,
        "fly_app_name": fly_app_name,
        "fly_url": f"https://{fly_app_name}.fly.dev",
        "duckdns_hostname": duckdns_hostname or None,
        "duckdns_url": duckdns_url,
        "smoke_paths": ["/health", "/ready", "/runtime-deploy", "/runtime-artifact"],
        "cost_guard": {
            "auto_stop_machines": "stop",
            "auto_start_machines": True,
            "min_machines_running": 0,
            "no_paid_database": True,
            "no_volume_required": True,
        },
        "constraints": [
            "does not configure secrets in code",
            "does not create DNS records automatically",
            "does not claim production without smoke evidence",
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
