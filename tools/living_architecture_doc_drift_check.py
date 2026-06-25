#!/usr/bin/env python3
"""Validador de Documentação Viva / Arquitetura Viva do ReqSys.

Objetivo:
- Validar o mapa runtime↔docs em docs/living-architecture/runtime-docs-map.json.
- Evidenciar documentos ausentes.
- Verificar metadados mínimos de governança em modo warning-first.
- Gerar artifact JSON para auditoria e evolução incremental.

Este script não acessa rede, não lê secrets e não executa código de runtime.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MAP_PATH = ROOT / "docs" / "living-architecture" / "runtime-docs-map.json"
DEFAULT_REPORT_PATH = ROOT / "artifacts" / "living-architecture-report.json"

OWNER_PATTERN = re.compile(r"\b(owner|respons[aá]vel|ia_documentacao_viva)\b", re.IGNORECASE)
STATUS_PATTERN = re.compile(r"\b(status|estado|initial-baseline|baseline|vigente|proposto)\b", re.IGNORECASE)
DATE_PATTERN = re.compile(r"(20\d{2}-\d{2}-\d{2}|\d{2}/\d{2}/20\d{2}|atualizado em|updated_at|data)", re.IGNORECASE)


@dataclass
class Finding:
    severity: str
    code: str
    message: str
    path: str | None = None
    component_id: str | None = None


@dataclass
class ComponentResult:
    component_id: str
    component_type: str
    expected_docs: list[str]
    existing_docs: list[str] = field(default_factory=list)
    missing_docs: list[str] = field(default_factory=list)
    metadata_warnings: list[Finding] = field(default_factory=list)


@dataclass
class Report:
    schema_version: str
    generated_at: str
    scope: str
    mode: str
    map_path: str
    totals: dict[str, int]
    coverage_percent: float
    status: str
    findings: list[Finding]
    components: list[ComponentResult]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Valida documentação viva do ReqSys.")
    parser.add_argument("--map", default=str(DEFAULT_MAP_PATH), help="Caminho do runtime-docs-map.json")
    parser.add_argument("--report", default=str(DEFAULT_REPORT_PATH), help="Caminho do relatório JSON de saída")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Falha também em warnings de metadados. O padrão é warning-first.",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(f"Mapa não encontrado: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"JSON inválido em {path}: {exc}") from exc


def has_required_metadata(path: Path) -> list[Finding]:
    text = path.read_text(encoding="utf-8", errors="replace")
    warnings: list[Finding] = []

    checks = [
        (OWNER_PATTERN, "DOC_METADATA_OWNER_MISSING", "Documento sem metadado claro de owner/responsável."),
        (STATUS_PATTERN, "DOC_METADATA_STATUS_MISSING", "Documento sem metadado claro de status/estado."),
        (DATE_PATTERN, "DOC_METADATA_DATE_MISSING", "Documento sem metadado claro de data/atualização."),
    ]

    for pattern, code, message in checks:
        if not pattern.search(text):
            warnings.append(Finding(severity="warning", code=code, message=message, path=str(path.relative_to(ROOT))))

    return warnings


def validate(map_path: Path, strict: bool) -> Report:
    findings: list[Finding] = []
    components: list[ComponentResult] = []
    payload = load_json(map_path)

    runtime_doc_links = payload.get("runtime_doc_links")
    if not isinstance(runtime_doc_links, list):
        findings.append(Finding(severity="error", code="MAP_RUNTIME_DOC_LINKS_INVALID", message="runtime_doc_links deve ser uma lista."))
        runtime_doc_links = []

    total_expected = 0
    total_existing = 0
    total_missing = 0
    total_metadata_warnings = 0

    for item in runtime_doc_links:
        component_id = str(item.get("component_id", "unknown"))
        component_type = str(item.get("component_type", "unknown"))
        expected_docs = item.get("expected_docs", [])

        if not isinstance(expected_docs, list):
            findings.append(
                Finding(
                    severity="error",
                    code="EXPECTED_DOCS_INVALID",
                    message="expected_docs deve ser uma lista.",
                    component_id=component_id,
                )
            )
            expected_docs = []

        result = ComponentResult(component_id=component_id, component_type=component_type, expected_docs=[str(p) for p in expected_docs])

        for raw_doc_path in expected_docs:
            doc_path_text = str(raw_doc_path)
            total_expected += 1
            absolute_doc_path = ROOT / doc_path_text

            if not absolute_doc_path.exists() or not absolute_doc_path.is_file():
                total_missing += 1
                result.missing_docs.append(doc_path_text)
                findings.append(
                    Finding(
                        severity="error",
                        code="DOC_MISSING",
                        message="Documento referenciado não existe.",
                        path=doc_path_text,
                        component_id=component_id,
                    )
                )
                continue

            total_existing += 1
            result.existing_docs.append(doc_path_text)

            metadata_warnings = has_required_metadata(absolute_doc_path)
            for warning in metadata_warnings:
                warning.component_id = component_id
            result.metadata_warnings.extend(metadata_warnings)
            findings.extend(metadata_warnings)
            total_metadata_warnings += len(metadata_warnings)

        components.append(result)

    coverage_percent = round((total_existing / total_expected * 100), 2) if total_expected else 0.0
    has_errors = any(f.severity == "error" for f in findings)
    has_warnings = any(f.severity == "warning" for f in findings)

    if has_errors:
        status = "failed"
    elif strict and has_warnings:
        status = "failed"
    elif has_warnings:
        status = "warning"
    else:
        status = "passed"

    return Report(
        schema_version="1.0.0",
        generated_at=datetime.now(timezone.utc).isoformat(),
        scope=str(payload.get("scope", "REQSYS#007.LIVING_ARCHITECTURE")),
        mode="strict" if strict else "warning-first",
        map_path=str(map_path.relative_to(ROOT) if map_path.is_relative_to(ROOT) else map_path),
        totals={
            "components": len(components),
            "expected_docs": total_expected,
            "existing_docs": total_existing,
            "missing_docs": total_missing,
            "metadata_warnings": total_metadata_warnings,
            "findings": len(findings),
        },
        coverage_percent=coverage_percent,
        status=status,
        findings=findings,
        components=components,
    )


def write_report(report: Report, report_path: Path) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(asdict(report), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    map_path = Path(args.map).resolve()
    report_path = Path(args.report).resolve()

    try:
        report = validate(map_path=map_path, strict=args.strict)
        write_report(report, report_path)
    except RuntimeError as exc:
        fallback = Report(
            schema_version="1.0.0",
            generated_at=datetime.now(timezone.utc).isoformat(),
            scope="REQSYS#007.LIVING_ARCHITECTURE",
            mode="strict" if args.strict else "warning-first",
            map_path=str(map_path),
            totals={"components": 0, "expected_docs": 0, "existing_docs": 0, "missing_docs": 0, "metadata_warnings": 0, "findings": 1},
            coverage_percent=0.0,
            status="failed",
            findings=[Finding(severity="error", code="VALIDATOR_RUNTIME_ERROR", message=str(exc))],
            components=[],
        )
        write_report(fallback, report_path)
        print(str(exc), file=sys.stderr)
        return 1

    print(json.dumps({"status": report.status, "coverage_percent": report.coverage_percent, "totals": report.totals}, ensure_ascii=False))

    if report.status == "failed":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
