#!/usr/bin/env python3
"""Shared, strict primitives for task protocol 1. No model calls or shell execution."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import re
import stat
import tempfile
from pathlib import Path
from zoneinfo import ZoneInfo

PROTOCOL = 1
CAPABILITIES = frozenset({'input-contract-v1', 'result-v1', 'task-closure-v1'})
CONDITIONS = frozenset({'always', 'ui', 'tracking', 'q_security', 'lane_l2plus'})
SKIP_DIRS = frozenset({'.git', '__pycache__', 'node_modules', '.venv', 'venv', '.pytest_cache', '.cache'})
SAFE_ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]{0,119}$')


class ProtocolError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise ProtocolError(message)


def object_keys(value, allowed, required=(), label='object'):
    require(isinstance(value, dict), f'{label}: expected object')
    require(not set(value) - set(allowed), f'{label}: unknown fields {sorted(set(value) - set(allowed))}')
    require(set(required) <= set(value), f'{label}: missing fields {sorted(set(required) - set(value))}')
    return value


def _pairs(pairs):
    result = {}
    for k, v in pairs:
        require(k not in result, f'duplicate JSON key: {k}')
        result[k] = v
    return result


def loads(text):
    def invalid(value):
        raise ProtocolError(f'invalid JSON constant: {value}')
    try:
        return json.loads(text, object_pairs_hook=_pairs, parse_constant=invalid)
    except json.JSONDecodeError as error:
        raise ProtocolError(str(error)) from error


def load(path):
    return loads(Path(path).read_text(encoding='utf-8'))


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n').encode()


def digest(value):
    return hashlib.sha256(encoded(value)).hexdigest()


def file_hash(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def write_json(path, value, exclusive=True):
    """Atomic, no-clobber publication; a failed write leaves no partial record."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.task-write-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(encoded(value)); stream.flush(); os.fsync(stream.fileno())
        if exclusive:
            os.link(name, path)  # fails if another process already published this name
        else:
            os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def capabilities(value):
    require(isinstance(value, list) and all(isinstance(x, str) for x in value), 'required_capabilities must be a string list')
    require(not set(value) - CAPABILITIES, f'unsupported required capabilities: {sorted(set(value) - CAPABILITIES)}')


def version(value):
    require(isinstance(value,dict), 'protocol document must be an object')
    require(type(value.get('protocol_version')) is int and value['protocol_version'] == PROTOCOL, 'unsupported protocol_version')
    capabilities(value.get('required_capabilities', []))


def now():
    return dt.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(timespec='microseconds')


def safe_id(value, label='id'):
    require(isinstance(value, str) and bool(SAFE_ID.fullmatch(value)), f'unsafe {label}: {value!r}')
    return value


def path_inside(path, root, exists=False):
    root = Path(root).resolve()
    path = Path(path)
    if not path.is_absolute():
        path = root / path
    resolved = path.resolve()
    require(resolved.is_relative_to(root) and resolved != root, f'path escapes or names root: {path}')
    if exists:
        require(resolved.is_file(), f'missing file: {resolved}')
    return resolved


def file_record(path):
    path = Path(path)
    s = path.lstat()
    if stat.S_ISLNK(s.st_mode):
        return {'type': 'symlink', 'target': os.readlink(path), 'mode': stat.S_IMODE(s.st_mode)}
    require(stat.S_ISREG(s.st_mode), f'unsupported filesystem entry: {path}')
    return {'type': 'file', 'sha256': file_hash(path), 'size': s.st_size, 'mode': stat.S_IMODE(s.st_mode)}


def snapshot(roots, exclude=(), limit=20000):
    """Observed files only. Symlinks are recorded, never traversed; exclusions are explicit."""
    roots = sorted(set(str(Path(p).resolve()) for p in roots))
    excluded = [Path(p).absolute() for p in exclude]
    files, gaps = {}, []
    for raw in roots:
        root = Path(raw)
        if not root.is_dir():
            gaps.append(f'missing root: {root}'); continue
        def error(e):
            gaps.append(str(e))
        for directory, dirs, names in os.walk(root, followlinks=False, onerror=error):
            parent = Path(directory)
            dirs.sort(); names.sort()
            for name in list(dirs):
                p = parent / name
                if name in SKIP_DIRS or any(p == ex or p.is_relative_to(ex) for ex in excluded):
                    dirs.remove(name)
                elif p.is_symlink():
                    dirs.remove(name); names.append(name)
            for name in names:
                p = parent / name
                if any(p == ex or p.is_relative_to(ex) for ex in excluded):
                    continue
                try:
                    files[str(p)] = file_record(p)
                except (OSError, ProtocolError) as e:
                    gaps.append(str(e))
                require(len(files) <= limit, f'snapshot exceeds {limit} files; explicitly scope observation roots')
    return {'roots': roots, 'files': files, 'gaps': gaps, 'excluded_paths': list(map(str, excluded)),
            'excluded_directory_names': sorted(SKIP_DIRS),
            'limits': ['no write-then-restore detection', 'no remote effects', 'no observations outside roots']}


def changes(before, after):
    return [p for p in sorted(set(before['files']) | set(after['files']))
            if before['files'].get(p) != after['files'].get(p)]


def state_read(path):
    """Read existing YAML via the shared parser, reject ambiguous new protocol sections."""
    from check_config import parse_yaml, _strip_comment
    text = Path(path).read_text(encoding='utf-8')
    # Existing legacy fields keep their syntax. Strictness applies to protocol-owned blocks.
    owned = {'task_protocol', 'required_capabilities', 'selected_tasks', 'obligations', 'task_decisions'}
    top, section, blocks = set(), None, {}
    for raw in text.splitlines():
        line = _strip_comment(raw).rstrip()
        if not line.strip():
            continue
        require('\t' not in raw[:len(raw) - len(raw.lstrip())], 'tabs in YAML indentation')
        indent = len(line) - len(line.lstrip())
        if indent == 0:
            m = re.match(r'([\w-]+):', line)
            if not m:
                continue
            key = m[1]
            require(key not in top, f'duplicate state key: {key}')
            top.add(key); section = key
        if section in owned:
            blocks.setdefault(section, []).append((indent, line.strip()))
    value = parse_yaml(text)
    for rows in blocks.values():
        value.update(strict_yaml_block(rows))
    if 'task_protocol' in value:
        require(type(value['task_protocol']) is int and value['task_protocol'] == PROTOCOL, 'unsupported task_protocol')
    capabilities(value.get('required_capabilities', []))
    return value


def strict_yaml_block(rows):
    """Protocol YAML subset: indented maps/lists, quoted scalars, scalar flow lists.

    No flow maps, aliases, tags, complex keys, multiline scalars or silent fallbacks.
    Legacy fields are parsed separately and are not rewritten by this reader.
    """
    from check_config import _scalar
    def scalar(raw):
        require(raw not in ('|', '>') and not raw.startswith(('{', '&', '*', '!')),
                'protocol state: use block mappings; flow objects/aliases/tags/scalars unsupported')
        require(not (raw.startswith('[') and any(c in raw for c in '{}')),
                'protocol state: flow objects unsupported')
        if raw.startswith('['):
            require(raw.endswith(']') and '[' not in raw[1:], 'invalid scalar list')
        if raw.startswith(('"', "'")):
            require(len(raw) >= 2 and raw[-1] == raw[0], 'unterminated quoted scalar')
        return _scalar(raw)
    def parse(items):
        require(bool(items), 'empty YAML block')
        level = items[0][0]
        is_list = items[0][1].startswith('- ')
        out = [] if is_list else {}
        i = 0
        while i < len(items):
            ind, body = items[i]
            require(ind == level, f'invalid protocol indentation: {body}')
            j = i + 1
            while j < len(items) and items[j][0] > level:
                j += 1
            children = items[i + 1:j]
            if is_list:
                require(body.startswith('- '), 'mixed list/mapping in protocol state')
                body = body[2:]
                if re.match(r'^[\w.-]+:(\s|$)', body):
                    out.append(parse([(level + 2, body)] + children))
                else:
                    require(not children, 'scalar list item has children')
                    out.append(scalar(body))
            else:
                m = re.fullmatch(r'([\w.-]+):(?:\s+(.*))?', body)
                require(m is not None, f'unsupported protocol YAML: {body}')
                key, raw = m[1], m[2] or ''
                require(key not in out, f'duplicate protocol field: {key}')
                require(not (raw and children), f'scalar {key} has children')
                out[key] = parse(children) if children else scalar(raw)
            i = j
        return out
    return parse(rows)


def enabled(condition, state):
    require(condition in CONDITIONS, f'unknown input condition: {condition}')
    if condition == 'always':
        return True
    if condition == 'lane_l2plus':
        require(state.get('lane') in ('L0','L1','L2','L3','L4'), 'missing/unknown lane')
        return state['lane'] in ('L2','L3','L4')
    require(condition in state, f'undecided condition: {condition}')
    value = state[condition]
    require(value in (True, False, 'yes', 'no', 'true', 'false'), f'invalid condition {condition}')
    return value in (True, 'yes', 'true')


def input_contract_errors(registry):
    errors = []
    try:
        capabilities(registry.get('required_capabilities', []))
        for t in registry['tasks']:
            ids = set()
            for entry in t.get('inputs', []):
                object_keys(entry, {'id','source','ref','when','access','cardinality','requires_acceptance','allow_unfilled','alternatives'},
                            {'id','source','when','access'}, 'input contract')
                require(entry['id'] not in ids, 'duplicate input id'); ids.add(entry['id'])
                safe_id(entry['id'])
                require(entry['when'] in CONDITIONS, 'unknown input condition')
                require(entry['source'] in ('artifact','product','binding','source_snapshot','verification_records'), 'unknown input source')
                require(entry['access'] in ('read','read-write'), 'unknown input access')
                require(entry.get('cardinality','one')=='one', 'protocol 1 currently supports cardinality one only')
                for flag in ('requires_acceptance','allow_unfilled'):
                    require(flag not in entry or type(entry[flag]) is bool, f'{flag} must be boolean')
                for alternative in entry.get('alternatives',[]):
                    object_keys(alternative,{'source','ref','rule'},{'source','ref','rule'},'input alternative')
                    require(alternative['source']=='artifact' and alternative['ref'] in registry['artifacts']
                            and alternative['rule']=='l2-short-spec','unsupported input alternative')
                if entry['source'] == 'artifact':
                    require(entry.get('ref') in registry['artifacts'], 'unknown artifact input')
                if entry['source'] == 'product':
                    ref = entry.get('ref', '')
                    require(bool(ref) and not Path(ref).is_absolute() and '..' not in Path(ref).parts, 'unsafe product input')
    except (ProtocolError, TypeError) as e:
        errors.append(str(e))
    return errors
