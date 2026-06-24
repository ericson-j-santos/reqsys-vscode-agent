from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from reqsys_agent.workspace_reader import discover_files, load_index, read_config, utc_now


def _runtime_dir(workspace: Path) -> Path:
    path = workspace / '.reqsys'
    path.mkdir(exist_ok=True)
    return path


def _index_path(workspace: Path) -> Path:
    return _runtime_dir(workspace) / 'index.json'


def _state_path(workspace: Path) -> Path:
    return _runtime_dir(workspace) / 'index-state.json'


def _load_state(workspace: Path) -> dict[str, Any]:
    path = _state_path(workspace)
    if not path.exists():
        return {'files': {}}
    return json.loads(path.read_text(encoding='utf-8'))


def _save_state(workspace: Path, state: dict[str, Any]) -> None:
    _state_path(workspace).write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')


def _fingerprint(path: str, size_bytes: int, modified_at: str) -> str:
    value = f'{path}|{size_bytes}|{modified_at}'.encode('utf-8')
    return hashlib.sha256(value).hexdigest()


def build_incremental_index(workspace: Path) -> dict[str, Any]:
    config = read_config(workspace)
    previous_index = load_index(workspace) or {'files': []}
    previous_files = {item.get('path'): item for item in previous_index.get('files', [])}
    previous_state = _load_state(workspace).get('files', {})

    files = discover_files(workspace, config)
    indexed_files: list[dict[str, Any]] = []
    next_state: dict[str, Any] = {'files': {}}
    cache_hits = 0
    cache_misses = 0

    for workspace_file in files:
        payload = asdict(workspace_file)
        current_fingerprint = _fingerprint(
            workspace_file.path,
            workspace_file.size_bytes,
            workspace_file.modified_at,
        )
        previous_fingerprint = previous_state.get(workspace_file.path, {}).get('fingerprint')
        previous_payload = previous_files.get(workspace_file.path)

        if previous_payload and previous_fingerprint == current_fingerprint:
            indexed_files.append(previous_payload)
            cache_hits += 1
        else:
            indexed_files.append(payload)
            cache_misses += 1

        next_state['files'][workspace_file.path] = {
            'fingerprint': current_fingerprint,
            'sha256': workspace_file.sha256,
        }

    index = {
        'schema_version': '0.4.0',
        'generated_at': utc_now(),
        'project': config.get('project', workspace.name),
        'mode': config.get('mode', 'safe-readonly'),
        'workspace': str(workspace.resolve()),
        'file_count': len(indexed_files),
        'cache': {
            'enabled': True,
            'cache_hits': cache_hits,
            'cache_misses': cache_misses,
        },
        'files': indexed_files,
        'restrictions': [
            'safe-readonly',
            'allowed paths only',
            'binary files ignored',
            'large files skipped',
            'incremental cache enabled',
        ],
    }

    _index_path(workspace).write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding='utf-8')
    _save_state(workspace, next_state)
    return index
