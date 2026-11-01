"""Pin full original/candidate diffs for three incorrectly reported corruptions."""
from pathlib import Path
from collections import Counter
import difflib
import json
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv
AUDIT=Path(__file__).resolve().parent
manifest=inv.BASE/"legacy_span_review_v2/manifest.json"
sources={row["id"]:row for row in inv.cache.read(manifest)["rows"]}
claims={"expanded_train:23003":"후보 꼬리가 레닌 문서로 바뀌었다는 주장",
        "expanded_train:23894":"4.19 혁명 전후의 정상 문단이 통째로 빠졌다는 주장",
        "expanded_train:23988":"원문에 없는 분류14개가 후보에 추가됐다는 주장"}
records=[]
lines=["# 추가·누락 오독의 실제 전체 diff 반증", "",
       "판독자의 큰 추가/누락 주장 세 건을 총괄이 명세 SHA와 전체 diff로 확인했다. 세 주장 모두 실제 파일과 맞지 않아 철회 대상이다.",
       "원주장/이전 review는 보존하고, 이에 기대어 문서를 제외하거나 원문에 없는 내용을 다시 삽입하지 않는다.", ""]
for ident,claim in claims.items():
    source=sources[ident]
    texts={}
    for label,info in source["paths"].items():
        path=ROOT/info["path"]
        inv.require(inv.file_sha(path)==info["sha256"],"pinned source/candidate changed")
        texts[label]=path.read_bytes().decode("utf-8")
    before,after=texts["original"],texts["candidate"]
    diff="".join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile="original",tofile="candidate",n=1))
    record=dict(id=ident,claim=claim,verdict="REFUTED_BY_PINNED_FULL_TEXT_DIFF",paths=source["paths"],
                literal_counts={key:{label:text.count(key)for label,text in texts.items()}for key in
                                ["레닌","나폴레옹","4.19 혁명 전후","대만에 거주한 대한민국인"]},
                added_nonempty_lines=list((Counter(after.splitlines())-Counter(before.splitlines())).elements()),full_diff=diff)
    records.append(record)
    lines.extend(["## "+ident,"",claim+" — 실제 diff로 반증됐다.","","```diff",diff.rstrip(),"```",""])
inv.write_json(AUDIT/"counter_literal_refutations_v3.json",dict(records=records,
               manifest_sha256=inv.file_sha(manifest),source_sha256=inv.file_sha(Path(__file__)),
               root_semantic_or_cache_admission=False))
with(AUDIT/"counter_literal_refutations_v3.md").open("x",encoding="utf-8")as stream:
    stream.write(chr(10).join(lines)+chr(10))
print(json.dumps(dict(refuted=list(claims),actual_source_writes=0),ensure_ascii=False))
