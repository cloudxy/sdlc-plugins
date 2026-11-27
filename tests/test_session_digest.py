#!/usr/bin/env python3
"""session_digest.py on a synthetic Claude Code transcript (no real session data in the repository)."""
from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path
_SCRIPTS_DIR = str(_Path(__file__).resolve().parents[1] / 'scripts')  # _SDLC_SCRIPTS_PATH
if _SCRIPTS_DIR not in _sys.path:
    _sys.path.insert(0, _SCRIPTS_DIR)

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts' / 'gates' / 'session_digest.py'
SAMPLE = ROOT / 'tests' / 'fixtures' / 'session-sample.jsonl'


def digest(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *args], text=True, capture_output=True)


class DigestTests(unittest.TestCase):
    def rows(self, path=SAMPLE):
        p = digest(str(path), '--format', 'tsv')
        self.assertEqual(p.returncode, 0, p.stderr)
        lines = p.stdout.splitlines()
        header = lines[0].split('\t')
        return [dict(zip(header, line.split('\t'))) for line in lines[1:] if line and not line.startswith('#')]

    def test_rows_cite_path_and_line(self):
        rows = self.rows()
        self.assertTrue(all(r['ref'].startswith(f'{SAMPLE}:') for r in rows))
        reads = [r for r in rows if r['kind'] == 'tool_use' and r['tool'] == 'Read']
        self.assertEqual([r['ref'].rsplit(':', 1)[1] for r in reads], ['2', '6'])

    def test_errors_and_repeats_are_flagged(self):
        rows = self.rows()
        errors = [r for r in rows if r['kind'] == 'tool_result' and r['error'] == 'yes']
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0]['tool'], 'Bash')  # result mapped back to its tool_use
        second_read = [r for r in rows if r['tool'] == 'Read' and r['kind'] == 'tool_use'][1]
        self.assertEqual(second_read['repeat_of'], f'{SAMPLE}:2')
        kinds = {r['kind'] for r in rows}
        self.assertTrue({'user', 'tool_use', 'tool_result', 'compaction', 'skill_load', 'assistant_text'} <= kinds)
        self.assertTrue(any(r['side'] == 'sub' for r in rows))

    def test_secret_like_values_are_redacted(self):
        p = digest(str(SAMPLE), '--format', 'md')
        self.assertNotIn('abcdefghijklmnopqrstuvwxyz0123', p.stdout)
        self.assertIn('<REDACTED>', p.stdout)

    def test_long_line_is_truncated_and_streamed(self):
        with tempfile.TemporaryDirectory() as d:
            big = Path(d) / 'big.jsonl'
            huge = 'x' * 150_000
            big.write_text(SAMPLE.read_text(encoding='utf-8') + json.dumps(
                {'type': 'user', 'message': {'content': [{'type': 'tool_result', 'tool_use_id': 't9',
                                                          'is_error': False, 'content': huge}]}}) + '\n',
                encoding='utf-8')
            p = digest(str(big), '--format', 'tsv')
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertLess(max(len(line) for line in p.stdout.splitlines()), 600)

    def test_injected_text_is_not_a_user_turn(self):
        with tempfile.TemporaryDirectory() as d:
            t = Path(d) / 's.jsonl'
            t.write_text('\n'.join(json.dumps(r, ensure_ascii=False) for r in [
                {'type': 'user', 'message': {'content': '<task-notification> <task-id>b1</task-id> done</task-notification>'}},
                {'type': 'user', 'message': {'content': '<local-command-caveat>The command below was run directly</local-command-caveat>'}},
                {'type': 'user', 'message': {'content': '为什么是14次？'}},
            ]) + '\n', encoding='utf-8')
            rows = self.rows(t)
            self.assertEqual([r['kind'] for r in rows], ['injected', 'injected', 'user'])
            self.assertIn('task-notification', rows[0]['summary'], 'a tag name is not a secret')

    def test_unknown_format_fails_clearly(self):
        with tempfile.TemporaryDirectory() as d:
            other = Path(d) / 'codex.jsonl'
            other.write_text('\n'.join(json.dumps({'event': 'turn', 'payload': i}) for i in range(5)) + '\n')
            p = digest(str(other))
            self.assertEqual(p.returncode, 2)
            self.assertIn('unsupported', p.stderr)

    def test_stats_summarize_the_session(self):
        p = digest(str(SAMPLE), '--stats')
        self.assertEqual(p.returncode, 0, p.stderr)
        stats = json.loads(p.stdout)
        self.assertEqual(stats['tool_uses']['Read'], 2)
        self.assertEqual(stats['tool_errors'], 1)
        self.assertEqual(stats['repeats'], 1)
        self.assertEqual(stats['compactions'], 1)

    def test_zcode_sqlite_read_only_digest_and_subagents(self):
        import sqlite3
        with tempfile.TemporaryDirectory() as d:
            db = Path(d) / 'zcode.db'
            conn = sqlite3.connect(db)
            conn.executescript("""
                CREATE TABLE sessions (
                    id TEXT PRIMARY KEY,
                    parent_id TEXT,
                    created_at INTEGER,
                    updated_at INTEGER
                );
                CREATE TABLE messages (
                    id TEXT PRIMARY KEY,
                    session_id TEXT,
                    role TEXT,
                    content TEXT,
                    tool_calls TEXT,
                    created_at INTEGER,
                    input_tokens INTEGER,
                    output_tokens INTEGER
                );
            """)
            conn.execute("INSERT INTO sessions VALUES ('sess_root', NULL, 1700000000, 1700000300)")
            conn.execute("INSERT INTO sessions VALUES ('sess_sub1', 'sess_root', 1700000060, 1700000240)")
            conn.execute(
                "INSERT INTO messages VALUES ('m1', 'sess_root', 'user', '分析日志 token=sk-abcdefghijklmnopqrstuvwxyz012345', NULL, 1700000000, NULL, NULL)"
            )
            conn.execute(
                "INSERT INTO messages VALUES ('m2', 'sess_root', 'assistant', '正在派发专家', ?, 1700000030, 12000, 400)",
                (json.dumps([{'name': 'Task', 'input': {'subagent_type': 'sdlc-workflow:sre'}}]),),
            )
            conn.execute(
                "INSERT INTO messages VALUES ('m3', 'sess_sub1', 'assistant', ?, NULL, 1700000120, 8000, 600)",
                (json.dumps([
                    {'type': 'tool_use', 'name': 'Bash', 'input': {'command': 'python3 log_profiler.py'}},
                    {'type': 'text', 'text': '已完成分析'},
                ]),),
            )
            conn.execute(
                "INSERT INTO messages VALUES ('m4', 'sess_sub1', 'user', ?, NULL, 1700000240, NULL, NULL)",
                (json.dumps([{'type': 'tool_result', 'name': 'Bash', 'is_error': True, 'content': 'boom'}]),),
            )
            conn.commit()
            conn.close()

            mtime_before = db.stat().st_mtime_ns
            p = digest('--zcode-db', str(db), '--session', 'sess_root', '--stats')
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertEqual(db.stat().st_mtime_ns, mtime_before)
            self.assertFalse((Path(d) / 'zcode.db-wal').exists())
            s = json.loads(p.stdout)
            self.assertEqual(s['host'], 'zcode')
            self.assertEqual(s['spawns'], 1)
            self.assertEqual(s['child_sessions'], ['sess_sub1'])
            self.assertEqual(s['model_calls'], 2)
            self.assertEqual(s['tool_calls'], 2)
            self.assertEqual(s['tool_errors'], 1)
            self.assertEqual(s['input_tokens'], 20000)
            self.assertEqual(s['output_tokens'], 1000)
            self.assertEqual(s['wall_duration_min'], 4.0)
            self.assertEqual(s['missing_metrics'], [])

            # Timeline view must redact secrets
            pt = digest('--zcode-db', str(db), '--session', 'sess_root', '--format', 'tsv')
            self.assertEqual(pt.returncode, 0, pt.stderr)
            self.assertNotIn('sk-abcdefghijklmnopqrstuvwxyz012345', pt.stdout)
            self.assertIn('<REDACTED>', pt.stdout)


if __name__ == '__main__':
    unittest.main()
