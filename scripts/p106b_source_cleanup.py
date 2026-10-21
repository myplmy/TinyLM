#!/usr/bin/env python3
"""Versioned, conservative text-format cleanup. Never edits an input cache.

This is not a truth, language-quality, or benchmark decontamination filter.
Code/math and uncertain wiki constructs are retained for offline review.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import html
import json
import mmap
from pathlib import Path
import re
import sys
import time
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
VERSION = "P106B_CONSERVATIVE_SOURCE_CLEANUP_V1"
DEFAULT = ROOT / "data_cache/p106b_native_cleanup_v1_s1337"
TRAIN = ROOT / "data_cache/p106b_native_expansion_v1_s1337/train.bin"
TOKENIZER = ROOT / "data_cache/tok-ko-en-32768-chat32.json"
TAG = "p106b_native_cleanup_v1_s1337"
PROTECTED = {"TinyDataset", ".claude", ".codex", ".agents", ".aws"}
SAFE_TAGS = "b|strong|i|em|u|span|p|div|br|h[1-6]|ul|ol|li"
TAG_PATTERN = re.compile(r"</?(?:" + SAFE_TAGS + r")(?:\s+[^<>]*?)?\s*/?>", re.I)
FENCE = re.compile(r"(```.*?```|~~~.*?~~~|`[^`\n]+`)", re.S)


def safe(path):
    path = Path(path).absolute()
    if not path.is_relative_to(ROOT) or any(p in PROTECTED for p in path.relative_to(ROOT).parts):
        raise ValueError("explicit non-protected repository path required")
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError("symlink inputs/outputs refused")
    return path


def sha(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest().upper()


def clean_text(text, source_kind="unknown"):
    if source_kind not in ("unknown", "wikipedia_text", "fineweb_text"):
        raise ValueError("explicit source kind required")
    original = text
    changes, warnings = Counter(), set()
    # Do not normalize away compatibility distinctions in numbers or code.
    text = unicodedata.normalize("NFC", text.replace("\r\n", "\n").replace("\r", "\n"))
    if text.startswith("\ufeff"):
        text = text[1:]; changes["leading_bom"] += 1
    parts = FENCE.split(text)
    for i in range(0, len(parts), 2):
        part = parts[i]
        if re.search(r"<(?:script|style|table)\b", part, re.I):
            warnings.add("complex_html_preserved")
        if "{{" in part or "{|" in part:
            warnings.add("wiki_template_or_table_preserved")
        if re.search(r"(?m)^\s*(?:분류:|Category:)", part):
            warnings.add("plain_category_tail_preserved")
        # Only paired known presentation tags, or explicit linebreak tags.
        # Unclosed markup is a warning, not permission to delete prose.
        tags = list(TAG_PATTERN.finditer(part))
        balanced = True; stack = []
        for match in tags:
            tag = re.match(r"<(/?)([a-z0-9]+)", match.group(), re.I)
            closing, name = tag.group(1), tag.group(2).lower()
            if name == "br" or match.group().endswith("/>"):
                continue
            if not closing:
                stack.append(name)
            elif not stack or stack.pop() != name:
                balanced = False; break
        if tags and balanced and not stack:
            changes["balanced_presentation_tags"] += len(tags)
            part = TAG_PATTERN.sub(lambda m: "\n" if re.match(r"</?(?:p|div|br|h[1-6]|li)\b", m.group(), re.I) else "", part)
        elif tags:
            warnings.add("unbalanced_html_preserved")
        # Comments can contain code examples: preserve when their intent is unknown.
        if "<!--" in part:
            warnings.add("html_comment_preserved")
        if source_kind == "wikipedia_text":
            part, n = re.subn(r"\[\[([^\[\]|\n]+)\|([^\[\]\n]+)\]\]", r"\2", part)
            changes["wiki_display_links"] += n
            part, n = re.subn(r"(?m)^\s*\[\[(?:분류|Category):[^\]\n]+\]\]\s*$", "", part)
            changes["wiki_category_markup_lines"] += n
        elif "[[" in part:
            warnings.add("wiki_markup_unknown_provenance_preserved")
        # Do not html.unescape: it could turn literal &lt;code&gt; into markup.
        parts[i] = part
    result = "".join(parts)
    if result != original:
        changes["changed_documents"] = 1
    return result, dict(+changes), sorted(warnings)


def bounded_cache_documents(path, tok, count=64, max_segment_ids=262144):
    """Read complete EOS segments at spaced offsets; not a representative census."""
    import numpy as np
    with path.open("rb") as stream, mmap.mmap(stream.fileno(), 0, access=mmap.ACCESS_READ) as mapped:
        total = len(mapped) // 2
        seen = set()
        for i in range(count):
            offset = (i * total // count)
            end = min(total, offset + max_segment_ids * 2)
            view = np.frombuffer(mapped[offset * 2:end * 2], dtype="<u2")
            marks = np.flatnonzero(view == 2)
            if len(marks) < 2:
                del view; continue
            start, stop = offset + int(marks[0]) + 1, offset + int(marks[1])
            if (start, stop) in seen or stop - start > max_segment_ids:
                del view; continue
            seen.add((start, stop))
            values = np.frombuffer(mapped[start * 2:stop * 2], dtype="<u2").tolist()
            del view
            yield dict(source_kind="unknown", cache_segment_ids=[start, stop], text=tok.decode(values, skip_special_tokens=False))


def prepare(output=DEFAULT, count=64):
    from tokenizers import Tokenizer
    output, train, tokenizer = safe(output), safe(TRAIN), safe(TOKENIZER)
    if output.exists():
        raise FileExistsError("write-once cleanup namespace exists; choose a new version")
    before = (train.stat().st_size, train.stat().st_mtime_ns)
    tok = Tokenizer.from_file(str(tokenizer))
    began = time.perf_counter(); rows = []; totals = Counter(); warns = Counter()
    for n, source in enumerate(bounded_cache_documents(train, tok, count)):
        cleaned, changes, warnings = clean_text(source["text"], source["source_kind"])
        totals.update(changes); warns.update(warnings)
        rows.append(dict(id=n, **source, cleaned_text=cleaned, original_sha256=sha(source["text"]),
                         cleaned_sha256=sha(cleaned), changes=changes, warnings=warnings,
                         admission="REVIEW_REQUIRED" if warnings else "FORMAT_ONLY_NOT_QUALITY_PASS"))
    if not rows:
        raise ValueError("zero complete source documents is not success")
    if before != (train.stat().st_size, train.stat().st_mtime_ns):
        raise ValueError("source stat changed during bounded read")
    output.mkdir(parents=True, exist_ok=False)
    payload = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
    if len(payload.encode()) >= 20_000_000:
        raise ValueError("bounded pilot exceeded20MB; reduce --documents")
    with (output / "paired_documents.jsonl").open("x", encoding="utf-8") as stream:
        stream.write(payload)
    report = dict(schema=VERSION, tag=TAG, status="BOUNDED_CLEANUP_COMPLETE", documents=len(rows),
                  changes=dict(totals), warnings=dict(warns), seconds=time.perf_counter() - began,
                  source=str(train.relative_to(ROOT)), source_size=before[0], source_stat_unchanged=True,
                  paired_sha256=sha(payload), semantic_quality="NOT_REVIEWED", decontamination="NOT_RUN",
                  corpus_scope="spaced EOS segments; not original source URL documents or whole pool",
                  full_pool_cleaned=False, models_loaded=0, gpu_calls=0, original_writes=0)
    with (output / "report.json").open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    print(json.dumps(report, ensure_ascii=False))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--documents", type=int, default=64)
    parser.add_argument("--output", type=Path, default=DEFAULT)
    args = parser.parse_args()
    if args.documents < 1 or args.documents > 256:
        parser.error("bounded pilot requires1..256 complete segments")
    if args.execute == args.check_only:
        parser.error("choose exactly one of --execute or --check-only")
    if args.check_only:
        print(json.dumps(dict(schema=VERSION, source=str(TRAIN.relative_to(ROOT)),
              destination=str(args.output), semantic_quality="NOT_RUN", source_loaded=False)))
    else:
        prepare(args.output, args.documents)


if __name__ == "__main__":
    main()
