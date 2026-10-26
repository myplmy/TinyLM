"""Create root-authored, offline source-context drafts; never admit or train them."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
from tokenizers import Tokenizer

ROOT=Path(__file__).resolve().parents[3]
BASE=Path(__file__).resolve().parent
SOURCE=BASE/"source_context_review_v1/packet.json"
OUTPUT=ROOT/"data_cache/p106b_native_source_context_clean_v1_20261026"

def sha(raw):
    return hashlib.sha256(raw).hexdigest().upper()

def main():
    inputs=json.loads((ROOT/"test_result/evidence/p106b_native_exposure_v3_20261026_rootc/inputs.json").read_text())
    tokenizer_path=ROOT/inputs["tokenizer"]
    tokenizer_sha=inputs["refs"][inputs["tokenizer"]]
    assert sha(tokenizer_path.read_bytes())==tokenizer_sha
    tokenizer=Tokenizer.from_file(str(tokenizer_path))
    packet=json.loads(SOURCE.read_text())
    assert len(packet["rows"])==8 and not OUTPUT.exists()
    texts={row["id"]:row for row in packet["rows"]}
    drafts={}
    edits={}
    for ident,marker in {
        "source_01":chr(10)+"각주 "+chr(10),
        "source_02":chr(10)+"각주 "+chr(10),
        "source_04":chr(10)+" 참고 문헌 "+chr(10),
        "source_06":chr(10)+chr(10)+"협회별 팀 배정 "+chr(10),
    }.items():
        original=texts[ident]["text"]
        assert original.count(marker)==1
        at=original.index(marker)
        draft=original[:at].rstrip()+chr(10)
        edits[ident]=[dict(operation="EXTRACT_PREFIX_AND_SEPARATE_TAIL",raw_char_span=[at,len(original)],
                          raw_tail=original[at:],reason="root reviewed categories/reference boundary or later missing tables")]
        if ident=="source_06":
            duplicate="유럽 축구 연맹(UEFA)의 최상위 클럽 축구 대회인 "
            assert draft.count(duplicate)==2
            repeated=duplicate+duplicate
            assert draft.count(repeated)==1
            draft=draft.replace(repeated,duplicate,1)
            edits[ident].append(dict(operation="REMOVE_ONE_EXACT_ADJACENT_DUPLICATE_PHRASE",
                                   exact_phrase=duplicate,replacement_count=1))
        drafts[ident]=draft
    drafts["source_08"]=(
        "National Geographic's Field Guide to the Birds of Western North America covers birds west of the Rocky Mountains. "
        "It includes illustrated accounts of plumages and life stages, a visual index, annotated artwork and color-coded range maps. "
        "The source describes 619 species, 560 new range maps, accounts for 85 casual and accidental birds, "
        "and an appendix listing 70 rarities. The book has 432 pages."+chr(10))
    edits["source_08"]=[dict(operation="ROOT_NEUTRAL_PROSE_DRAFT",
        reason="separate sales UI, discount, SKU, stock and promotional claims; retain the source's book specifications without independent fact certification",
        original_retained=True)]
    OUTPUT.mkdir(parents=True)
    records=[]
    for ident,row in texts.items():
        original=row["text"]
        record=dict(id=ident,source_span=row["source_content_span"],source_ids_sha256=row["ids_sha256"],
                    source_url=None,source_dataset=row["source_dataset"],formal_train_ready=False,
                    source_truth_verified=False,training_admission=0,raw_manifest=str(SOURCE.relative_to(ROOT)))
        if original is not None:
            raw=original.encode()
            assert sha(raw)==row["text_sha256"]
            raw_path=OUTPUT/(ident+"_original.txt")
            with raw_path.open("xb") as f:f.write(raw)
            record.update(raw_path=str(raw_path.relative_to(ROOT)),raw_bytes=len(raw),raw_sha256=sha(raw))
        else:
            record.update(raw_path="handoff/audit/oct26_research/source_context_review_v1/long_source_05/original.txt",
                          raw_copy_made=False)
        if ident in drafts:
            draft=drafts[ident]
            assert draft.strip()
            draft_path=OUTPUT/(ident+"_draft.txt")
            metadata_path=OUTPUT/(ident+"_edits.json")
            with draft_path.open("xb") as f:f.write(draft.encode())
            with metadata_path.open("x",encoding="utf-8") as f:
                json.dump(edits[ident],f,ensure_ascii=False,indent=2);f.write(chr(10))
            assert draft_path.read_text()==draft
            record.update(status="OFFLINE_DRAFT_NOT_TRAIN_READY",draft_path=str(draft_path.relative_to(ROOT)),
                draft_bytes=draft_path.stat().st_size,draft_sha256=sha(draft.encode()),
                draft_tokens=len(tokenizer.encode(draft,add_special_tokens=False).ids),
                edit_sidecar_path=str(metadata_path.relative_to(ROOT)),
                edit_sidecar_sha256=sha(metadata_path.read_bytes()),
                unchanged_semantic_factual_limits_preserved=True)
        else:
            record.update(status={
                "source_03":"HOLD_MISSING_TABLES_AND_VERIFIED_AWARD_YEAR_ERROR",
                "source_05":"HOLD_FOR_ATTRIBUTED_TRANSCRIPTION_SECTIONING_NO_REGEX_STRIP",
                "source_07":"HOLD_MISSING_TITLES_NO_INVENTED_REPAIR",
            }[ident],draft_path=None)
        records.append(record)
    manifest=dict(schema="TINYLM_ROOT_SOURCE_CONTEXT_OFFLINE_DRAFTS_V1",
        created_at=datetime.now(timezone.utc).isoformat(),
        source_packet_sha256=sha(SOURCE.read_bytes()),tokenizer=inputs["tokenizer"],
        tokenizer_sha256=tokenizer_sha,rows=records,
        selected_source_count=8,drafts=5,held=3,actual_training_admission=0,model_or_gpu_calls=0,
        source_training_cache_mutations=0,whole_corpus_semantic_cleanup_complete=False,
        selection_is_representative=False,
        limitation="These are five text drafts and three explicitly held sources, not a new corpus or the user's requested complete preprocessing.")
    target=BASE/"source_context_review_v1/offline_draft_manifest.json"
    with target.open("x",encoding="utf-8") as f:
        json.dump(manifest,f,ensure_ascii=False,indent=2);f.write(chr(10))
    for row in records:
        if row.get("draft_path"):
            path=ROOT/row["draft_path"]
            assert sha(path.read_bytes())==row["draft_sha256"] and path.stat().st_size<20000000
    print(json.dumps({key:manifest[key] for key in ["drafts","held","actual_training_admission","source_training_cache_mutations"]}))

if __name__=="__main__":
    main()

