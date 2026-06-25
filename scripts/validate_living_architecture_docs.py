#!/usr/bin/env python3
"""Validate ReqSys living architecture documentation.

This validator is intentionally standard-library only so it can run in GitHub
Actions without installing project dependencies.

Default mode is warning-first: findings are reported in JSON, but the process
exits with 0 unless --strict is used.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import uuid
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

MAP_PATH = Path("docs/living-architecture/runtime-docs-map.json")
DEFAULT_REPORT_PATH = Path("artifacts/living-architecture-report.json")

REQUIRED_MAP_FIELDS = {
    "schema_version",
    "scope",
    "updated_at",
    "owner",
    "status",
    "runtime_doc_links",
}

METADATA_PATTERNS = {
    "owner": re.compile(r"(?im)^\s*(\*\*)?owner(\*\*)?\s*[:|-]|\"owner\"\s*:") ,
    "status": re.compile(r"(?im)^\s*(\*\*)?status(\*\*)?\s*[:|-]|\"status\"\s*:") ,
    "updated_at": re.compile(r"(?im)^\s*(\*\*)?(atualizado em|data|updated_at)(\*\*)?\s*[:|-]|\"updated_at\"\s*:") ,
}

# Detect likely secret assignments without flagging ordinary governance text that
# merely mentions tokens, secrets, CPF, PII, or connection strings.
SENSITIVE_ASSIGNMENT = re.compile(
    r"(?i)(token|secret|password|senha|connection[_ -]?string|api[_ -]?key)\s*[:=]\s*['\"][^'\"]{8,}['\"]"
)

PII_EXAMPLES = re.compile(r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b|\b\d{11}\b")


@dataclass(frozen=True)
class Finding:
    rule_id: str
    severity: str
    path: str
    message: str


def utc_now() -> str:
    return dt.datetime.now(dt.UTC).isoformat(timespec="seconds")


def read_json(path: Path) -> tuple[dict[str, Any] | None, list[Finding]]:
    findings: list[Finding] = []
    if not path.exists():
        findings.append(
            Finding(
                rule_id="LIVDOCS-MAP-001",
                severity="error",
                path=str(path),
                message="Arquivo runtime-docs-map.json não encontrado.",
            )
        )
        return None, findings

    try:
        return json.loads(path.read_text(encoding="utf-8")), findings
    except json.JSONDecodeError as exc:
        findings.append(
            Finding(
                rule_id="LIVDOCS-MAP-002",
                severity="error",
                path=str(path),
                message=f"JSON inválido: {exc}",
            )
        )
        return None, findings


def validate_map_shape(data: dict[str, Any] | None, map_path: Path) -> list[Finding]:
    if data is None:
        return []

    findings: list[Finding] = []
    missing = sorted(REQUIRED_MAP_FIELDS - set(data))
    for field in missing:
        findings.append(
            Finding(
                rule_id="LIVDOCS-MAP-003",
                severity="error",
                path=str(map_path),
                message=f"Campo obrigatório ausente no mapa: {field}",
            )
        )

    links = data.get("runtime_doc_links")
    if not isinstance(links, list) or not links:
        findings.append(
            Finding(
                rule_id="LIVDOCS-MAP-004",
                severity="error",
                path=str(map_path),
                message="runtime_doc_links deve ser uma lista não vazia.",
            )
        )
        return findings

    for index, item in enumerate(links):
        item_path = f"{map_path}#runtime_doc_links[{index}]"
        if not isinstance(item, dict):
            findings.append(
                Finding(
                    rule_id="LIVDOCS-MAP-005",
                    severity="error",
                    path=item_path,
                    message="Entrada de runtime_doc_links deve ser objeto JSON.",
                )
            )
            continue

        for field in ("component_id", "component_type", "expected_docs", "validation_status"):
            if field not in item:
                findings.append(
                    Finding(
                        rule_id="LIVDOCS-MAP-006",
                        severity="warning",
                        path=item_path,
                        message=f"Campo recomendado ausente no vínculo runtime↔docs: {field}",
                    )
                )

        expected_docs = item.get("expected_docs")
        if not isinstance(expected_docs, list) or not expected_docs:
            findings.append(
                Finding(
                    rule_id="LIVDOCS-MAP-007",
                    severity="error",
                    path=item_path,
                    message="expected_docs deve ser uma lista não vazia.",
                )
            )

    return findings


def collect_expected_docs(data: dict[str, Any] | None) -> list[str]:
    if data is None:
        return []

    docs: list[str] = []
    for item in data.get("runtime_doc_links", []):
        if isinstance(item, dict):
            expected_docs = item.get("expected_docs", [])
            if isinstance(expected_docs, list):
                docs.extend(str(path) for path in expected_docs if path)
    return sorted(set(docs))


def validate_doc(path: Path) -> tuple[bool, bool, list[Finding]]:
    findings: list[Finding] = []
    if not path.exists():
        findings.append(
            Finding(
                rule_id="LIVDOCS-DOC-001",
                severity="error",
                path=str(path),
                message="Documento referenciado não existe.",
            )
        )
        return False, False, findings

    try:
        content = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        findings.append(
            Finding(
                rule_id="LIVDOCS-DOC-002",
                severity="error",
                path=str(path),
                message="Documento não está legível como UTF-8.",
            )
        )
        return True, False, findings

    if SENSITIVE_ASSIGNMENT.search(content):
        findings.append(
            Finding(
                rule_id="LIVDOCS-SEC-001",
                severity="error",
                path=str(path),
                message="Possível segredo ou credencial atribuído no documento.",
            )
        )

    if PII_EXAMPLES.search(content):
        findings.append(
            Finding(
                rule_id="LIVDOCS-SEC-002",
                severity="warning",
                path=str(path),
                message="Possível CPF/PII literal encontrado. Validar se é dado fictício ou remover.",
            )
        )

    metadata_hits = {
        name: bool(pattern.search(content)) for name, pattern in METADATA_PATTERNS.items()
    }
    has_metadata = all(metadata_hits.values())
    if not has_metadata:
        missing = ", ".join(name for name, hit in metadata_hits.items() if not hit)
        findings.append(
            Finding(
                rule_id="LIVDOCS-DOC-003",
                severity="warning",
                path=str(path),
                message=f"Metadados mínimos ausentes ou não padronizados: {missing}",
            )
        )

    return True, has_metadata, findings


def percent(part: int, total: int) -> float:
    if total == 0:
        return 0.0
    return round((part / total) * 100, 2)


def build_report(root: Path, report_path: Path, strict: bool) -> tuple[dict[str, Any], int]:
    map_path = root / MAP_PATH
    data, findings = read_json(map_path)
    findings.extend(validate_map_shape(data, map_path))

    expected_docs = collect_expected_docs(data)
    existing_docs = 0
    docs_with_metadata = 0

    for doc in expected_docs:
        exists, has_metadata, doc_findings = validate_doc(root / doc)
        if exists:
            existing_docs += 1
        if has_metadata:
            docs_with_metadata += 1
        findings.extend(doc_findings)

    error_count = sum(1 for finding in findings if finding.severity == "error")
    warning_count = sum(1 for finding in findings if finding.severity == "warning")

    status = "passed"
    if warning_count:
        status = "warning"
    if error_count:
        status = "failed" if strict else "warning"

    report = {
        "schema_version": "1.0.0",
        "scope": "REQSYS#007.LIVING_ARCHITECTURE",
        "correlation_id": str(uuid.uuid4()),
        "generated_at": utc_now(),
        "strict": strict,
        "status": status,
        "summary": {
            "components_mapped": len(data.get("runtime_doc_links", [])) if isinstance(data, dict) else 0,
            "expected_docs": len(expected_docs),
            "existing_docs": existing_docs,
            "docs_with_minimum_metadata": docs_with_metadata,
            "coverage_percent": percent(existing_docs, len(expected_docs)),
            "metadata_coverage_percent": percent(docs_with_metadata, len(expected_docs)),
            "errors": error_count,
            "warnings": warning_count,
        },
        "findings": [asdict(finding) for finding in findings],
        "next_actions": [
            "Corrigir documentos ausentes antes de promover o gate para bloqueante.",
            "Padronizar metadados mínimos em README, HTML e diagramas vivos.",
            "Evoluir validação para conferir links reais de runtime e artifacts de CI.",
        ],
    }

    report_output = root / report_path
    report_output.parent.mkdir(parents=True, exist_ok=True)
    report_output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    exit_code = 1 if strict and error_count else 0
    return report, exit_code


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate ReqSys living architecture docs.")
    parser.add_argument("--root", default=".", help="Repository root. Default: current directory.")
    parser.add_argument(
        "--report",
        default=str(DEFAULT_REPORT_PATH),
        help="Report output path relative to root.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail with exit code 1 when error findings are detected.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    root = Path(args.root).resolve()
    report_path = Path(args.report)
    report, exit_code = build_report(root=root, report_path=report_path, strict=args.strict)

    print(json.dumps(report["summary"], ensure_ascii=False, indent=2))
    print(f"living architecture docs status: {report['status']}")
    print(f"report: {root / report_path}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
