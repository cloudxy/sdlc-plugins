#!/usr/bin/env python3
"""A citable timeline of one Claude Code session transcript (~/.claude/projects/<project>/<session>.jsonl).

  session_digest.py <jsonl> [--from-line N] [--to-line M] [--format md|tsv]
  session_digest.py <jsonl> --stats        JSON counts: tool uses, errors, repeats, compactions, sidechain events, span

Every row cites `path:line`, so a diagnosis finding can point at the exact event. Lines are read one at a time and
each field is cut to 200 characters; secrets are redacted before anything is printed. Rows: user (the person's own
words), injected (text the host placed in a user turn: notifications, hook output, local-command echoes), assistant_text,
tool_use (skill_load for the Skill tool), tool_result (mapped back to its tool, flagged on error), compaction.
`repeat_of` names the earlier identical tool call (same tool and input). Only the Claude Code format is parsed;
other hosts' transcripts are reported as unsupported: provide an export or an excerpt instead.
Exit: 0 ok · 2 usage or unsupported format.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

from behavior_smoke import redact

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


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('transcript', type=Path)
    ap.add_argument('--from-line', type=int, default=1)
    ap.add_argument('--to-line', type=int, default=0)
    ap.add_argument('--format', choices=['md', 'tsv'], default='md')
    ap.add_argument('--stats', action='store_true')
    args = ap.parse_args(argv)
    if not args.transcript.is_file():
        print(f'session_digest: {args.transcript} not found', file=sys.stderr)
        return 2
    try:
        rows = list(events(args.transcript, args.from_line, args.to_line))
    except ValueError:
        print(f'session_digest: unsupported transcript format in {args.transcript} '
              '(Claude Code jsonl only; provide an export or an excerpt)', file=sys.stderr)
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
    if args.format == 'tsv':
        print('\t'.join(COLUMNS))
        for r in rows:
            print('\t'.join(r[c].replace('\t', ' ') for c in COLUMNS))
    else:
        print('| ' + ' | '.join(COLUMNS) + ' |')
        print('|' + '---|' * len(COLUMNS))
        for r in rows:
            print('| ' + ' | '.join(r[c].replace('|', '\\|') for c in COLUMNS) + ' |')
    return 0


if __name__ == '__main__':
    sys.exit(main())
