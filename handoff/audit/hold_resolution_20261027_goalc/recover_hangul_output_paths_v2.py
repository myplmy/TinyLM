"""Recover already-authored files from a wrong output directory, byte for byte.

No corpus text is authored, rewritten, moved or deleted here. Only explicit
assigned-ID references in four saved reviews can enter the role directory.
"""
from pathlib import Path
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

BASE, AUDIT = inv.BASE, Path(__file__).resolve().parent
source_dir = BASE / "automatic_partial_counter_v1"
owner_dir = BASE / "agents/context_hangul/automatic_partial_counter_v1"
OUT = AUDIT / "HANGUL_OUTPUT_PATH_RECOVERY_V2.json"
inv.require(not OUT.exists(), "new path recovery receipt required")
manifest_path = source_dir / "manifest.json"
manifest = inv.cache.read(manifest_path)
assigned = set(manifest["assignments"]["context_hangul"])
reviews = ["review_003_v2.md", "review_008.md", "review_009.md", "review_010.md"]
names, touched_ids, pins = set(reviews), set(), []
reference = re.compile(r"expanded_train_[0-9]+_v[0-9]+(?:_hold(?:_v[0-9]+)?)?[.](?:txt|md)")
for name in reviews:
    payload = (source_dir / name).read_bytes()
    inv.require(payload == (source_dir / name).read_bytes(), "saved review changed during recovery")
    text = payload.decode("utf-8")
    for line in text.splitlines():
        if not line.startswith("|"):
            continue
        cells = line.split("|")[1:-1]
        found = re.fullmatch(r"(?:expanded_train[:_])?([0-9]+)", cells[0].strip(" `*")) if cells else None
        if found:
            ident = "expanded_train:" + found[1]
            inv.require(ident in assigned, "review row is outside the role assignment")
            touched_ids.add(ident)
    for name_found in reference.findall(text):
        ident = "expanded_train:" + re.match(r"expanded_train_([0-9]+)_", name_found)[1]
        inv.require(ident in assigned, "file reference is outside the role assignment")
        names.add(name_found)
inv.require(len(touched_ids) == 12, "wrong-directory review coverage differs from 12 assigned sources")
# Preserve the sidecar history even when a review uses the shorthand "hold"
# rather than spelling out a sidecar basename. No version is silently chosen.
for path in source_dir.glob("expanded_train_*_v*_hold*.md"):
    found = re.fullmatch(reference.pattern, path.name)
    if found:
        ident = "expanded_train:" + re.match(r"expanded_train_([0-9]+)_", path.name)[1]
        if ident in touched_ids:
            names.add(path.name)
for name in sorted(names):
    source, target = source_dir / name, owner_dir / name
    if not source.exists():
        inv.require(target.is_file(), "referenced author output is absent in both directories: " + name)
        pins.append(dict(path=str(target.relative_to(ROOT)), sha256=inv.file_sha(target),
                         recovery="ALREADY_IN_OWNER_DIRECTORY_REFERENCE_ONLY"))
        continue
    payload = source.read_bytes()
    inv.require(payload == source.read_bytes() and len(payload) < 20_000_000, "unstable or oversized saved output")
    if target.exists():
        inv.require(target.read_bytes() == payload, "owner path has different existing bytes: " + name)
        action = "IDENTICAL_OWNER_FILE_ALREADY_EXISTS"
    else:
        with target.open("xb") as stream:
            stream.write(payload)
        action = "NEW_BYTE_IDENTICAL_COPY_NO_TEXT_REWRITE"
    inv.require(source.read_bytes() == target.read_bytes() == payload, "byte identity failed after copy")
    pins.append(dict(source=str(source.relative_to(ROOT)), source_sha256=inv.file_sha(source),
                     path=str(target.relative_to(ROOT)), sha256=inv.file_sha(target), bytes=len(payload), recovery=action))
result = dict(status="AUTHOR_OUTPUT_PATHS_RECOVERED_NOT_NEW_REVIEW_OR_CACHE_ADMISSION",
              original_author="context_hangul", assigned_sources=sorted(touched_ids), files=pins,
              original_files_preserved=True, deleted=0, moved=0, text_rewrites=0,
              input_manifest_sha256=inv.file_sha(manifest_path), producer_sha256=inv.file_sha(Path(__file__)),
              root_adopted=0, goal_complete=False, training_authorized=False,
              extends_receipt="handoff/audit/hold_resolution_20261027_goalc/HANGUL_OUTPUT_PATH_RECOVERY_V1.json")
inv.write_json(OUT, result)
print(json.dumps(dict(status=result["status"], sources=len(touched_ids), files=len(pins),
                      copies=sum(row["recovery"] == "NEW_BYTE_IDENTICAL_COPY_NO_TEXT_REWRITE" for row in pins)), ensure_ascii=False))
