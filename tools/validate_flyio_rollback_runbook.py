from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

REQUIRED_HEADINGS = [
    "## Pré-condições",
    "## Critérios que acionam rollback",
    "## Procedimento",
    "## Evidências obrigatórias",
    "## Restrições",
    "## Teste do runbook",
]

REQUIRED_TOKENS = [
    'flyctl releases --app "$FLY_APP_NAME" --image',
    'flyctl deploy',
    '--image "$PREVIOUS_IMAGE"',
    '--strategy rolling',
    '--wait-timeout 10m',
    '--ha=false',
    'REQSYS_RUNTIME_ENVIRONMENT',
    'REQSYS_FLY_APP_NAME',
    'REQSYS_DUCKDNS_HOSTNAME',
    '/health',
    '/ready',
    '/runtime-public',
    'correlation_id',
    'FLY_API_TOKEN',
]

FORBIDDEN_TOKENS = [
    "FLY_API_TOKEN=",
    "Authorization: Bearer",
]


def validate(runbook_path: Path) -> dict:
    text = runbook_path.read_text(encoding="utf-8")
    missing_headings = [heading for heading in REQUIRED_HEADINGS if heading not in text]
    missing_tokens = [token for token in REQUIRED_TOKENS if token not in text]
    forbidden_matches = [token for token in FORBIDDEN_TOKENS if token in text]

    checks = {
        "runbook_exists": runbook_path.exists(),
        "required_headings_present": not missing_headings,
        "required_commands_present": not missing_tokens,
        "no_literal_secret_assignment": not forbidden_matches,
        "minimum_length": len(text) >= 2500,
    }

    status = "ok" if all(checks.values()) else "blocked"
    return {
        "schema_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "domain": "REQSYS#002.RUNTIME_PUBLICO.ROLLBACK_READINESS",
        "status": status,
        "runbook": str(runbook_path),
        "checks": checks,
        "missing_headings": missing_headings,
        "missing_tokens": missing_tokens,
        "forbidden_matches": forbidden_matches,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the Fly.io rollback runbook contract.")
    parser.add_argument(
        "--runbook",
        default="docs/FLYIO_ROLLBACK_RUNBOOK.md",
        help="Path to the Markdown runbook.",
    )
    parser.add_argument(
        "--report",
        default="artifacts/flyio-rollback-readiness.json",
        help="Path to the JSON evidence report.",
    )
    args = parser.parse_args()

    runbook_path = Path(args.runbook)
    report_path = Path(args.report)

    if not runbook_path.exists():
        result = {
            "schema_version": "1.0.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "domain": "REQSYS#002.RUNTIME_PUBLICO.ROLLBACK_READINESS",
            "status": "blocked",
            "runbook": str(runbook_path),
            "checks": {"runbook_exists": False},
            "missing_headings": REQUIRED_HEADINGS,
            "missing_tokens": REQUIRED_TOKENS,
            "forbidden_matches": [],
        }
    else:
        result = validate(runbook_path)

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
