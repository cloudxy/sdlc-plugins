#!/usr/bin/env python3
"""A citable timeline and efficiency digest for Claude Code JSONL or ZCode SQLite sessions.

  session_digest.py <jsonl> [--from-line N] [--to-line M] [--format md|tsv]
  session_digest.py <jsonl> --stats
  session_digest.py --zcode-db <sqlite_path> --session <session_id> [--stats] [--format md|tsv]

Every Claude Code row cites `path:line`, so a diagnosis finding can point at the exact event. Lines are read one at a
time and each field is cut to 200 characters; secrets are redacted before anything is printed.
In optional `--zcode-db` mode, the SQLite file is opened strictly read-only (`mode=ro`) to summarize the root session
and child subagent sessions (wall duration, spawns, model calls, tool calls, tokens, and missing metrics) with secret
redaction. Other unsupported transcript formats exit 2 cleanly.
Exit: 0 ok · 2 usage or unsupported format.
"""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path
_SCRIPTS_DIR = str(_Path(__file__).resolve().parents[1])  # _SDLC_SCRIPTS_PATH
if _SCRIPTS_DIR not in _sys.path:
    _sys.path.insert(0, _SCRIPTS_DIR)

import argparse
import collections
import datetime as dt
import json
import sqlite3
import sys
from pathlib import Path
from urllib.parse import quote

from evals.behavior_smoke import redact

KNOWN_TYPES = {'user', 'assistant', 'system', 'attachment', 'summary', 'mode', 'permission-mode'}
COLUMNS = ['ref', 'time', 'side', 'kind', 'tool', 'summary', 'error', 'repeat_of']
LIMIT = 200


def clip(value) -> str:
    if not isinstance(value, str):
        value = json.dumps(value, ensure_ascii=False, sort_keys=True)
    value = ' '.join(value.split())
    value = redact(value)
    return value if len(value) <= LIMIT else value[:LIMIT - 1] + '…'


def result_text(content) -> str:
    if isinstance(content, list):
        return ' '.join(c.get('text', '') for c in content if isinstance(c, dict))
    return content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)


def _parse_ts(val) -> float | None:
    if val is None or val == '':
        return None
    if isinstance(val, (int, float)):
        num = float(val)
        return num / 1000.0 if num > 1e11 else num
    s = str(val).strip()
    if not s:
        return None
    try:
        num = float(s)
        return num / 1000.0 if num > 1e11 else num
    except ValueError:
        pass
    try:
        return dt.datetime.fromisoformat(s.replace('Z', '+00:00')).timestamp()
    except ValueError:
        return None


def _fmt_ts(val) -> str:
    ts = _parse_ts(val)
    if ts is None:
        return str(val or '')[:19]
    return dt.datetime.fromtimestamp(ts, tz=dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S')


def _safe_int(val) -> int | None:
    if val is None or isinstance(val, bool):
        return None
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


def events(path: Path, first: int, last: int):
    """Yield one row per meaningful event; raise ValueError for a non-Claude-Code transcript."""
    tool_of, seen = {}, {}
    recognized = checked = 0
    with path.open(encoding='utf-8', errors='replace') as fh:
        for n, line in enumerate(fh, 1):
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(rec, dict):
                continue
            if checked < 50:
                checked += 1
                recognized += rec.get('type') in KNOWN_TYPES
                if checked == 50 and not recognized:
                    raise ValueError('unsupported')
            if n < first or (last and n > last):
                continue
            ref = f'{path}:{n}'
            base = {'ref': ref, 'time': str(rec.get('timestamp', ''))[:19],
                    'side': 'sub' if rec.get('isSidechain') else 'main', 'tool': '', 'error': '', 'repeat_of': ''}
            kind = rec.get('type')
            if kind == 'system' and rec.get('subtype') == 'compact_boundary' or rec.get('isCompactSummary'):
                yield dict(base, kind='compaction', summary=clip(rec.get('subtype') or 'compact summary'))
                continue
            message = rec.get('message') if isinstance(rec.get('message'), dict) else {}
            content = message.get('content')
            if kind == 'user' and isinstance(content, str):
                injected = content.lstrip().startswith('<')  # hook output, notifications, local-command echoes
                yield dict(base, kind='injected' if injected else 'user', summary=clip(content))
                continue
            for item in content if isinstance(content, list) else []:
                if not isinstance(item, dict):
                    continue
                t = item.get('type')
                if kind == 'user' and t == 'text':
                    yield dict(base, kind='user', summary=clip(item.get('text', '')))
                elif kind == 'user' and t == 'tool_result':
                    yield dict(base, kind='tool_result', tool=tool_of.get(item.get('tool_use_id'), ''),
                               summary=clip(result_text(item.get('content'))),
                               error='yes' if item.get('is_error') else '')
                elif kind == 'assistant' and t == 'text':
                    yield dict(base, kind='assistant_text', summary=clip(item.get('text', '')))
                elif kind == 'assistant' and t == 'tool_use':
                    name = item.get('name', '')
                    tool_of[item.get('id')] = name
                    key = (name, json.dumps(item.get('input'), sort_keys=True, ensure_ascii=False))
                    repeat = seen.get(key, '')
                    seen.setdefault(key, ref)
                    yield dict(base, kind='skill_load' if name == 'Skill' else 'tool_use', tool=name,
                               summary=clip(item.get('input')), repeat_of=repeat)
    if checked and not recognized:
        raise ValueError('unsupported')


def _extract_zcode_tool_items(raw_content, raw_tool_calls) -> tuple[list[dict], list[dict], str]:
    """Parse tool calls, tool errors, and display text from ZCode message columns."""
    tool_uses: list[dict] = []
    tool_results: list[dict] = []
    text_parts: list[str] = []

    def _inspect_list(items):
        for item in items:
            if not isinstance(item, dict):
                if isinstance(item, str):
                    text_parts.append(item)
                continue
            t = str(item.get('type') or '').lower()
            if t in ('tool_use', 'tool_call', 'tool-invocation', 'function_call'):
                tool_uses.append({
                    'name': str(item.get('name') or item.get('toolName') or (item.get('function') or {}).get('name') or ''),
                    'input': item.get('input') if 'input' in item else item.get('arguments', item.get('args', '')),
                })
            elif t in ('tool_result', 'tool-result'):
                tool_results.append({
                    'name': str(item.get('name') or item.get('toolName') or ''),
                    'is_error': bool(item.get('is_error') or item.get('isError') or item.get('error')),
                    'content': item.get('content', item.get('result', '')),
                })
            elif t == 'text' or 'text' in item:
                text_parts.append(str(item.get('text') or ''))

    if isinstance(raw_content, str):
        stripped = raw_content.strip()
        if stripped.startswith('[') or stripped.startswith('{'):
            try:
                parsed = json.loads(stripped)
                if isinstance(parsed, list):
                    _inspect_list(parsed)
                elif isinstance(parsed, dict):
                    _inspect_list([parsed])
            except json.JSONDecodeError:
                text_parts.append(raw_content)
        else:
            text_parts.append(raw_content)

    if isinstance(raw_tool_calls, str) and raw_tool_calls.strip():
        try:
            parsed_tc = json.loads(raw_tool_calls)
            if isinstance(parsed_tc, list):
                for item in parsed_tc:
                    if isinstance(item, dict):
                        fn = item.get('function') if isinstance(item.get('function'), dict) else {}
                        name = str(item.get('name') or item.get('tool') or fn.get('name') or '')
                        inp = item.get('input', item.get('arguments', fn.get('arguments', '')))
                        if name or inp:
                            tool_uses.append({'name': name, 'input': inp})
        except json.JSONDecodeError:
            pass

    return tool_uses, tool_results, ' '.join(p for p in text_parts if p)


def digest_zcode_db(db_path: Path, session_id: str) -> tuple[list[dict], dict]:
    """Read-only summary of one ZCode SQLite session and its child subagent sessions."""
    uri = f'file:{quote(str(db_path.resolve()))}?mode=ro'
    try:
        conn = sqlite3.connect(uri, uri=True)
    except sqlite3.Error as exc:
        raise ValueError(f'unable to open sqlite read-only: {exc}') from exc
    conn.row_factory = sqlite3.Row
    try:
        tables = {
            row['name']
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        if 'messages' not in tables:
            raise ValueError('unsupported sqlite schema: missing messages table')

        sess_cols = (
            {row['name'] for row in conn.execute('PRAGMA table_info(sessions)')}
            if 'sessions' in tables else set()
        )
        msg_cols = {row['name'] for row in conn.execute('PRAGMA table_info(messages)')}
        if 'session_id' not in msg_cols:
            raise ValueError('unsupported sqlite schema: messages.session_id missing')

        session_ids = [session_id]
        child_ids: list[str] = []
        session_timestamps: list[float] = []
        sess_in_tok = 0
        sess_out_tok = 0
        saw_sess_in = False
        saw_sess_out = False

        if 'sessions' in tables and 'id' in sess_cols:
            root_row = conn.execute('SELECT * FROM sessions WHERE id = ?', (session_id,)).fetchone()
            if root_row is None:
                # Also verify if messages exist even without a sessions row
                msg_exists = conn.execute(
                    'SELECT 1 FROM messages WHERE session_id = ? LIMIT 1', (session_id,)
                ).fetchone()
                if msg_exists is None:
                    raise ValueError(f'session not found: {session_id}')
            parent_col = next((c for c in ('parent_id', 'parent_session_id') if c in sess_cols), None)
            queue = [session_id]
            visited = {session_id}
            while queue:
                cur = queue.pop(0)
                srow = conn.execute('SELECT * FROM sessions WHERE id = ?', (cur,)).fetchone()
                if srow is not None:
                    for tc in ('created_at', 'updated_at', 'finished_at'):
                        if tc in sess_cols:
                            ts = _parse_ts(srow[tc])
                            if ts is not None:
                                session_timestamps.append(ts)
                    for ic in ('input_tokens', 'prompt_tokens'):
                        if ic in sess_cols and _safe_int(srow[ic]) is not None:
                            sess_in_tok += int(srow[ic])
                            saw_sess_in = True
                            break
                    for oc in ('output_tokens', 'completion_tokens'):
                        if oc in sess_cols and _safe_int(srow[oc]) is not None:
                            sess_out_tok += int(srow[oc])
                            saw_sess_out = True
                            break
                if parent_col:
                    for crow in conn.execute(f'SELECT id FROM sessions WHERE {parent_col} = ?', (cur,)):
                        cid = str(crow['id'])
                        if cid not in visited:
                            visited.add(cid)
                            session_ids.append(cid)
                            child_ids.append(cid)
                            queue.append(cid)
        else:
            msg_exists = conn.execute(
                'SELECT 1 FROM messages WHERE session_id = ? LIMIT 1', (session_id,)
            ).fetchone()
            if msg_exists is None:
                raise ValueError(f'session not found: {session_id}')

        placeholders = ','.join('?' for _ in session_ids)
        order_col = 'created_at' if 'created_at' in msg_cols else ('rowid' if 'id' not in msg_cols else 'id')
        msg_rows = conn.execute(
            f'SELECT * FROM messages WHERE session_id IN ({placeholders}) ORDER BY {order_col} ASC',
            session_ids,
        ).fetchall()

        rows: list[dict] = []
        tool_uses = collections.Counter()
        errors_by_tool = collections.Counter()
        seen_calls: dict[tuple[str, str], str] = {}
        repeats = 0
        model_calls = 0
        user_turns = 0
        msg_in_tok = 0
        msg_out_tok = 0
        saw_msg_in = False
        saw_msg_out = False
        msg_timestamps: list[float] = []

        for idx, m in enumerate(msg_rows, 1):
            sid = str(m['session_id'])
            side = 'main' if sid == session_id else 'sub'
            mid = m['id'] if 'id' in msg_cols else idx
            ref = f'{db_path.name}:{sid}:{mid}'
            ts_raw = m['created_at'] if 'created_at' in msg_cols else None
            ts_num = _parse_ts(ts_raw)
            if ts_num is not None:
                msg_timestamps.append(ts_num)
            if 'finished_at' in msg_cols:
                fin_num = _parse_ts(m['finished_at'])
                if fin_num is not None:
                    msg_timestamps.append(fin_num)
            ts_str = _fmt_ts(ts_raw)
            role = str(m['role'] if 'role' in msg_cols else '').lower()

            for ic in ('input_tokens', 'prompt_tokens'):
                if ic in msg_cols and _safe_int(m[ic]) is not None:
                    msg_in_tok += int(m[ic])
                    saw_msg_in = True
                    break
            for oc in ('output_tokens', 'completion_tokens'):
                if oc in msg_cols and _safe_int(m[oc]) is not None:
                    msg_out_tok += int(m[oc])
                    saw_msg_out = True
                    break

            raw_content = m['parts'] if 'parts' in msg_cols and m['parts'] else (m['content'] if 'content' in msg_cols else '')
            raw_tc = m['tool_calls'] if 'tool_calls' in msg_cols else None
            t_uses, t_results, display_text = _extract_zcode_tool_items(raw_content, raw_tc)

            if role == 'assistant':
                model_calls += 1
                if display_text.strip():
                    rows.append({
                        'ref': ref, 'time': ts_str, 'side': side, 'kind': 'assistant_text',
                        'tool': '', 'summary': clip(display_text), 'error': '', 'repeat_of': '',
                    })
                for tu in t_uses:
                    name = tu['name'] or 'unknown'
                    tool_uses[name] += 1
                    key = (name, json.dumps(tu['input'], sort_keys=True, ensure_ascii=False))
                    rep = seen_calls.get(key, '')
                    if rep:
                        repeats += 1
                    seen_calls.setdefault(key, ref)
                    rows.append({
                        'ref': ref, 'time': ts_str, 'side': side,
                        'kind': 'skill_load' if name == 'Skill' else 'tool_use',
                        'tool': name, 'summary': clip(tu['input']), 'error': '', 'repeat_of': rep,
                    })
            elif role == 'user':
                if display_text.strip():
                    user_turns += 1
                    rows.append({
                        'ref': ref, 'time': ts_str, 'side': side, 'kind': 'user',
                        'tool': '', 'summary': clip(display_text), 'error': '', 'repeat_of': '',
                    })
                for tr in t_results:
                    err_flag = 'yes' if tr['is_error'] else ''
                    if err_flag:
                        errors_by_tool[tr['name'] or 'unknown'] += 1
                    rows.append({
                        'ref': ref, 'time': ts_str, 'side': side, 'kind': 'tool_result',
                        'tool': tr['name'], 'summary': clip(tr['content']), 'error': err_flag, 'repeat_of': '',
                    })
            elif role == 'tool':
                is_err = bool('is_error' in msg_cols and m['is_error'])
                tname = str(m['tool_name'] if 'tool_name' in msg_cols else (m['name'] if 'name' in msg_cols else ''))
                if is_err:
                    errors_by_tool[tname or 'unknown'] += 1
                rows.append({
                    'ref': ref, 'time': ts_str, 'side': side, 'kind': 'tool_result',
                    'tool': tname, 'summary': clip(display_text or raw_content),
                    'error': 'yes' if is_err else '', 'repeat_of': '',
                })

        all_ts = sorted(msg_timestamps or session_timestamps)
        wall_duration_min = round((all_ts[-1] - all_ts[0]) / 60.0, 2) if len(all_ts) >= 2 else None
        input_tokens = msg_in_tok if saw_msg_in else (sess_in_tok if saw_sess_in else None)
        output_tokens = msg_out_tok if saw_msg_out else (sess_out_tok if saw_sess_out else None)

        summary = {
            'host': 'zcode',
            'db': str(db_path),
            'session_id': session_id,
            'child_sessions': child_ids,
            'spawns': len(child_ids),
            'rows': len(rows),
            'model_calls': model_calls,
            'tool_calls': sum(tool_uses.values()),
            'tool_uses': dict(tool_uses.most_common()),
            'tool_errors': sum(errors_by_tool.values()),
            'errors_by_tool': dict(errors_by_tool),
            'repeats': repeats,
            'user_turns': user_turns,
            'wall_duration_min': wall_duration_min,
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'first': _fmt_ts(all_ts[0]) if all_ts else None,
            'last': _fmt_ts(all_ts[-1]) if all_ts else None,
        }
        summary['missing_metrics'] = [
            k for k in ('wall_duration_min', 'input_tokens', 'output_tokens') if summary[k] is None
        ]
        return rows, summary
    finally:
        conn.close()


def _print_rows(rows: list[dict], fmt: str) -> None:
    if fmt == 'tsv':
        print('\t'.join(COLUMNS))
        for r in rows:
            print('\t'.join(r[c].replace('\t', ' ') for c in COLUMNS))
    else:
        print('| ' + ' | '.join(COLUMNS) + ' |')
        print('|' + '---|' * len(COLUMNS))
        for r in rows:
            print('| ' + ' | '.join(r[c].replace('|', '\\|') for c in COLUMNS) + ' |')


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('transcript', type=Path, nargs='?')
    ap.add_argument('--zcode-db', type=Path)
    ap.add_argument('--session')
    ap.add_argument('--from-line', type=int, default=1)
    ap.add_argument('--to-line', type=int, default=0)
    ap.add_argument('--format', choices=['md', 'tsv'], default='md')
    ap.add_argument('--stats', action='store_true')
    args = ap.parse_args(argv)

    if args.zcode_db is not None:
        if not args.session:
            print('session_digest: --zcode-db requires --session <session_id>', file=sys.stderr)
            return 2
        if not args.zcode_db.is_file():
            print(f'session_digest: {args.zcode_db} not found', file=sys.stderr)
            return 2
        try:
            rows, summary = digest_zcode_db(args.zcode_db, args.session)
        except ValueError as exc:
            print(f'session_digest: {exc}', file=sys.stderr)
            return 2
        if args.stats:
            print(json.dumps(summary, ensure_ascii=False, indent=1))
            return 0
        _print_rows(rows, args.format)
        return 0

    if args.transcript is None:
        print('session_digest: provide a Claude Code <jsonl> path or --zcode-db <sqlite> --session <id>',
              file=sys.stderr)
        return 2
    if not args.transcript.is_file():
        print(f'session_digest: {args.transcript} not found', file=sys.stderr)
        return 2
    try:
        rows = list(events(args.transcript, args.from_line, args.to_line))
    except ValueError:
        print(f'session_digest: unsupported transcript format in {args.transcript} '
              '(Claude Code jsonl or --zcode-db sqlite; provide an export or an excerpt)', file=sys.stderr)
        return 2
    if args.stats:
        uses = collections.Counter(r['tool'] for r in rows if r['kind'] in ('tool_use', 'skill_load'))
        times = [r['time'] for r in rows if r['time']]
        print(json.dumps({'transcript': str(args.transcript), 'rows': len(rows),
                          'tool_uses': dict(uses.most_common()),
                          'tool_errors': sum(r['error'] == 'yes' for r in rows),
                          'errors_by_tool': dict(collections.Counter(r['tool'] for r in rows if r['error'] == 'yes')),
                          'repeats': sum(bool(r['repeat_of']) for r in rows),
                          'compactions': sum(r['kind'] == 'compaction' for r in rows),
                          'sidechain_rows': sum(r['side'] == 'sub' for r in rows),
                          'user_turns': sum(r['kind'] == 'user' for r in rows),
                          'first': min(times) if times else None, 'last': max(times) if times else None},
                         ensure_ascii=False, indent=1))
        return 0
    _print_rows(rows, args.format)
    return 0


if __name__ == '__main__':
    sys.exit(main())
