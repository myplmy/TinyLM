"""Search TinyLM's research Markdown and its explicitly recorded evidence."""

from __future__ import annotations

import argparse
from bisect import bisect_right
from collections import defaultdict
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import posixpath
import re
import shlex
import sqlite3
import sys
from urllib.parse import unquote, urlsplit

from scripts.check_result_conditions import CLAIMS, parse_signatures, validate_signature


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = Path("runs/research_catalog/index.sqlite3")
ONTOLOGY = Path("docs/research_wiki/ontology.json")
METHOD_REVIEWS = Path("docs/research_wiki/방법론_적용_판정.md")
APPLICATION_ID = 0x544C4D52
SCHEMA_VERSION = 2
REVIEW_ORIGINS = ("사용자 실행 보고", "GPT 주도 실험", "실행 주체 미확인")
REVIEW_DECISIONS = ("적용", "유보", "미실행", "미검토", "후속 검증")
REVIEW_HEADER = "| 근거 출처 | 프리셋 | 적용 상태 |"
ARTIFACT_DIRS = tuple(map(Path, ("test_result/evidence", "handoff/audit", "runs/logs", "smoketest_logs")))
ARTIFACT_SUFFIXES = {".md", ".json", ".jsonl", ".txt", ".log", ".csv", ".tsv"}
SOURCE_DIRS = {
    "docs": "reference", "docs/research": "analysis", "docs/review": "review",
    "docs/methods": "method", "docs/research_wiki": "wiki", "test_plan": "plan",
    "test_result": "result", "handoff": "handoff", "ai_dev_tool/Codex": "procedure",
}
KINDS = tuple(SOURCE_DIRS.values())
EXPERIMENT = re.compile(r"(?<![A-Za-z0-9])(P[0-9]{3}[A-Z]?)(?![A-Za-z0-9])")
HEADING = re.compile(r"^[ ]{0,3}#{1,6}[ \t]+(.+?)[ \t]*$")
FENCE = re.compile(r"^[ ]{0,3}([~]{3,}|[\x60]{3,})(.*)$")
ANCHOR = re.compile(r"""<a\s+id=["']([^"']+)["']\s*></a>""")
LINK = re.compile(r"""(?<!!)\[[^\]\n]+\]\(\s*(?:<([^>\n]+)>|([^\s)\n]+))(?:\s+["'][^\n]*?["'])?\s*\)""")
METHOD_REVIEW_SCHEMA = """CREATE TABLE method_review (
    section_id INTEGER NOT NULL REFERENCES section ON DELETE CASCADE,
    origin TEXT NOT NULL, preset TEXT COLLATE NOCASE NOT NULL, decision TEXT NOT NULL,
    PRIMARY KEY(section_id, preset)
)"""
SCHEMA = (
    """CREATE TABLE document (
        path TEXT PRIMARY KEY, kind TEXT NOT NULL, title TEXT NOT NULL,
        project TEXT, sha256 TEXT NOT NULL
    )""",
    """CREATE TABLE section (
        id INTEGER PRIMARY KEY, path TEXT NOT NULL REFERENCES document ON DELETE CASCADE,
        line INTEGER NOT NULL, end_line INTEGER NOT NULL, heading TEXT NOT NULL, anchor TEXT,
        UNIQUE(path, line)
    )""",
    """CREATE TABLE anchor (
        path TEXT NOT NULL REFERENCES document ON DELETE CASCADE, name TEXT NOT NULL,
        section_id INTEGER NOT NULL REFERENCES section ON DELETE CASCADE, PRIMARY KEY(path, name)
    )""",
    """CREATE TABLE citation (
        source INTEGER NOT NULL REFERENCES section ON DELETE CASCADE,
        target TEXT NOT NULL REFERENCES document ON DELETE CASCADE, fragment TEXT NOT NULL,
        PRIMARY KEY(source, target, fragment)
    )""",
    """CREATE TABLE comparison (
        id INTEGER PRIMARY KEY, section_id INTEGER NOT NULL REFERENCES section ON DELETE CASCADE,
        signature TEXT NOT NULL, line INTEGER NOT NULL, claim TEXT NOT NULL
    )""",
    """CREATE TABLE condition (
        comparison_id INTEGER NOT NULL REFERENCES comparison ON DELETE CASCADE,
        field TEXT NOT NULL, arm_a TEXT NOT NULL, arm_b TEXT NOT NULL, evidence TEXT NOT NULL,
        PRIMARY KEY(comparison_id, field)
    )""",
    METHOD_REVIEW_SCHEMA,
    """CREATE TABLE concept (id TEXT PRIMARY KEY, label TEXT NOT NULL)""",
    """CREATE TABLE alias (
        text TEXT NOT NULL, normalized TEXT PRIMARY KEY,
        concept_id TEXT NOT NULL REFERENCES concept ON DELETE CASCADE
    )""",
    """CREATE TABLE issue (
        path TEXT NOT NULL REFERENCES document ON DELETE CASCADE, message TEXT NOT NULL
    )""",
    """CREATE TABLE metadata (id INTEGER PRIMARY KEY CHECK(id = 1), built_at TEXT NOT NULL)""",
    "CREATE INDEX citation_target ON citation(target, fragment)",
    "CREATE INDEX comparison_section ON comparison(section_id, claim)",
    "CREATE INDEX document_project ON document(project, kind)",
    """CREATE VIRTUAL TABLE section_fts USING fts5(
        heading, body, context, content='', tokenize='unicode61'
    )""",
)


@dataclass
class Section:
    line: int
    end_line: int
    heading: str
    anchors: list[str]


def inside_source(root: Path, path: Path) -> bool:
    if not path.is_relative_to(root) or ".." in path.relative_to(root).parts or path.is_symlink():
        return False
    return all(not parent.is_symlink() for parent in path.parents if parent.is_relative_to(root))


def documents(root: Path):
    for directory, kind in SOURCE_DIRS.items():
        parent = root / directory
        if not inside_source(root, parent):
            continue
        for path in sorted(parent.glob("*.md")):
            if inside_source(root, path) and path.is_file():
                yield path, kind
    for name in ("AGENTS.md", "README.md"):
        path = root / name
        if inside_source(root, path) and path.is_file():
            yield path, "procedure"


def markup_lines(lines: list[str]) -> list[str]:
    active = []
    fence = None
    for line in lines:
        match = FENCE.match(line)
        if match and fence is None:
            fence = match[1]
            active.append("")
        elif fence is not None:
            if match and match[1].startswith(fence) and not match[2].strip():
                fence = None
            active.append("")
        else:
            active.append(line)
    return active


def split_sections(lines: list[str], default_title: str) -> tuple[str, list[Section]]:
    heads = [(i, re.sub(r"\s+#+$", "", match[1]).strip())
             for i, line in enumerate(lines) if (match := HEADING.match(line))]
    title = heads[0][1] if heads else default_title
    starts = heads if heads and heads[0][0] == 0 else [(0, title), *heads]
    numbers = [index for index, _ in starts]
    sections = [Section(i + 1, end, head, [])
                for (i, head), end in zip(starts, [*numbers[1:], len(lines)], strict=True)]
    for i, text in enumerate(lines):
        names = ANCHOR.findall(text)
        if not names:
            continue
        at = bisect_right(numbers, i) - 1
        if at + 1 < len(numbers) and all(
                not x.strip() or ANCHOR.fullmatch(x.strip()) for x in lines[i + 1:numbers[at + 1]]):
            at += 1
        sections[at].anchors.extend(names)
    return title, sections


def target_for(path: str, link: str, root: Path) -> tuple[str, str] | None:
    try:
        url = urlsplit(link)
    except ValueError:
        return None
    if url.scheme or url.netloc:
        return None
    name = unquote(url.path)
    if name.startswith("/"):
        if not name.startswith(root.as_posix() + "/"):
            return None
        name = posixpath.normpath(name[len(root.as_posix()) + 1:])
    elif name:
        name = posixpath.normpath(posixpath.join(posixpath.dirname(path), name))
    else:
        name = path
    return name, unquote(url.fragment)


def normalized(text: str) -> str:
    return " ".join(text.casefold().split())


def add_ontology(db: sqlite3.Connection, root: Path) -> None:
    path = root / ONTOLOGY
    if not inside_source(root, path):
        raise ValueError("온톨로지 파일은 저장소의 일반 파일이어야 합니다.")
    source = json.loads(path.read_text(encoding="utf-8"))
    if source.get("version") != 1:
        raise ValueError("지원되는 온톨로지 어휘 버전은 1입니다.")
    for concept in source["concepts"]:
        ident, label = concept["id"], concept["label"]
        forms = {normalized(name): name for name in (label, *concept["aliases"])}
        if not re.fullmatch(r"[a-z][a-z0-9_-]*", ident) or not all(forms):
            raise ValueError(f"빈 별칭이나 잘못된 개념 ID가 있습니다. {ident}")
        db.execute("INSERT INTO concept VALUES (?, ?)", (ident, label))
        db.executemany("INSERT INTO alias VALUES (?, ?, ?)",
                       [(name, key, ident) for key, name in forms.items()])


def method_review_rows(section: Section, lines: list[str]) -> list[tuple[str, str, str]]:
    location = f"{METHOD_REVIEWS}:{section.line}"
    headers = [i for i, line in enumerate(lines) if line.strip() == REVIEW_HEADER]
    if len(section.anchors) != 1 or len(headers) != 1:
        raise ValueError(f"방법론 절에 앵커 하나와 판정 표 하나가 필요합니다. {location}")
    delimiter = headers[0] + 1
    if delimiter >= len(lines) or not re.fullmatch(r"\|\s*(?::?-{3,}:?\s*\|\s*){3}", lines[delimiter].strip()):
        raise ValueError(f"방법론 판정 표의 구분 행이 잘못됐습니다. {location}")
    rows, presets = [], set()
    for line in lines[delimiter + 1:]:
        line = line.strip()
        if not line.startswith("|"):
            break
        fields = [cell.strip() for cell in line[1:-1].split("|")]
        if not line.endswith("|") or len(fields) != 3:
            raise ValueError(f"방법론 판정 행에 세 열이 필요합니다. {location} {line}")
        origin, preset, decision = fields
        if origin not in REVIEW_ORIGINS or decision not in REVIEW_DECISIONS or not preset:
            raise ValueError(f"방법론 판정 행의 값이 잘못됐습니다. {location} {line}")
        if preset.casefold() in presets:
            raise ValueError(f"같은 방법론 절에서 프리셋이 중복됐습니다. {location} {preset}")
        presets.add(preset.casefold())
        rows.append((origin, preset, decision))
    if not rows:
        raise ValueError(f"방법론 판정 표에 판정 행이 필요합니다. {location}")
    return rows


def add_document(db: sqlite3.Connection, root: Path, path: Path, kind: str) -> list[tuple[int, str, str]]:
    rel = path.relative_to(root).as_posix()
    raw = path.read_bytes()
    lines = raw.decode("utf-8-sig").splitlines()
    active = markup_lines(lines)
    title, sections = split_sections(active, path.stem)
    project = EXPERIMENT.search(path.stem) if kind in {"plan", "result"} else None
    db.execute("INSERT INTO document VALUES (?, ?, ?, ?, ?)",
               (rel, kind, title, project[0] if project else None, sha256(raw).hexdigest()))
    section_ids, pending = [], []
    review_doc = rel == METHOD_REVIEWS.as_posix()
    review_anchors = set()
    for section in sections:
        section_id = db.execute("INSERT INTO section(path,line,end_line,heading,anchor) VALUES (?,?,?,?,?)",
                                (rel, section.line, section.end_line, section.heading,
                                 next(iter(section.anchors), None))).lastrowid
        section_ids.append(section_id)
        body = "\n".join(lines[section.line - 1:section.end_line])
        db.execute("INSERT INTO section_fts(rowid,heading,body,context) VALUES (?,?,?,?)",
                   (section_id, section.heading, body, f"{title} {rel} {' '.join(section.anchors)}"))
        db.executemany("INSERT OR IGNORE INTO anchor VALUES (?, ?, ?)",
                       [(rel, name, section_id) for name in section.anchors])
        section_markup = active[section.line - 1:section.end_line]
        if review_doc and section_markup and re.match(r"^ {0,3}##[ \t]+", section_markup[0]):
            records = method_review_rows(section, section_markup)
            anchor = section.anchors[0]
            if anchor in review_anchors:
                raise ValueError(f"방법론 판정 문서에서 앵커가 중복됐습니다. {rel}#{anchor}")
            review_anchors.add(anchor)
            db.executemany("INSERT INTO method_review VALUES (?, ?, ?, ?)",
                           [(section_id, *row) for row in records])
        for text in section_markup:
            for angle, bare in LINK.findall(text):
                target = target_for(rel, angle or bare, root)
                if target is not None:
                    pending.append((section_id, *target))
    if review_doc and not review_anchors:
        raise ValueError(f"방법론 판정 문서에 앵커가 있는 2단계 제목이 필요합니다. {rel}")
    if kind == "result":
        signatures, issues = parse_signatures("\n".join(active))
        positions = [section.line for section in sections]
        # A partially parsed table may look compatible after a damaged row is
        # omitted. Keep its text searchable and withhold typed comparisons.
        for signature in (() if issues else signatures):
            invalid = validate_signature(signature)
            if invalid:
                issues.extend(invalid)
                continue
            part = section_ids[bisect_right(positions, signature.line) - 1]
            comparison_id = db.execute(
                "INSERT INTO comparison(section_id,signature,line,claim) VALUES (?,?,?,?)",
                (part, signature.ident, signature.line, signature.rows["permitted_claim"].arm_a),
            ).lastrowid
            db.executemany("INSERT INTO condition VALUES (?, ?, ?, ?, ?)",
                           [(comparison_id, field, row.arm_a, row.arm_b, row.evidence)
                            for field, row in signature.rows.items()])
        db.executemany("INSERT INTO issue VALUES (?, ?)", [(rel, issue) for issue in issues])
    return pending


def open_index(path: Path, *, writable: bool = False) -> sqlite3.Connection:
    if path.is_symlink() or path.parent.is_symlink():
        raise ValueError("로컬 색인에는 심볼릭 링크를 사용할 수 없습니다.")
    mode = "rwc" if writable else "ro"
    db = sqlite3.connect(f"{path.absolute().as_uri()}?mode={mode}", uri=True)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    return db


def status(db: sqlite3.Connection) -> dict:
    if db.execute("PRAGMA application_id").fetchone()[0] != APPLICATION_ID:
        raise ValueError("TinyLM 연구 색인이 필요합니다. 먼저 refresh를 실행하세요.")
    if db.execute("PRAGMA user_version").fetchone()[0] != SCHEMA_VERSION:
        raise ValueError("색인 스키마 버전이 현재 실행기와 다릅니다. 기존 버전 1은 refresh로 갱신할 수 있습니다.")
    stats = {table: db.execute(f"SELECT count(*) FROM {table}").fetchone()[0] for table in
             ("document", "section", "citation", "comparison", "method_review", "concept", "issue")}
    stats["built_at"] = db.execute("SELECT built_at FROM metadata WHERE id=1").fetchone()[0]
    return stats


def refresh(root: Path, database: Path) -> dict:
    if not inside_source(root, database):
        raise ValueError("색인은 저장소의 로컬 실행 디렉터리에 만들어야 합니다.")
    database.parent.mkdir(parents=True, exist_ok=True)
    with closing(open_index(database, writable=True)) as db, db:
        db.execute("BEGIN IMMEDIATE")
        app_id = db.execute("PRAGMA application_id").fetchone()[0]
        if app_id == APPLICATION_ID:
            if db.execute("PRAGMA user_version").fetchone()[0] == 1:
                db.execute(METHOD_REVIEW_SCHEMA)
                db.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
            status(db)
            db.execute("INSERT INTO section_fts(section_fts) VALUES('delete-all')")
            for table in ("document", "concept", "metadata"):
                db.execute(f"DELETE FROM {table}")
        elif app_id == 0 and not db.execute("SELECT 1 FROM sqlite_master LIMIT 1").fetchone():
            for statement in SCHEMA:
                db.execute(statement)
            db.execute(f"PRAGMA application_id = {APPLICATION_ID}")
            db.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
        else:
            raise ValueError("이미 있는 별도 SQLite DB를 연구 색인으로 덮어쓸 수 없습니다.")
        add_ontology(db, root)
        pending = []
        for path, kind in documents(root):
            pending.extend(add_document(db, root, path, kind))
        known = {row["path"] for row in db.execute("SELECT path FROM document")}
        db.executemany("INSERT OR IGNORE INTO citation VALUES (?, ?, ?)",
                       (link for link in pending if link[1] in known))
        ungrounded = db.execute("""
            SELECT s.path, s.line FROM section s JOIN method_review r ON r.section_id=s.id
            WHERE NOT EXISTS (
                SELECT 1 FROM citation c JOIN document d ON d.path=c.target
                WHERE c.source=s.id AND d.kind='result' AND (c.fragment='' OR EXISTS (
                    SELECT 1 FROM anchor a WHERE a.path=c.target AND a.name=c.fragment))
            ) LIMIT 1
        """).fetchone()
        if ungrounded:
            raise ValueError(f"방법론 절에서 실제 결과 근거를 찾지 못했습니다. {ungrounded['path']}:{ungrounded['line']}")
        db.execute("INSERT INTO metadata VALUES(1,?)", (datetime.now(timezone.utc).isoformat(timespec="seconds"),))
        return status(db)


def search_expression(db: sqlite3.Connection, query: str) -> str:
    aliases = defaultdict(list)
    forms = {}
    for row in db.execute("SELECT text, normalized, concept_id FROM alias ORDER BY normalized"):
        aliases[row["concept_id"]].append(row["text"])
        forms[row["normalized"]] = row["concept_id"]
    parts = shlex.split(query)
    max_words = max((len(name.split()) for name in forms), default=1)
    groups = []
    while parts:
        for size in range(min(len(parts), max_words), 1, -1):
            if normalized(" ".join(parts[:size])) in forms:
                parts[:size] = [" ".join(parts[:size])]
                break
        phrase = parts.pop(0)
        if not any(char.isalnum() for char in phrase):
            continue
        variants = aliases[forms[normalized(phrase)]] if normalized(phrase) in forms else [phrase]
        exact = re.fullmatch(r"[A-Za-z0-9]+(?:_[A-Za-z0-9]+){2,}", phrase)
        quoted = ['"' + term.replace('"', '""') + '"' + ("" if exact else " *") for term in variants]
        groups.append("(" + " OR ".join(quoted) + ")")
    return " AND ".join(groups)


def comparison_where(args: argparse.Namespace, *, alias: str = "c") -> tuple[str, list[str]]:
    clauses, values = [], []
    if args.claim:
        clauses.append(f"{alias}.claim = ?")
        values.append(args.claim)
    pairs = [(field, value) for field, value in
             (("eval_dataset", args.dataset), ("tokenizer", args.tokenizer)) if value]
    if pairs:
        arms = []
        for arm in ("arm_a", "arm_b"):
            arms.append("(" + " AND ".join(
                f"EXISTS (SELECT 1 FROM condition v WHERE v.comparison_id={alias}.id AND v.field=? AND v.{arm}=?)"
                for _ in pairs
            ) + ")")
            values.extend(value for pair in pairs for value in pair)
        clauses.append("(" + " OR ".join(arms) + ")")
    return " AND ".join(clauses), values


def search(db: sqlite3.Connection, args: argparse.Namespace) -> list[dict]:
    relation = ""
    clauses, values = [], []
    expression = search_expression(db, args.query)
    if expression:
        relation = "JOIN section_fts ON section_fts.rowid=s.id"
        clauses.append("section_fts MATCH ?")
        values.append(expression)
    elif args.query:
        raise ValueError("검색어에 문자나 숫자를 입력하세요.")
    if args.kind:
        clauses.append("d.kind = ?")
        values.append(args.kind)
    review_filters = [(column, value) for column, value in
                      (("origin", args.origin), ("preset", args.preset), ("decision", args.decision)) if value]
    review_where = " AND ".join(f"r.{column} = ?" for column, _ in review_filters)
    review_values = [value for _, value in review_filters]
    if args.project:
        project = args.project.upper()
        if review_filters:
            clauses.append("""(d.project = ? OR EXISTS (
                SELECT 1 FROM citation ref JOIN document target ON target.path=ref.target
                WHERE ref.source=s.id AND target.project=?))""")
            values.extend((project, project))
        else:
            clauses.append("d.project = ?")
            values.append(project)
    if review_filters:
        clauses.append(f"EXISTS (SELECT 1 FROM method_review r WHERE r.section_id=s.id AND {review_where})")
        values.extend(review_values)
    restrictions, extra = comparison_where(args)
    if restrictions:
        clauses.append(f"EXISTS (SELECT 1 FROM comparison c WHERE c.section_id=s.id AND {restrictions})")
        values.extend(extra)
    where = "WHERE " + " AND ".join(clauses) if clauses else ""
    order = "bm25(section_fts,3,1,.5), " if expression else ""
    rows = db.execute(
        f"""SELECT d.path,d.kind,d.sha256,s.line,s.end_line,s.heading,s.anchor,s.id AS section_id
            FROM section s JOIN document d ON d.path=s.path {relation} {where}
            ORDER BY {order} d.path,s.line LIMIT ?""", (*values, args.limit),
    )
    hits = [dict(row) for row in rows]
    for hit in hits:
        section_id = hit.pop("section_id")
        if review_filters:
            hit["method_reviews"] = [dict(row) for row in db.execute(
                f"""SELECT r.origin,r.preset,r.decision FROM method_review r
                    WHERE r.section_id=? AND {review_where} ORDER BY r.preset""",
                (section_id, *review_values),
            )]
    return hits


def related(db: sqlite3.Connection, reference: str, limit: int) -> list[dict]:
    path, _, fragment = reference.partition("#")
    wanted = db.execute("SELECT 1 FROM document WHERE path=?", (path,)).fetchone()
    if not wanted:
        raise ValueError(f"색인에 없는 저장소 상대 경로입니다. {path}")
    if fragment and not db.execute("SELECT 1 FROM anchor WHERE path=? AND name=?", (path, fragment)).fetchone():
        raise ValueError(f"색인에서 명시 앵커를 찾지 못했습니다. {fragment}")
    # The resolved target may lack a matching explicit anchor. Its document
    # still participates, with the unresolved fragment retained as evidence.
    query = """
        WITH links(relation,path,kind,sha256,line,heading,anchor) AS (
            SELECT 'cites',t.path,t.kind,t.sha256,s.line,coalesce(s.heading,t.title),nullif(c.fragment,'')
            FROM citation c JOIN section src ON src.id=c.source JOIN document t ON t.path=c.target
            LEFT JOIN anchor a ON a.path=t.path AND a.name=c.fragment LEFT JOIN section s ON s.id=a.section_id
            WHERE src.path=? AND (?='' OR src.id=(SELECT section_id FROM anchor WHERE path=? AND name=?))
            UNION
            SELECT 'cited_by',d.path,d.kind,d.sha256,src.line,src.heading,src.anchor
            FROM citation c JOIN section src ON src.id=c.source JOIN document d ON d.path=src.path
            WHERE c.target=? AND (?='' OR c.fragment=?)
        ) SELECT * FROM links
        ORDER BY relation,path,line LIMIT ?
    """
    return [dict(row) for row in db.execute(query, (path, fragment, path, fragment, path, fragment, fragment, limit))]


def wiki_data(db: sqlite3.Connection, project: str, limit: int) -> dict:
    docs = [dict(row) for row in db.execute("""
        SELECT d.path,d.title,d.kind,d.sha256 FROM document d WHERE d.project=?
        OR (d.kind IN ('wiki','analysis','review') AND EXISTS(
            SELECT 1 FROM section s JOIN citation link ON link.source=s.id
            JOIN document t ON t.path=link.target WHERE s.path=d.path AND t.project=?))
        ORDER BY d.kind NOT IN ('plan','result','wiki'),d.kind,d.path DESC LIMIT ?
    """, (project, project, limit))]
    pairs = [dict(row) for row in db.execute("""
        SELECT d.path,d.sha256,s.heading,s.anchor,c.line,c.signature,c.claim,
               t.arm_a,t.arm_b,e.arm_a AS eval_a,e.arm_b AS eval_b
        FROM comparison c JOIN section s ON s.id=c.section_id JOIN document d ON d.path=s.path
        JOIN condition t ON t.comparison_id=c.id AND t.field='comparator_tag'
        JOIN condition e ON e.comparison_id=c.id AND e.field='eval_dataset'
        WHERE d.project=? ORDER BY d.path DESC,c.line DESC LIMIT ?
    """, (project, limit))]
    return dict(project=project, documents=docs, comparisons=pairs)


def source_file(root: Path, relative: str) -> Path:
    path = root / relative
    allowed = relative in ("AGENTS.md", "README.md") or (
        path.suffix == ".md" and Path(relative).parent.as_posix() in SOURCE_DIRS)
    if not allowed or not inside_source(root, path) or not path.is_file():
        raise ValueError(f"허용된 연구 문서 경로가 아닙니다. {relative}")
    return path


def check_sources(root: Path, rows: list[dict]) -> None:
    checked = {}
    for row in rows:
        rel = row["path"]
        if rel not in checked:
            try:
                checked[rel] = sha256(source_file(root, rel).read_bytes()).hexdigest()
            except (OSError, ValueError):
                checked[rel] = None
        row["stale"] = checked[rel] != row["sha256"]


def show(db: sqlite3.Connection, root: Path, reference: str, limit: int, *, section_start: bool = False) -> dict:
    relative, has_anchor, anchor = reference.partition("#")
    line = None
    if not has_anchor:
        name, _, suffix = relative.rpartition(":")
        if name and re.fullmatch(r"[0-9]+", suffix):
            relative, line = name, int(suffix)
    indexed = db.execute("SELECT sha256 FROM document WHERE path=?", (relative,)).fetchone()
    if indexed is None:
        raise ValueError(f"색인에 없는 저장소 상대 경로입니다. {relative}")
    path = source_file(root, relative)
    raw = path.read_bytes()
    lines = raw.decode("utf-8-sig").splitlines()
    if not lines:
        raise ValueError(f"문서에 읽을 내용이 없습니다. {relative}")
    _, sections = split_sections(markup_lines(lines), path.stem)
    if has_anchor:
        section = next((item for item in sections if anchor in item.anchors), None)
    elif line is not None:
        section = next((item for item in sections if item.line <= line <= item.end_line), None)
    else:
        section = sections[0]
    if section is None:
        raise ValueError(f"현재 원문에서 지정한 절을 찾지 못했습니다. {reference}")
    start = line if line is not None and not section_start else section.line
    end = min(section.end_line, start + limit - 1)
    digest = sha256(raw).hexdigest()
    return dict(path=relative, heading=section.heading, anchor=anchor or next(iter(section.anchors), None),
                line=start, end_line=end, next_line=end + 1 if end < section.end_line else None,
                sha256=digest, stale=digest != indexed["sha256"], text="\n".join(lines[start - 1:end]))


def artifact_paths(db: sqlite3.Connection, root: Path, reference: str, limit: int) -> dict:
    source = show(db, root, reference, sys.maxsize, section_start=True)
    found = {}
    for number, line in enumerate(markup_lines(source.pop("text").splitlines()), start=source["line"]):
        for angle, bare in LINK.findall(line):
            target = target_for(source["path"], angle or bare, root)
            if target is None or target[0] in found:
                continue
            relative = Path(target[0])
            is_result_log = relative.parent == Path("test_result") and re.match(r"[0-9]{3}_log_", relative.name)
            if relative.suffix.lower() not in ARTIFACT_SUFFIXES or not (
                    is_result_log or any(relative.is_relative_to(directory) for directory in ARTIFACT_DIRS)):
                continue
            path = root / relative
            if inside_source(root, path):
                found[target[0]] = dict(path=target[0], source_line=number, present=path.is_file())
    return dict(path=source["path"], anchor=source["anchor"], heading=source["heading"],
                stale=source["stale"], count=len(found), artifacts=list(found.values())[:limit])


def source_label(row: dict) -> str:
    if row["stale"]:
        return row["path"] + " (갱신 필요)"
    if row.get("anchor"):
        return row["path"] + "#" + row["anchor"]
    if row.get("line"):
        return f"{row['path']}:{row['line']}"
    return row["path"]


def parser() -> argparse.ArgumentParser:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--json", action="store_true", help="기계 판독용 JSON")
    commands = cli.add_subparsers(dest="command", required=True)
    commands.add_parser("refresh", help="Markdown 색인과 근거 링크를 갱신")
    commands.add_parser("status", help="색인 구축 시각과 항목 수 확인")
    find = commands.add_parser("search", help="문서 절을 검색하고 필요시 실험 조건으로 제한")
    find.add_argument("query", nargs="?", default="")
    find.add_argument("--kind", choices=sorted(set(KINDS)))
    find.add_argument("--project")
    find.add_argument("--claim", choices=sorted(CLAIMS))
    find.add_argument("--dataset", help="정확한 eval_dataset 값")
    find.add_argument("--tokenizer", help="정확한 tokenizer 값")
    find.add_argument("--origin", choices=REVIEW_ORIGINS, help="방법론을 판단한 근거의 출처")
    find.add_argument("--preset", help="방법론 판정 표의 프리셋 이름")
    find.add_argument("--decision", choices=REVIEW_DECISIONS, help="방법론의 적용 판정")
    links = commands.add_parser("related", help="문서 또는 명시 앵커에서 원문 링크를 추적")
    links.add_argument("reference")
    artifacts = commands.add_parser("artifacts", help="원문 절에서 직접 인용한 로컬 검산 파일과 로그 경로를 확인")
    artifacts.add_argument("reference", help="저장소 상대 경로#앵커 또는 경로:줄번호")
    excerpt = commands.add_parser("show", help="앵커나 줄 번호로 현재 원문 절을 읽기")
    excerpt.add_argument("reference", help="저장소 상대 경로, 경로#앵커 또는 경로:줄번호")
    excerpt.add_argument("--lines", type=int, default=80)
    view = commands.add_parser("wiki", help="실험 번호의 문서와 검증된 비교 링크")
    view.add_argument("project")
    for command in (find, links, artifacts, view):
        command.add_argument("--limit", type=int, default=12)
    return cli


def main() -> int:
    cli = parser()
    args = cli.parse_args()
    if getattr(args, "limit", 1) not in range(1, 101):
        cli.error("--limit은 1~100 범위입니다.")
    if getattr(args, "lines", 1) not in range(1, 1001):
        cli.error("--lines는 1~1000 범위입니다.")
    database = ROOT / DB_PATH
    try:
        if not inside_source(ROOT, database):
            raise ValueError("색인은 저장소의 로컬 실행 디렉터리에 있어야 합니다.")
        if args.command == "refresh":
            result = refresh(ROOT, database)
        else:
            with closing(open_index(database)) as db:
                db.execute("BEGIN")
                stats = status(db)
                if args.command == "search":
                    result = search(db, args)
                elif args.command == "related":
                    result = related(db, args.reference, args.limit)
                elif args.command == "artifacts":
                    result = artifact_paths(db, ROOT, args.reference, args.limit)
                elif args.command == "show":
                    result = show(db, ROOT, args.reference, args.lines)
                elif args.command == "wiki":
                    result = wiki_data(db, args.project.upper(), args.limit)
                else:
                    result = stats
        if isinstance(result, list):
            check_sources(ROOT, result)
        elif args.command == "wiki":
            check_sources(ROOT, result["documents"] + result["comparisons"])
    except (OSError, ValueError, sqlite3.Error) as error:
        print(f"연구 색인 조회 또는 갱신 실패. {error}", file=sys.stderr)
        return 1
    if args.json or args.command in {"refresh", "status"}:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.command == "show":
        stale = " (현재 원문, 색인 갱신 필요)" if result["stale"] else ""
        print(f"{result['path']}:{result['line']}{stale}\n")
        print(result["text"])
        if result["next_line"]:
            print(f"\n계속 읽기 {result['path']}:{result['next_line']}")
    elif args.command == "artifacts":
        stale = " (현재 원문, 색인 갱신 필요)" if result["stale"] else ""
        print(f"{result['heading']}{stale} · 경로 {result['count']}개")
        for item in result["artifacts"]:
            availability = "있음" if item["present"] else "로컬 파일 누락"
            print(f"{availability}\t{item['path']}\t{result['path']}:{item['source_line']}")
        if result["count"] > len(result["artifacts"]):
            print("더 보려면 --limit 값을 늘리세요.")
    elif args.command == "wiki":
        print("#", result["project"])
        for row in result["documents"]:
            print(f"- {row['kind']} {row['title']}  {source_label(row)}")
        if result["comparisons"]:
            print("\n## 비교 조건")
            for row in result["comparisons"]:
                print(f"- {row['claim']} {row['signature']}  {row['arm_a']} ↔ {row['arm_b']}")
                print(f"  평가 {row['eval_a']} / {row['eval_b']}  {source_label(row)}")
    elif result:
        for row in result:
            print(f"{row.get('relation', row['kind'])}\t{row['heading']}\t{source_label(row)}")
            for review in row.get("method_reviews", ()):
                print(f"  {review['preset']} · {review['decision']} · {review['origin']}")
    else:
        print("일치하는 문서 절이 없습니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
