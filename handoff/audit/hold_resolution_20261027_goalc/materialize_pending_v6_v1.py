"""Replay remaining V6 drafts and independently check terminal text integrity.

Inherited individual/span holds stay metadata-only and are never recopied here.
Every other pending candidate is materialized as a diagnostic, not an admission.
This also checks that V6 terminal edits introduce no non-whitespace characters.
"""
from collections import Counter,defaultdict
from contextlib import ExitStack
import heapq
import json
from pathlib import Path
import re
import sys
import time

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from scripts import p106b_hold_resolution_inventory as inv
from scripts import p106b_hold_resolution_policy_v6 as policy

BASE=inv.BASE
SOURCE=BASE/"draft_proposals_v6"
OUT=BASE/"pending_materialized_v6_v1"
report=inv.cache.read(SOURCE/"complete.json")
inv.require(not OUT.exists(),"write-once diagnostic namespace required")
inv.verify(SOURCE/"unique",report["unique_manifest"])
pin=dict(source_complete_sha256=inv.file_sha(SOURCE/"complete.json"),
         producer_sha256=inv.file_sha(Path(__file__)),
         frozen_code=report["lineage"]["source_code_sha256"])
for name,digest in pin["frozen_code"].items():
    inv.require(inv.file_sha(ROOT/name)==digest,"frozen V6 source changed")
pending=inv.ShardWriter(OUT/"pending","candidates",limit=19_999_999)
integrity=inv.ShardWriter(OUT/"terminal_integrity","checks",limit=19_999_999)
counts=Counter()
features=Counter()
heaps=defaultdict(list)
flags=[]
started=last=time.monotonic()


def ordered_deletion(original,cleaned):
    source=iter(char for char in original if not char.isspace())
    return all(any(a==b for a in source)for b in cleaned if not b.isspace())


def shape_features(text,reasons):
    plain="".join(re.sub(r"[^\r\n]"," ",part)if protected else part
                  for protected,part in policy.v1.protected_parts(text)[0])
    tags=set()
    if "APPENDIX_CATEGORY_BOUNDARY_REQUIRES_CONTEXT"in reasons:
        lines=[line.strip()for line in plain.splitlines()if line.strip()]
        last=next((i for i in range(len(lines)-1,-1,-1)if policy.v1.normalize_heading(lines[i])in policy.v4.APPENDICES),None)
        tail=lines[last+1:]if last is not None else []
        hard=[i for i,line in enumerate(tail)if policy.v2.METADATA_YEAR.fullmatch(line)]
        tags.add("APPENDIX/HARD_ANCHOR_"+str(min(len(hard),2)))
        if hard:
            prefix=tail[:hard[0]]
            tags.add("APPENDIX/PREFIX_ALL_KNOWN_TYPES"if all(policy.v4.CATEGORY_LINE.fullmatch(line)for line in prefix)
                     else"APPENDIX/PREFIX_UNKNOWN_NOMINAL")
        if policy.REFERENCE_RECORD.search(chr(10).join(tail)):
            tags.add("APPENDIX/ACTUAL_NAMED_REFERENCE_PATTERN")
    if "MAIN_BODY_REPETITION_REQUIRES_CONTEXT"in reasons:
        lines=[line.strip()for line in plain.splitlines()if line.strip()]
        frequency=Counter(lines)
        repeated={line for line,count in frequency.items()if count>1 and len(line)>=6
                  and policy.v1.normalize_heading(line)not in policy.v4.LABELS}
        prose=any(policy.v1.PUNCTUATION.search(line)for line in repeated)
        adjacent=any(a==b and a in repeated for a,b in zip(lines,lines[1:]))
        tags.add("REPEAT/PROSE"if prose else"REPEAT/NOMINAL_OR_VALUES")
        tags.add("REPEAT/ADJACENT"if adjacent else"REPEAT/SEPARATED")
    if "BROKEN_TABLE_OR_WIKI_MARKUP"in reasons or "UNRESOLVED_RAW_TABLE_OR_CLOSING_WIKI_MARKUP"in reasons:
        if "{|"in plain or "|}"in plain:
            tags.add("MARKUP/WIKI_TABLE_MATCHED_COUNTS"if plain.count("{|")==plain.count("|}")else"MARKUP/WIKI_TABLE_UNBALANCED")
        if "[["in plain or "]]"in plain:
            tags.add("MARKUP/WIKI_LINK_MATCHED_COUNTS"if plain.count("[[")==plain.count("]]")else"MARKUP/WIKI_LINK_UNBALANCED")
        if re.search(r"(?i)rowspan|colspan",plain):
            tags.add("MARKUP/SPANNING_TABLE_CELLS")
        if re.search(r"(?m)^\s*\|",plain):
            tags.add("MARKUP/PIPE_ROWS")
    if "UNRESOLVED_FIELD_OR_TITLE"in reasons:
        if re.search(r"《\s*》|〈\s*〉",plain):
            tags.add("FIELD/EMPTY_BOOK_OR_WORK_TITLE")
        if "←"in plain:
            tags.add("FIELD/FORMER_NAME_ARROW")
        if policy.MATH_CONTEXT.search(plain):
            tags.add("FIELD/MATHEMATICAL_OR_PHYSICAL_CONTEXT")
        if policy.identified(text):
            tags.add("FIELD/IDENTIFIED_ARTICLE")
        if re.search(r"\(\s*\)",plain):
            tags.add("FIELD/EMPTY_PAREN_REMAINS")
    if "MARKUP_OR_TRANSCRIPTION_REQUIRES_CONTEXT"in reasons:
        if policy.v1.GENERIC_TAG.search(plain):
            tags.add("TRANSCRIPTION/TAG_OR_TYPED_CODE_SYNTAX")
        if "{{"in plain or "}}"in plain:
            tags.add("TRANSCRIPTION/TEMPLATE")
    return tags or {"OTHER/"+reasons[0]}


with ExitStack()as stack:
    reader=inv.OriginalReader(inv.cache.read(BASE/"scope.json"),stack)
    for number,row in enumerate(inv.cache.rows(SOURCE/"unique",report["unique_manifest"]),1):
        decision=row["decision"]
        counts.update(unique=1,**{decision:1})
        if decision=="EXCLUDE":
            continue
        if decision=="PENDING"and any("PRIOR_INDIVIDUAL_OR_SPAN"in reason for reason in row["reasons"]):
            pending.append(dict(row,route="ASSIGNED_TEXT_REVIEW_ONLY_NO_SOURCE_RECOPY",diagnostic_candidate=None))
            counts.update(inherited_metadata_only=1)
            continue
        inv.require(row["id"]!="expanded_train:756966","unsafe source must not be decoded again")
        original,complete,valid=reader.text(row)
        if decision in{"KEEP","EDIT"}:
            clean=original if decision=="KEEP"else row["text"]
            inv.require(inv.sha(clean)==row["clean_text_sha256"],"frozen terminal body differs")
            ordered=ordered_deletion(original,clean)
            code=policy.code_preserved(original,clean)
            unicode=policy.unicode_examples_preserved(original,clean)
            item=dict(id=row["id"],original_text_sha256=row["original_text_sha256"],clean_text_sha256=inv.sha(clean),
                      original_characters=len(original),clean_characters=len(clean),decision=decision,
                      ordered_nonwhitespace_deletion_only=ordered,code_guard=code,unicode_guard=unicode,
                      status="BYTE_AND_ORDER_CHECK_NOT_SEMANTIC_APPROVAL")
            integrity.append(item)
            if not(ordered and code and unicode):
                flags.append(item)
        else:
            value=policy.propose(dict(row,text=original,complete_eos=complete,valid_utf8=valid))
            inv.require(value["decision"]=="PENDING"and value["reasons"]==row["reasons"]
                        and value["changes"]==row["changes"],"pending V6 replay differs")
            candidate=value.get("candidate",value["text"])
            kinds=shape_features(candidate,row["reasons"])
            item=dict(row,route="REPLAYED_DIAGNOSTIC_NOT_ADMISSION",diagnostic_candidate=candidate,
                      diagnostic_candidate_sha256=inv.sha(candidate),profile_features=sorted(kinds))
            pending.append(item)
            counts.update(materialized_pending=1,pending_characters=len(candidate))
            for kind in kinds:
                features[kind]+=1
                size="short"if len(original)<700 else"medium"if len(original)<7000 else"long"
                stratum="/".join([kind,row["language_bucket"],size])
                key=row["original_text_sha256"]
                entry=(-int(key,16),key,item)
                heap=heaps[stratum]
                if len(heap)<2:
                    heapq.heappush(heap,entry)
                elif entry[:2]>heap[0][:2]:
                    heapq.heapreplace(heap,entry)
        if time.monotonic()-last>=20:
            print(json.dumps(dict(phase="v6_terminal_integrity_and_pending_replay",unique_done=number,
                                 counts=dict(counts),seconds=round(time.monotonic()-started,1))),flush=True)
            last=time.monotonic()
    lineage=dict(pin=pin,purpose="DIAGNOSTIC_NOT_ROOT_APPROVAL_OR_CACHE_ADMISSION")
    pending_manifest=pending.close(lineage=lineage)
    integrity_manifest=integrity.close(lineage=lineage)
    inv.require(counts["unique"]==297539 and pending_manifest["rows"]==report["unique_counts"]["PENDING"]
                and integrity_manifest["rows"]==report["unique_counts"]["KEEP"]+report["unique_counts"]["EDIT"],
                "full V6 conservation differs")
    selected={}
    for kind,heap in heaps.items():
        for _,key,item in heap:
            selected.setdefault(key,dict(item,strata=[]))["strata"].append(kind)
    packet_dir=OUT/"review_packets"
    packet_dir.mkdir()
    packets=[]
    for row in sorted(selected.values(),key=lambda row:row["id"]):
        original,_,_=reader.text(row)
        paths={}
        for label,text in[("original",original),("candidate",row["diagnostic_candidate"])]:
            path=packet_dir/(row["id"].replace(":","_")+"_"+label+".txt")
            payload=text.encode("utf-8")
            inv.require(len(payload)<20_000_000,"split large ordered packet")
            with path.open("xb")as stream:
                stream.write(payload)
            paths[label]=dict(path=str(path.relative_to(ROOT)),sha256=inv.file_sha(path))
        packets.append({**{key:value for key,value in row.items()if key!="diagnostic_candidate"},"paths":paths})
for name,digest in pin["frozen_code"].items():
    inv.require(inv.file_sha(ROOT/name)==digest,"frozen code changed during replay")
inv.require(inv.file_sha(Path(__file__))==pin["producer_sha256"],"producer changed during run")
value=dict(schema="P106B_MATERIALIZED_V6_DIAGNOSTICS_V1",status="DIAGNOSTIC_NOT_ROOT_ADMISSION",
           pin=pin,counts=dict(counts),features=dict(features),pending_manifest=pending_manifest,
           terminal_integrity_manifest=integrity_manifest,terminal_integrity_flags=flags,
           seconds=time.monotonic()-started,root_adopted=0,training_authorized=False)
inv.write_json(packet_dir/"manifest.json",dict(rows=packets,purpose="PENDING_CONTEXT_COUNTEREXAMPLES_NOT_COMPLETION"))
inv.write_json(OUT/"complete.json",value)
print(json.dumps(dict(counts=dict(counts),features=dict(features),terminal_flags=len(flags),packets=len(packets),
                      seconds=value["seconds"])),flush=True)
