#!/usr/bin/env python3
"""Validador de evidência runtime↔documentação da Arquitetura Viva.

Owner: IA_DOCUMENTACAO_VIVA
Status: runtime-evidence-local-e2e
Atualizado em: 2026-09-20
Escopo: REQSYS#007.LIVING_ARCHITECTURE

Este validador usa apenas stdlib. Ele valida contratos versionados do repositório
e, quando uma base URL é fornecida, executa smoke HTTP real contra o runtime.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MAP_PATH = ROOT / "docs" / "living-architecture" / "runtime-docs-map.json"
DEFAULT_REPORT_PATH = ROOT / "artifacts" / "living-architecture-runtime-evidence.json"
NEGATIVE_CONTROL_PATH = "/__living_architecture_negative_control__"


@dataclass
class Finding:
    severity: str
    code: str
    message: str
    path: str | None = None


@dataclass
class EndpointEvidence:
    path: str
    http_code: int
    status: str | None
    correlation_id: str | None
    passed: bool


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Valida evidências reais de runtime ligadas à documentação viva.")
    parser.add_argument("--map", default=str(DEFAULT_MAP_PATH))
    parser.add_argument("--report", default=str(DEFAULT_REPORT_PATH))
    parser.add_argument("--base-url", default="")
    parser.add_argument("--telemetry-log", default="")
    parser.add_argument("--timeout", type=float, default=3.0)
    parser.add_argument(
        "--repository-only",
        action="store_true",
        help="Valida somente contratos versionados; usado também no controle negativo do próprio validador.",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(f"Arquivo JSON não encontrado: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"JSON inválido em {path}: {exc}") from exc


def add_finding(
    findings: list[Finding],
    severity: str,
    code: str,
    message: str,
    path: str | None = None,
) -> None:
    findings.append(Finding(severity=severity, code=code, message=message, path=path))


def validate_repository_contract(payload: dict[str, Any], findings: list[Finding]) -> dict[str, Any]:
    evidence = payload.get("runtime_evidence")
    result: dict[str, Any] = {
        "required_paths": [],
        "repository_markers": [],
    }

    if not isinstance(evidence, dict):
        add_finding(
            findings,
            "error",
            "RUNTIME_EVIDENCE_CONTRACT_MISSING",
            "runtime_evidence deve existir no mapa e ser um objeto.",
        )
        return result

    required_paths = evidence.get("required_paths", [])
    if not isinstance(required_paths, list):
        add_finding(findings, "error", "RUNTIME_EVIDENCE_PATHS_INVALID", "required_paths deve ser uma lista.")
        required_paths = []

    for raw_path in required_paths:
        path_text = str(raw_path)
        absolute = ROOT / path_text
        exists = absolute.is_file()
        result["required_paths"].append({"path": path_text, "exists": exists})
        if not exists:
            add_finding(
                findings,
                "error",
                "RUNTIME_EVIDENCE_PATH_MISSING",
                "Arquivo obrigatório de evidência não existe.",
                path_text,
            )

    markers = evidence.get("repository_markers", [])
    if not isinstance(markers, list):
        add_finding(findings, "error", "RUNTIME_EVIDENCE_MARKERS_INVALID", "repository_markers deve ser uma lista.")
        markers = []

    for marker in markers:
        if not isinstance(marker, dict):
            add_finding(findings, "error", "RUNTIME_EVIDENCE_MARKER_INVALID", "Marcador deve ser um objeto.")
            continue
        path_text = str(marker.get("path", ""))
        expected = str(marker.get("contains", ""))
        absolute = ROOT / path_text
        matched = False
        if absolute.is_file() and expected:
            matched = expected in absolute.read_text(encoding="utf-8", errors="replace")
        result["repository_markers"].append(
            {"path": path_text, "contains": expected, "matched": matched}
        )
        if not matched:
            add_finding(
                findings,
                "error",
                "REPOSITORY_MARKER_MISSING",
                f"Marcador obrigatório não encontrado: {expected}",
                path_text,
            )

    return result


def request_json(base_url: str, path: str, timeout: float) -> tuple[int, dict[str, Any]]:
    url = f"{base_url.rstrip('/')}{path}"
    request = Request(url, headers={"User-Agent": "reqsys-living-architecture-runtime-evidence/1.0"})
    try:
        with urlopen(request, timeout=timeout) as response:
            code = int(response.status)
            body = response.read().decode("utf-8")
    except HTTPError as exc:
        code = int(exc.code)
        body = exc.read().decode("utf-8", errors="replace")
    except URLError as exc:
        raise RuntimeError(f"Falha HTTP em {url}: {exc}") from exc

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Resposta não JSON em {url}: {exc}") from exc

    if not isinstance(payload, dict):
        raise RuntimeError(f"Resposta JSON em {url} deve ser um objeto.")

    return code, payload


def validate_runtime_http(
    payload: dict[str, Any],
    base_url: str,
    timeout: float,
    telemetry_log: str,
    findings: list[Finding],
) -> dict[str, Any]:
    evidence = payload.get("runtime_evidence", {})
    required_endpoints = evidence.get("required_endpoints", [])
    if not isinstance(required_endpoints, list) or not required_endpoints:
        add_finding(
            findings,
            "error",
            "RUNTIME_ENDPOINTS_INVALID",
            "runtime_evidence.required_endpoints deve ser uma lista não vazia.",
        )
        required_endpoints = []

    endpoint_evidence: list[EndpointEvidence] = []
    response_payloads: dict[str, dict[str, Any]] = {}

    for raw_path in required_endpoints:
        path = str(raw_path)
        try:
            http_code, response_payload = request_json(base_url, path, timeout)
        except RuntimeError as exc:
            add_finding(findings, "error", "RUNTIME_ENDPOINT_REQUEST_FAILED", str(exc), path)
            endpoint_evidence.append(
                EndpointEvidence(path=path, http_code=0, status=None, correlation_id=None, passed=False)
            )
            continue

        status = response_payload.get("status")
        correlation_id = response_payload.get("correlation_id")
        passed = http_code == 200 and status == "ok" and isinstance(correlation_id, str) and bool(correlation_id)
        endpoint_evidence.append(
            EndpointEvidence(
                path=path,
                http_code=http_code,
                status=str(status) if status is not None else None,
                correlation_id=str(correlation_id) if correlation_id is not None else None,
                passed=passed,
            )
        )
        response_payloads[path] = response_payload
        if not passed:
            add_finding(
                findings,
                "error",
                "RUNTIME_ENDPOINT_INVALID",
                f"{path} deve retornar HTTP 200, status=ok e correlation_id.",
                path,
            )

    deploy_payload = response_payloads.get("/runtime-deploy", {})
    routing = deploy_payload.get("runtime_routing", {})
    if not isinstance(routing, dict) or routing.get("active_policy") != "pc24x7-first" or routing.get("flyio_active") is not False:
        add_finding(
            findings,
            "error",
            "RUNTIME_ROUTING_POLICY_MISMATCH",
            "/runtime-deploy não confirma active_policy=pc24x7-first e flyio_active=false.",
            "/runtime-deploy",
        )

    public_payload = response_payloads.get("/runtime-public", {})
    target = public_payload.get("target", {})
    runtime_configuration = public_payload.get("runtime_configuration", {})
    provider = target.get("provider") if isinstance(target, dict) else None
    flyio_active = runtime_configuration.get("flyio_active") if isinstance(runtime_configuration, dict) else None
    if provider in {"fly.io", "flyio", "legacy-flyio"} or flyio_active is not False:
        add_finding(
            findings,
            "error",
            "RUNTIME_PUBLIC_PROVIDER_MISMATCH",
            "/runtime-public não pode declarar Fly.io ativo.",
            "/runtime-public",
        )

    negative_control: dict[str, Any] = {"path": NEGATIVE_CONTROL_PATH, "passed": False}
    try:
        negative_code, negative_payload = request_json(base_url, NEGATIVE_CONTROL_PATH, timeout)
        negative_control.update(
            {
                "http_code": negative_code,
                "status": negative_payload.get("status"),
                "correlation_id": negative_payload.get("correlation_id"),
            }
        )
        negative_control["passed"] = (
            negative_code == 404
            and negative_payload.get("status") == "blocked"
            and bool(negative_payload.get("correlation_id"))
        )
    except RuntimeError as exc:
        negative_control["error"] = str(exc)

    if not negative_control["passed"]:
        add_finding(
            findings,
            "error",
            "RUNTIME_NEGATIVE_CONTROL_FAILED",
            "Endpoint inexistente deve retornar HTTP 404, status=blocked e correlation_id.",
            NEGATIVE_CONTROL_PATH,
        )

    telemetry_result: dict[str, Any] = {
        "path": telemetry_log or None,
        "event": "http_access",
        "passed": False,
    }
    if telemetry_log:
        telemetry_path = Path(telemetry_log).resolve()
        if telemetry_path.is_file():
            telemetry_text = telemetry_path.read_text(encoding="utf-8", errors="replace")
            expected_paths = [str(path) for path in required_endpoints] + [NEGATIVE_CONTROL_PATH]
            missing_paths = [path for path in expected_paths if path not in telemetry_text]
            telemetry_result.update(
                {
                    "event_found": '"event": "http_access"' in telemetry_text,
                    "missing_paths": missing_paths,
                }
            )
            telemetry_result["passed"] = telemetry_result["event_found"] and not missing_paths
        if not telemetry_result["passed"]:
            add_finding(
                findings,
                "error",
                "RUNTIME_TELEMETRY_EVIDENCE_MISSING",
                "Log estruturado deve conter evento http_access para casos positivo e negativo.",
                telemetry_log,
            )
    else:
        add_finding(
            findings,
            "warning",
            "RUNTIME_TELEMETRY_LOG_NOT_PROVIDED",
            "Nenhum arquivo de telemetria foi fornecido para validação.",
        )

    return {
        "base_url": base_url,
        "endpoints": [asdict(item) for item in endpoint_evidence],
        "negative_control": negative_control,
        "telemetry": telemetry_result,
    }


def main() -> int:
    args = parse_args()
    map_path = Path(args.map).resolve()
    report_path = Path(args.report).resolve()
    findings: list[Finding] = []

    try:
        payload = load_json(map_path)
        repository_evidence = validate_repository_contract(payload, findings)

        runtime_evidence: dict[str, Any] | None = None
        if not args.repository_only:
            if not args.base_url:
                add_finding(
                    findings,
                    "error",
                    "RUNTIME_BASE_URL_REQUIRED",
                    "--base-url é obrigatório fora do modo --repository-only.",
                )
            else:
                runtime_evidence = validate_runtime_http(
                    payload=payload,
                    base_url=args.base_url,
                    timeout=args.timeout,
                    telemetry_log=args.telemetry_log,
                    findings=findings,
                )

        has_errors = any(item.severity == "error" for item in findings)
        has_warnings = any(item.severity == "warning" for item in findings)
        status = "failed" if has_errors else ("warning" if has_warnings else "passed")

        report = {
            "schema_version": "1.0.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "scope": str(payload.get("scope", "REQSYS#007.LIVING_ARCHITECTURE")),
            "status": status,
            "mode": "repository-only" if args.repository_only else "runtime-local-e2e",
            "correlation_id": str(uuid.uuid4()),
            "run_context": {
                "repository": os.environ.get("GITHUB_REPOSITORY"),
                "sha": os.environ.get("GITHUB_SHA"),
                "run_id": os.environ.get("GITHUB_RUN_ID"),
                "workflow": os.environ.get("GITHUB_WORKFLOW"),
            },
            "repository_evidence": repository_evidence,
            "runtime_evidence": runtime_evidence,
            "external_runtime": payload.get("runtime_evidence", {}).get("external_runtime"),
            "totals": {
                "errors": sum(1 for item in findings if item.severity == "error"),
                "warnings": sum(1 for item in findings if item.severity == "warning"),
                "findings": len(findings),
            },
            "findings": [asdict(item) for item in findings],
        }
    except RuntimeError as exc:
        report = {
            "schema_version": "1.0.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "scope": "REQSYS#007.LIVING_ARCHITECTURE",
            "status": "failed",
            "mode": "repository-only" if args.repository_only else "runtime-local-e2e",
            "correlation_id": str(uuid.uuid4()),
            "run_context": {
                "repository": os.environ.get("GITHUB_REPOSITORY"),
                "sha": os.environ.get("GITHUB_SHA"),
                "run_id": os.environ.get("GITHUB_RUN_ID"),
                "workflow": os.environ.get("GITHUB_WORKFLOW"),
            },
            "totals": {"errors": 1, "warnings": 0, "findings": 1},
            "findings": [
                asdict(Finding(severity="error", code="RUNTIME_EVIDENCE_VALIDATOR_ERROR", message=str(exc)))
            ],
        }

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": report["status"],
                "mode": report["mode"],
                "totals": report["totals"],
            },
            ensure_ascii=False,
        )
    )
    return 1 if report["status"] == "failed" else 0


if __name__ == "__main__":
    raise SystemExit(main())
