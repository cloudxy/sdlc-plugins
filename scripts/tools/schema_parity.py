#!/usr/bin/env python3
"""Read-only static schema parity checker across SQLAlchemy models, Alembic migrations, DBML, and JSON fixtures.

  python3 scripts/tools/schema_parity.py [--models PATH...] [--migrations PATH...] [--dbml FILE] [--fixture JSON] [--max-ident 64]

Pure Python stdlib (AST + regex); needs no database connection or project virtualenv.
Exit codes: 0 parity ok · 1 drift or identifier-length violation found · 2 usage/input error.
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path
from typing import Any


def _str_const(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _bool_kw(call: ast.Call, name: str) -> bool | None:
    for kw in call.keywords:
        if kw.arg == name and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, bool):
            return kw.value.value
    return None


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


def parse_models(paths: list[str]) -> tuple[dict[str, dict[str, dict[str, Any]]], list[str]]:
    """Static AST extraction of SQLAlchemy model __tablename__, Column/mapped_column names, nullable, and Index names."""
    tables: dict[str, dict[str, dict[str, Any]]] = {}
    indexes: list[str] = []
    files: list[Path] = []
    for raw in paths:
        p = Path(raw).resolve()
        if p.is_dir():
            files.extend(sorted(p.rglob("*.py")))
        elif p.is_file():
            files.append(p)
        else:
            raise ValueError(f"model path not found: {raw}")

    for fp in files:
        tree = ast.parse(fp.read_text(encoding="utf-8", errors="replace"), filename=str(fp))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            tname = None
            cols: dict[str, dict[str, Any]] = {}
            for stmt in node.body:
                if isinstance(stmt, ast.Assign):
                    for tgt in stmt.targets:
                        if isinstance(tgt, ast.Name) and tgt.id == "__tablename__":
                            tname = _str_const(stmt.value)
                        elif isinstance(tgt, ast.Name) and tgt.id == "__table_args__":
                            for sub in ast.walk(stmt.value):
                                if isinstance(sub, ast.Call) and _call_name(sub.func) == "Index" and sub.args:
                                    ix = _str_const(sub.args[0])
                                    if ix:
                                        indexes.append(ix)
                        elif isinstance(tgt, ast.Name) and isinstance(stmt.value, ast.Call):
                            fn = _call_name(stmt.value.func)
                            if fn in ("Column", "mapped_column"):
                                explicit = _str_const(stmt.value.args[0]) if stmt.value.args else None
                                col_name = explicit or tgt.id
                                cols[col_name] = {"nullable": _bool_kw(stmt.value, "nullable")}
                elif isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name) and isinstance(stmt.value, ast.Call):
                    fn = _call_name(stmt.value.func)
                    if fn in ("Column", "mapped_column"):
                        explicit = _str_const(stmt.value.args[0]) if stmt.value.args else None
                        col_name = explicit or stmt.target.id
                        cols[col_name] = {"nullable": _bool_kw(stmt.value, "nullable")}
            if tname and cols:
                tables[tname] = cols
    return tables, indexes


def parse_migrations(paths: list[str]) -> tuple[dict[str, dict[str, dict[str, Any]]], list[str]]:
    """Static AST extraction of Alembic op.create_table and op.create_index definitions."""
    tables: dict[str, dict[str, dict[str, Any]]] = {}
    indexes: list[str] = []
    for raw in paths:
        p = Path(raw).resolve()
        if not p.is_file():
            raise ValueError(f"migration file not found: {raw}")
        tree = ast.parse(p.read_text(encoding="utf-8", errors="replace"), filename=str(p))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            fn = _call_name(node.func)
            if fn == "create_table" and node.args:
                tname = _str_const(node.args[0])
                if not tname:
                    continue
                cols: dict[str, dict[str, Any]] = {}
                for arg in node.args[1:]:
                    if isinstance(arg, ast.Call) and _call_name(arg.func) == "Column" and arg.args:
                        cname = _str_const(arg.args[0])
                        if cname:
                            cols[cname] = {"nullable": _bool_kw(arg, "nullable")}
                if cols:
                    tables[tname] = cols
            elif fn == "create_index" and node.args:
                ix = _str_const(node.args[0])
                if ix:
                    indexes.append(ix)
    return tables, indexes


def parse_dbml(path: str) -> tuple[dict[str, dict[str, dict[str, Any]]], list[str]]:
    """Parse Table <name> { ... } blocks and index names from a DBML file."""
    p = Path(path).resolve()
    if not p.is_file():
        raise ValueError(f"dbml file not found: {path}")
    text = p.read_text(encoding="utf-8", errors="replace")
    tables: dict[str, dict[str, dict[str, Any]]] = {}
    indexes: list[str] = []
    cur_table: str | None = None
    in_indexes = False
    for raw_line in text.splitlines():
        line = re.sub(r"//.*$", "", raw_line).strip()
        if not line:
            continue
        m_tbl = re.match(r'^Table\s+["`]?([A-Za-z0-9_]+)["`]?\s*(?:as\s+\w+\s*)?\{', line, re.I)
        if m_tbl:
            cur_table = m_tbl.group(1)
            tables[cur_table] = {}
            in_indexes = False
            continue
        if cur_table is None:
            continue
        if re.match(r"^indexes\s*\{", line, re.I):
            in_indexes = True
            continue
        if line == "}":
            if in_indexes:
                in_indexes = False
            else:
                cur_table = None
            continue
        if in_indexes:
            m_ix = re.search(r"name\s*:\s*['\"]([^'\"]+)['\"]", line)
            if m_ix:
                indexes.append(m_ix.group(1))
            continue
        if line.lower().startswith("note:"):
            continue
        m_col = re.match(r'^["`]?([A-Za-z0-9_]+)["`]?\s+[A-Za-z0-9_(),]+(.*)$', line)
        if m_col:
            cname = m_col.group(1)
            attrs = m_col.group(2)
            nullable: bool | None = None
            if re.search(r"\bnot\s+null\b|\bpk\b|\bprimary\s+key\b", attrs, re.I):
                nullable = False
            elif re.search(r"\bnull\b", attrs, re.I):
                nullable = True
            tables[cur_table][cname] = {"nullable": nullable}
    return tables, indexes


def parse_fixture(path: str) -> dict[str, dict[str, dict[str, Any]]]:
    """Parse a projected JSON fixture mapping table_name -> list[dict] or dict."""
    p = Path(path).resolve()
    if not p.is_file():
        raise ValueError(f"fixture file not found: {path}")
    data = json.loads(p.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("fixture JSON root must be an object mapping table_name -> rows/object")
    tables: dict[str, dict[str, dict[str, Any]]] = {}
    for tname, val in data.items():
        keys: set[str] = set()
        if isinstance(val, dict):
            keys.update(str(k) for k in val.keys())
        elif isinstance(val, list):
            for row in val:
                if isinstance(row, dict):
                    keys.update(str(k) for k in row.keys())
        tables[tname] = {k: {"nullable": None} for k in sorted(keys)}
    return tables


def check_parity(
    models: list[str] | None = None,
    migrations: list[str] | None = None,
    dbml: str | None = None,
    fixture: str | None = None,
    ignore_cols: set[str] | None = None,
    max_ident: int = 64,
) -> dict[str, Any]:
    sources: dict[str, dict[str, dict[str, dict[str, Any]]]] = {}
    all_indexes: dict[str, list[str]] = {}
    if models:
        t, ix = parse_models(models)
        sources["models"] = t
        all_indexes["models"] = ix
    if migrations:
        t, ix = parse_migrations(migrations)
        sources["migrations"] = t
        all_indexes["migrations"] = ix
    if dbml:
        t, ix = parse_dbml(dbml)
        sources["dbml"] = t
        all_indexes["dbml"] = ix
    if fixture:
        sources["fixture"] = parse_fixture(fixture)

    if len(sources) < 2:
        raise ValueError("provide at least two schema sources among --models, --migrations, --dbml, --fixture")

    ignored = ignore_cols if ignore_cols is not None else {"id", "created_at", "updated_at", "is_deleted"}
    all_tables = sorted({t for src in sources.values() for t in src})
    empty_or_unsupported_sources = sorted(s for s, tbls in sources.items() if not tbls)
    empty_tables: list[dict[str, str]] = [
        {"source": s, "table": t}
        for s, tbls in sources.items()
        for t, cols in tbls.items()
        if not cols
    ]
    table_diffs: list[dict[str, Any]] = []
    column_diffs: list[dict[str, Any]] = []
    nullable_diffs: list[dict[str, Any]] = []
    long_identifiers: list[dict[str, Any]] = []

    for src_name, src_tables in sources.items():
        missing_tables = [t for t in all_tables if t not in src_tables]
        if missing_tables:
            table_diffs.append({"source": src_name, "missing_tables": missing_tables})
        for tname, cols in src_tables.items():
            if len(tname) > max_ident:
                long_identifiers.append({"source": src_name, "kind": "table", "name": tname, "length": len(tname)})
            for cname in cols:
                if len(cname) > max_ident:
                    long_identifiers.append({"source": src_name, "kind": "column", "name": f"{tname}.{cname}", "length": len(cname)})
    for src_name, ixs in all_indexes.items():
        for ix in ixs:
            if len(ix) > max_ident:
                long_identifiers.append({"source": src_name, "kind": "index", "name": ix, "length": len(ix)})

    for tname in all_tables:
        present_in = {s: set(sources[s][tname].keys()) for s in sources if tname in sources[s]}
        if len(present_in) < 2:
            continue
        # Compare schema-authoritative sources strictly; for fixture allow empty rows & ignore base audit columns.
        auth_sources = {s: cols for s, cols in present_in.items() if s != "fixture"}
        if len(auth_sources) >= 2:
            union_cols = set().union(*auth_sources.values())
            for s, cols in auth_sources.items():
                miss = sorted(union_cols - cols)
                if miss:
                    column_diffs.append({"table": tname, "source": s, "missing_columns": miss})
            for col in sorted(union_cols):
                nvals = {
                    s: sources[s][tname][col]["nullable"]
                    for s in auth_sources
                    if col in sources[s][tname] and sources[s][tname][col]["nullable"] is not None
                }
                if len(set(nvals.values())) > 1:
                    nullable_diffs.append({"table": tname, "column": col, "nullable_by_source": nvals})
        if "fixture" in present_in and present_in["fixture"] and auth_sources:
            ref_name = next(iter(auth_sources))
            ref_cols = auth_sources[ref_name]
            extra_in_fixture = sorted(present_in["fixture"] - ref_cols)
            missing_in_fixture = sorted((ref_cols - ignored) - present_in["fixture"])
            if extra_in_fixture:
                column_diffs.append({"table": tname, "source": ref_name, "missing_columns_from_fixture": extra_in_fixture})
            if missing_in_fixture:
                column_diffs.append({"table": tname, "source": "fixture", "unpopulated_non_audit_columns": missing_in_fixture})

    parity_ok = (
        len(all_tables) > 0
        and not empty_or_unsupported_sources
        and not empty_tables
        and not (table_diffs or column_diffs or nullable_diffs or long_identifiers)
    )
    return {
        "sources": {k: len(v) for k, v in sources.items()},
        "tables_checked": len(all_tables),
        "parity_ok": parity_ok,
        "empty_or_unsupported_sources": empty_or_unsupported_sources,
        "empty_tables": empty_tables,
        "table_diffs": table_diffs,
        "column_diffs": column_diffs,
        "nullable_diffs": nullable_diffs,
        "long_identifiers": long_identifiers,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Static schema parity checker across models, migrations, DBML, and fixtures.")
    ap.add_argument("--models", nargs="+")
    ap.add_argument("--migrations", nargs="+")
    ap.add_argument("--dbml")
    ap.add_argument("--fixture")
    ap.add_argument("--max-ident", type=int, default=64)
    args = ap.parse_args(argv)
    try:
        res = check_parity(
            models=args.models,
            migrations=args.migrations,
            dbml=args.dbml,
            fixture=args.fixture,
            max_ident=args.max_ident,
        )
        print(json.dumps(res, ensure_ascii=False, indent=2))
        return 0 if res["parity_ok"] else 1
    except (OSError, ValueError, SyntaxError) as exc:
        print(f"schema_parity: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
