"""Semantic layer of the diagram gate: the picture must show what its authoritative source says.

Nodes and edges carry data-sdlc-id. The checks are set comparisons, not judgement:
  every type   at least one id; every id appears in some declared source (no invented entities)
  er           every table and every relationship in the DBML source is drawn; relationships are
               written "<table>.<column>-><table>.<column>" (direction and arrow style do not matter)
  flow         ids include journey or requirement ids (J-n / FR-n) and each exists in the spec
DBML support is the subset the plugin's templates use (Table, inline [ref: ...], Ref: / Ref name: / Ref { }).
Anything else that defines structure is reported as UNPARSED rather than guessed.
"""
from __future__ import annotations

import re
from pathlib import Path

ID_ATTR = re.compile(r"""data-sdlc-id\s*=\s*["']([^"']+)["']""")
TABLE = re.compile(r"""^\s*Table\s+("?[\w.]+"?)(?:\s+as\s+\w+)?\s*(?:\[[^\]]*\])?\s*\{""", re.M | re.I)
ENDPOINT = r"""("?[\w]+"?)\.("?[\w]+"?)"""
REL = re.compile(ENDPOINT + r"\s*(?:<>|<|>|-)\s*" + ENDPOINT)
INLINE_REF = re.compile(r"""^\s*("?\w+"?)\s+[^\n\[]*\[[^\]]*\bref\s*:\s*(?:<>|<|>|-)\s*""" + ENDPOINT, re.M | re.I)
COMPOSITE = re.compile(r"\w+\.\(\s*\w+\s*,")


def table_blocks(text: str):
    """Yield (table name, body) with braces matched, so an `indexes { … }` block does not end the table early."""
    for m in re.finditer(r"""^\s*Table\s+("?[\w.]+"?)[^{\n]*\{""", text, re.M | re.I):
        depth, i = 1, m.end()
        while i < len(text) and depth:
            depth += {"{": 1, "}": -1}.get(text[i], 0)
            i += 1
        yield m.group(1), text[m.end():i - 1]


def _clean(s: str) -> str:
    return s.strip().strip('"').split(".")[-1].lower()


def rel_key(a_t, a_c, b_t, b_c) -> str:
    ends = sorted([f"{_clean(a_t)}.{_clean(a_c)}", f"{_clean(b_t)}.{_clean(b_c)}"])
    return f"{ends[0]}~{ends[1]}"


def parse_dbml(text: str) -> tuple[set[str], set[str], list[str]]:
    text = re.sub(r"//[^\n]*", "", text)
    tables, rels, unparsed = set(), set(), []
    for m in TABLE.finditer(text):
        tables.add(_clean(m.group(1)))
    # inline refs: need the owning table, so walk table blocks
    for name, body in table_blocks(text):
        owner = _clean(name)
        for im in INLINE_REF.finditer(body):
            rels.add(rel_key(owner, im.group(1), im.group(2), im.group(3)))
    for m in re.finditer(r"""^\s*Ref\b[^:{\n]*[:{](.*?)(?:\}|$)""", text, re.M | re.S | re.I):
        body = m.group(1)
        if COMPOSITE.search(body):
            unparsed.append(f"composite reference: {body.strip()[:60]}")
            continue
        found = False
        for rm in REL.finditer(body):
            rels.add(rel_key(*rm.groups()))
            found = True
        if not found:
            unparsed.append(f"reference: {body.strip()[:60]}")
    for kw in re.findall(r"^\s*(TablePartial|Records)\b", text, re.M):
        unparsed.append(f"{kw} block")
    return tables, rels, unparsed


def diagram_ids(svg_text: str) -> set[str]:
    return {i.strip() for i in ID_ATTR.findall(svg_text)}


def diagram_rel(i: str) -> str | None:
    m = re.fullmatch(r"\s*" + ENDPOINT + r"\s*(?:<->|->|<-|<>|>|<|-|~)\s*" + ENDPOINT + r"\s*", i)
    return rel_key(*m.groups()) if m else None


def check(svg_path: Path, dtype: str, sources: list[Path]) -> list[str]:
    """Return problems (empty = the diagram agrees with its sources)."""
    probs: list[str] = []
    ids = diagram_ids(svg_path.read_text(encoding="utf-8", errors="replace"))
    if dtype == "other":
        return probs
    if not ids:
        return [f"{svg_path.name}: no data-sdlc-id on any node or edge — the gate cannot tell what the picture claims"]
    texts = {p: p.read_text(encoding="utf-8", errors="replace") for p in sources}
    alltext = "\n".join(texts.values())
    if dtype == "er":
        dbml = [p for p in sources if p.suffix == ".dbml"]
        if not dbml:
            return [f"{svg_path.name}: an ER diagram needs a .dbml source"]
        tables, rels, unparsed = set(), set(), []
        for p in dbml:
            t, r, u = parse_dbml(texts[p])
            tables |= t; rels |= r; unparsed += [f"{p.name}: {x}" for x in u]
        probs += [f"UNPARSED {x} — draw it and check by hand, or express it in the supported subset" for x in unparsed]
        drawn_rels = {k for k in (diagram_rel(i) for i in ids) if k}
        drawn_tables = {_clean(i) for i in ids if diagram_rel(i) is None and "." not in i}
        for t in sorted(tables - drawn_tables):
            probs.append(f"{svg_path.name}: table {t} is in the DBML but not drawn")
        for t in sorted(drawn_tables - tables):
            probs.append(f"{svg_path.name}: table {t} is drawn but not in the DBML")
        for r in sorted(rels - drawn_rels):
            probs.append(f"{svg_path.name}: relationship {r.replace('~', ' — ')} is in the DBML but not drawn")
        for r in sorted(drawn_rels - rels):
            probs.append(f"{svg_path.name}: relationship {r.replace('~', ' — ')} is drawn but not in the DBML")
        return probs
    if dtype == "flow":
        refs = {i for i in ids if re.fullmatch(r"(J|FR)-\d+[a-z]?", i)}
        if not refs:
            probs.append(f"{svg_path.name}: a flow must name the journeys or requirements it shows (data-sdlc-id J-n / FR-n)")
    for i in sorted(ids):
        if diagram_rel(i):
            a, b = [x.strip() for x in re.split(r"<->|->|<-|<>|>|<|~", i, maxsplit=1)]
            tokens = [a.split(".")[0], b.split(".")[0]]
        else:
            tokens = [i]
        for tok in tokens:
            if not re.search(r"(?<![\w-])" + re.escape(tok) + r"(?![\w-])", alltext, re.I):
                probs.append(f"{svg_path.name}: '{tok}' is drawn but appears in none of the sources")
    return probs
