"""Profile actual remaining field matches after the frozen V4 alias repair.

No admission, rejection or source modification occurs. Source hashes and exact
match contexts make false positives and genuinely missing content reviewable.
"""
from collections import Counter, defaultdict
from contextlib import ExitStack
import heapq
import json
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inventory
from scripts import p106b_hold_resolution_policy_v4 as policy

BASE = inventory.BASE
source = BASE / "draft_proposals_v5"
report = inventory.cache.read(source / "complete.json")
out = BASE / "field_profile_v5"
inventory.require(not out.exists(), "profile must use a new immutable namespace")
inventory.verify(source / "unique", report["unique_manifest"])
counts = Counter()
features = Counter()
literals = Counter()
contexts = defaultdict(list)
selected = {}
heaps = defaultdict(list)
start = last = time.monotonic()
pins = dict(draft_sha256=inventory.file_sha(source / "complete.json"),
            producer_sha256=inventory.file_sha(Path(__file__)),
            policy_sha256=inventory.file_sha(ROOT / "scripts/p106b_hold_resolution_policy_v4.py"))
with ExitStack() as stack:
    reader = inventory.OriginalReader(inventory.cache.read(BASE / "scope.json"), stack)
    for row in inventory.cache.rows(source / "unique", report["unique_manifest"]):
        if row["decision"] != "PENDING" or "UNRESOLVED_FIELD_OR_TITLE" not in row["reasons"]:
            continue
        inventory.require(row["id"] != "expanded_train:756966", "unsafe source must not enter a packet")
        raw, _, _ = reader.text(row)
        normalized, opened = policy.v2.v2.literal_normalize(raw)
        text, changes = policy.name_slots(normalized)
        masked = "".join(re.sub(r"[^\r\n]", " ", part) if protected else part
                         for protected, part in policy.v1.protected_parts(text)[0])
        intro = policy.intro(text)
        hits = sorted(list(policy.v1.cache.MISSING_FIELD.finditer(masked)) + list(policy.v1.DANGLING_FIELD.finditer(masked)),
                      key=lambda match: match.start())
        kinds = set()
        examples = []
        for match in hits:
            literal = match[0]
            literals[literal] += 1
            left, right = masked[max(0, match.start()-70):match.start()], masked[match.end():match.end()+70]
            kind = ("EMPTY_BOOK_TITLE" if "《" in literal else "COMMA_SLOT" if "," in literal or "，" in literal else
                    "EMPTY_PAREN" if "(" in literal else "DANGLING_FIELD")
            boundary = ("KOREAN_NOMINAL" if re.search(r"[가-힣》〉」』] *$", left) else
                        "LATIN_CALL_OR_NAME" if re.search(r"[A-Za-z_][A-Za-z0-9_.:]* *$", left) else
                        "AFTER_QUOTE" if re.search(r"[‘’“”'\"] *$", left) else "OTHER_LEFT")
            following = ("KOREAN_PARTICLE" if re.match(r"\s*(?:은|는|이|가|의|에|을|를|로|와|과|도|란|라고)", right) else
                         "AFTER_PUNCTUATION" if re.match(r"\s*[,.;:!?)。]", right) else "OTHER_RIGHT")
            key = "/".join([kind, boundary, following, "INTRO" if intro and literal in intro else "BODY",
                            "TECHNICAL_CONTEXT" if policy.v2.TECHNICAL.search(left+literal+right) else "NONTECHNICAL_CONTEXT",
                            "IDENTIFIED_ENTITY" if intro and policy.ENTITY.search(intro) else "OTHER_INTRO",
                            row["language_bucket"]])
            kinds.add(key)
            if len(examples) < 12:
                examples.append(dict(span=[match.start(), match.end()], literal=literal, left=left, right=right, feature=key))
        if not hits:
            kinds.add("NO_FIELD_MATCH_AFTER_SOURCE_ALIAS_REPAIR/" + row["language_bucket"])
        counts.update(documents=1, occurrences=row["occurrences"], hits=len(hits), repaired=bool(changes))
        for key in kinds:
            features[key] += 1
            if len(contexts[key]) < 3:
                contexts[key].append(dict(id=row["id"], original_text_sha256=row["original_text_sha256"], examples=examples))
            entry = (-int(row["original_text_sha256"],16), row["id"], row)
            heap = heaps[key]
            if len(heap) < 2:
                heapq.heappush(heap, entry)
            elif entry[:2] > heap[0][:2]:
                heapq.heapreplace(heap, entry)
        if time.monotonic()-last >= 20:
            print(json.dumps(dict(phase="actual_field_context_profile_v5", counts=dict(counts), seconds=round(time.monotonic()-start,1))), flush=True)
            last = time.monotonic()
    out.mkdir()
    packet_dir = out / "review_packets"
    packet_dir.mkdir()
    for feature, heap in heaps.items():
        for _, key, row in heap:
            selected.setdefault(key, dict(row, features=[]))["features"].append(feature)
    packets = []
    for row in sorted(selected.values(), key=lambda value: value["id"]):
        raw, _, _ = reader.text(row)
        text, _ = policy.v2.v2.literal_normalize(raw)
        candidate, changes = policy.name_slots(text)
        paths = {}
        for label, body in [("original",raw),("after_alias_only",candidate)]:
            path = packet_dir / (row["id"].replace(":","_")+"_"+label+".txt")
            payload = body.encode("utf-8")
            inventory.require(len(payload)<20_000_000,"split large profile packet")
            with path.open("xb") as stream:
                stream.write(payload)
            paths[label] = dict(path=str(path.relative_to(ROOT)),sha256=inventory.file_sha(path))
        packets.append(dict(row, paths=paths, alias_changes=changes))
inventory.require(inventory.file_sha(Path(__file__))==pins["producer_sha256"],"profile producer changed")
result = dict(schema="P106B_ACTUAL_FIELD_CONTEXT_PROFILE_V5",pins=pins,counts=dict(counts),features=dict(features),
              literals=dict(literals),purpose="READ_ONLY_CONTEXT_PROFILE_NOT_ADMISSION",seconds=time.monotonic()-start)
inventory.write_json(out/"complete.json", result)
inventory.write_json(out/"contexts.json", dict(rows=dict(contexts)))
inventory.write_json(packet_dir/"manifest.json", dict(rows=packets))
print(json.dumps(dict(counts=dict(counts),packets=len(packets),seconds=result["seconds"])),flush=True)
