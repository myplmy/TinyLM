"""Snapshot saved author decisions; flag integrity risks without approving them."""
from collections import Counter
from pathlib import Path
import hashlib
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_policy_v2 as policy

BASE = ROOT / "data_cache/p106b_hold_resolution_v1_20261027_goalc"
AUDIT = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def relative(path):
    return str(path.relative_to(ROOT))


def version(path):
    match = re.search(r"_v([0-9]+)[.]", path.name)
    return int(match[1]) if match else 1


def decisions(directory, expected):
    found = {}
    for review in sorted(directory.glob("review*.md"), key=lambda p: (version(p), p.name)):
        for line in review.read_text().splitlines():
            if not line.startswith("|"):
                continue
            cells = [c.strip() for c in line.split("|")[1:-1]]
            if not cells or not re.fullmatch(r"(?:expanded_train:)?[0-9]+", cells[0]):
                continue
            ident = cells[0] if ":" in cells[0] else "expanded_train:" + cells[0]
            if ident in expected:
                found[ident] = dict(decision=cells[1], review=relative(review), review_sha256=digest(review), review_line=line)
    assert set(found) == set(expected), (directory, set(expected) - set(found))
    return found


def subsequence(original, candidate):
    source = iter(c for c in original if not c.isspace())
    return all(any(a == b for a in source) for b in candidate if not b.isspace())


manual = json.loads((AUDIT / "manual_residual_assignments_v1.json").read_text())["roles"]
family = json.loads((AUDIT / "family_assignments_v1.json").read_text())
output = []
for kind, assignments in [("manual_residual_v1", manual), ("family_resolution_v1", family)]:
    for role, assigned in assignments.items():
        rows = assigned if kind == "manual_residual_v1" else [dict(id=ident) for ident in assigned["ids"]]
        originals = {r["id"]: (ROOT / r["original_path"] if kind == "manual_residual_v1" else
                              BASE / "inventory_v1/review_packets" / (r["id"].replace(":", "_") + ".txt")) for r in rows}
        directory = BASE / "agents" / role / kind
        choices = decisions(directory, originals)
        for ident, source in originals.items():
            choice = choices[ident]
            assert choice["decision"] in {"KEEP", "EDIT", "EXCLUDE"}, (ident, choice)
            row = dict(id=ident, author=role, author_group=kind, source=relative(source),
                       original_text_sha256=digest(source), **choice, root_approved=False)
            if choice["decision"] == "EDIT":
                prefix = ident.replace(":", "_")
                candidates = [p for p in directory.glob(prefix + "*.txt")
                              if re.fullmatch(re.escape(prefix) + r"(?:_v[0-9]+)?[.]txt", p.name)]
                assert candidates, ident
                body = max(candidates, key=version)
                raw = source.read_text()
                clean = body.read_text()
                words = re.compile(r"[A-Za-z0-9_]+|[가-힣]+|[\u3400-\u9fff]+")
                source_words, new_words = Counter(words.findall(raw)), Counter(words.findall(clean))
                additions = dict(new_words - source_words)
                row.update(body=relative(body), clean_text_sha256=digest(body),
                           source_characters=len(raw), clean_characters=len(clean),
                           deletion_only_ignoring_whitespace=subsequence(raw, clean),
                           added_lexical_counts=additions,
                           code_guard=policy.code_preserved(raw, clean),
                           unicode_guard=policy.unicode_examples_preserved(raw, clean))
            output.append(row)
assert len(output) == 229 and len({r["id"] for r in output}) == 229
summary = Counter(r["decision"] for r in output)
value = dict(purpose="SAVED_AUTHOR_CANDIDATES_NOT_ROOT_APPROVAL", rows=output, counts=dict(summary),
             source_sha256=digest(Path(__file__)))
with (AUDIT / "authored_candidates_snapshot_v1.json").open("x", encoding="utf-8") as f:
    json.dump(value, f, ensure_ascii=False, indent=2)
    f.write(chr(10))
print(json.dumps(dict(counts=dict(summary), code_flags=[r["id"] for r in output if r.get("code_guard") is False],
                      unicode_flags=[r["id"] for r in output if r.get("unicode_guard") is False],
                      ordered_deletion_flags=[r["id"] for r in output if r.get("deletion_only_ignoring_whitespace") is False]), ensure_ascii=False))
