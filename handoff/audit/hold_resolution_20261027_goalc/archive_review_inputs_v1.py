"""Archive stable current review bytes and preserve missing prior review rows."""
from collections import defaultdict
from pathlib import Path
import json
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv
from scripts import p106b_hold_resolution_revision_v7 as failed_revision

AUDIT = Path(__file__).resolve().parent
BASE = inv.BASE / "agents"
out = AUDIT / "review_archive_v1"
out.mkdir(exist_ok=True)
groups = ["manual_residual_v1", "family_resolution_v1", "profile_resolution_v1",
          "extra_draft_repairs_v1", "legacy_span_review_v2"]
roles = ["context_controls", "context_hangul", "context_latin", "historical_review", "legacy_review"]
pins = []
skipped = []
for role in roles:
    for group in groups:
        directory = BASE / role / group
        for path in sorted(directory.glob("*review*.md")):
            raw = path.read_bytes()
            if raw != path.read_bytes():
                skipped.append(str(path.relative_to(ROOT)))
                continue
            inv.require(len(raw) < 20_000_000, "split large review archive")
            digest = inv.sha(raw.decode("utf-8"))
            archived = out / digest[:2] / (digest + ".md")
            archived.parent.mkdir(exist_ok=True)
            if archived.exists():
                inv.require(archived.read_bytes() == raw, "archive hash collision")
            else:
                with archived.open("xb") as stream:
                    stream.write(raw)
            pins.append(dict(source=str(path.relative_to(ROOT)), sha256=digest,
                             bytes=len(raw), archive=str(archived.relative_to(ROOT))))
snapshot = AUDIT / "authored_candidates_snapshot_v2.json"
old = inv.cache.read(snapshot)
missing = defaultdict(list)
for row in old["rows"]:
    path = ROOT / row["review"]
    current = path.read_bytes().decode("utf-8")
    if row["review_text"] not in current:
        missing[(row["review"], row["review_sha256"])].append(
            dict(id=row["id"], decision=row["decision"], original_row=row["review_text"]))
excerpts = []
for (source, original_sha), rows in missing.items():
    value = dict(status="RECOVERED_ROW_EXCERPT_NOT_ORIGINAL_REVIEW_BYTES", original_path=source,
                 original_review_sha256=original_sha, snapshot=str(snapshot.relative_to(ROOT)),
                 snapshot_sha256=inv.file_sha(snapshot), rows=rows)
    payload = (json.dumps(value, ensure_ascii=False, indent=2) + chr(10)).encode("utf-8")
    digest = inv.sha(payload.decode("utf-8"))
    path = out / (digest + ".json")
    if not path.exists():
        with path.open("xb") as stream:
            stream.write(payload)
    else:
        inv.require(path.read_bytes() == payload, "recovered excerpt differs")
    excerpts.append(dict(path=str(path.relative_to(ROOT)), sha256=digest, rows=len(rows)))
stamp = str(time.time_ns())
manifest = out / ("manifest_" + stamp + ".json")
inv.write_json(manifest, dict(status="CURRENT_REVIEW_BYTE_ARCHIVE_NOT_ADOPTION", sources=pins,
               in_flight_skipped=skipped, recovered_prior_rows=excerpts,
               source_sha256=inv.file_sha(Path(__file__))))
failure = AUDIT / "DRAFT_V7_FAILURE_V1.json"
if not failure.exists():
    inv.write_json(failure, dict(status="FAILED_DRAFT_NOT_CORPUS_QUALITY_RESULT", session=32354, actual_exit_code=1,
                   exception="individual HOLD cannot reuse terminal draft",
                   cause="Reuse adapter also rejected the existing hard-boundary EXCLUDE proposals.",
                   complete_json_present=(inv.BASE / "draft_proposals_v7/complete.json").exists(),
                   source_hashes_checked_after_exit={name: inv.file_sha(ROOT/name) for name in failed_revision.CODE},
                   followup="draft_proposals_v7b uses the established full engine without this adapter.",
                   original_writes=0, cache_admitted=0))
print(json.dumps(dict(archived_reviews=len(pins), in_flight_skipped=len(skipped),
                      recovered_rows=sum(item["rows"] for item in excerpts), manifest=str(manifest.relative_to(ROOT)))))
