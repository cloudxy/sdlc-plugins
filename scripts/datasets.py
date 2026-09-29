#!/usr/bin/env python3
"""Small-file data snapshots and explicit external data identity descriptors."""
from pathlib import Path
from runtime_protocol import digest, file_hash, load, now, object_keys, require, safe_id, write_json


def capture(root, dataset_id, source, semantics, window, limitations=()):
    from task_runtime import freeze_files
    root = Path(root).resolve(); source = Path(source).resolve(); safe_id(dataset_id)
    require(semantics and window, 'data semantics and observation window required')
    obj = freeze_files(root, [str(source)])[str(source)]
    value = {'schema_version': 1, 'kind': 'dataset-snapshot', 'id': dataset_id, 'at': now(),
             'identity': {'type': 'file', 'path': obj['object'], 'sha256': obj['sha256'], 'source': str(source)},
             'semantics': semantics, 'window': window, 'limitations': list(limitations)}
    out = root / 'artifacts' / dataset_id / ('dataset-' + digest(value) + '.json')
    write_json(out, value)
    return {'path': str(out), 'sha256': file_hash(out)}


def validate(path):
    value = load(path)
    object_keys(value, {'schema_version', 'kind', 'id', 'at', 'identity', 'semantics', 'window', 'limitations'},
                {'schema_version', 'kind', 'id', 'identity', 'semantics', 'window', 'limitations'}, 'dataset')
    require(value['schema_version'] == 1 and value['kind'] == 'dataset-snapshot', 'unsupported dataset descriptor')
    safe_id(value['id']); require(value['semantics'] and value['window'], 'dataset semantics/window missing')
    require(isinstance(value['limitations'], list), 'dataset limitations must be a list')
    identity = value['identity']
    if identity.get('type') == 'file':
        object_keys(identity, {'type', 'path', 'sha256', 'source'}, {'type', 'path', 'sha256'}, 'file dataset')
        require(Path(identity['path']).is_absolute() and file_hash(identity['path']) == identity['sha256'], 'dataset content changed')
    else:
        object_keys(identity, {'type', 'provider', 'snapshot_id', 'partitions', 'query_sha256', 'observed_at', 'evidence'},
                    {'type', 'provider', 'snapshot_id', 'partitions', 'query_sha256', 'observed_at', 'evidence'}, 'external dataset')
        require(identity['type'] == 'external' and isinstance(identity['provider'], str) and identity['provider']
                and isinstance(identity['snapshot_id'], str) and identity['snapshot_id'] not in ('latest', ''),
                'external dataset requires immutable provider snapshot identity')
        require(isinstance(identity['partitions'], list) and identity['query_sha256'] and identity['observed_at'], 'external data boundaries missing')
        require(isinstance(identity['evidence'], list) and identity['evidence'], 'external snapshot needs acquisition/quality evidence')
        for ref in identity['evidence']:
            object_keys(ref, {'path', 'sha256'}, {'path', 'sha256'}, 'dataset evidence')
            require(file_hash(ref['path']) == ref['sha256'], 'dataset evidence changed')
    return value
