"""Inspect literal source characters around allegedly missing Unicode fields."""
from pathlib import Path
import re
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv

source = inv.BASE / "legacy_span_review_v2/packets/expanded_train_387148_original.txt"
raw = source.read_bytes().decode("utf-8")
rows = []
for match in re.finditer(r"such as|Table 20[.]2|Table 20[.]3|Leading zeros|Unicode range", raw, re.I):
    lo, hi = max(0, match.start()-60), min(len(raw), match.end()+240)
    text = raw[lo:hi]
    rows.append(dict(marker=match[0], span=[lo, hi], literal_repr=repr(text),
                     non_ascii_characters=[dict(relative=i, codepoint="U+"+format(ord(char),"04X"),
                                                name=unicodedata.name(char,"UNNAMED"))
                                           for i,char in enumerate(text) if ord(char)>127]))
out = Path(__file__).resolve().parent / "invisible_character_readback_v1.json"
inv.write_json(out, dict(source=str(source.relative_to(ROOT)), source_sha256=inv.file_sha(source),
                        source_characters=len(raw), rows=rows, semantic_fact_validation=False,
                        producer_sha256=inv.file_sha(Path(__file__))))
for row in rows:
    print(row)
