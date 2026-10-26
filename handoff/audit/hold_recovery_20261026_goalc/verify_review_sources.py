"""Read-only raw-source proof for the two exact HOLD review packet manifests."""
from array import array
import argparse
from contextlib import ExitStack
import hashlib
import mmap
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT))
from scripts import p106b_corpus_cache as cache
from scripts import p106b_hold_recovery as recovery
from scripts.p106b_native_text_audit import file_sha,write_json


def main(packet_names=None,receipt_name="review_source_proof_v1.json"):
    started=time.monotonic();base=recovery.BASE
    allowed=["packets_initial_v2/manifest.json"]+[f"proposals_v{i}/review_packets/manifest.json" for i in (1,2,3)]
    packet_names=packet_names or allowed[:2]
    assert set(packet_names)<=set(allowed) and len(set(packet_names))==len(packet_names)
    assert Path(receipt_name).name==receipt_name and receipt_name.endswith(".json")
    scope=cache.read(base/"scope.json");tokenizer=ROOT/scope["tokenizer"]["path"]
    assert file_sha(tokenizer)==scope["tokenizer"]["sha256"]
    codec=cache.native.ByteCodec(cache.read(tokenizer));records=[];source_pins={}
    with ExitStack() as stack:
        maps={}
        for spec in scope["inputs"]:
            path=ROOT/spec["path"];observed=file_sha(path)
            assert observed==spec["sha256"],spec["name"]
            source_pins[spec["name"]]=observed
            stream=stack.enter_context(path.open("rb"))
            maps[spec["name"]]=stack.enter_context(mmap.mmap(stream.fileno(),0,access=mmap.ACCESS_READ))
        for packet_path in [base/name for name in packet_names]:
            manifest=cache.read(packet_path)
            for row in manifest["rows"]:
                lo,hi=row["source_ids"];raw=maps[row["source"]][lo*2:hi*2]
                assert hashlib.sha256(raw).hexdigest().upper()==row["source_ids_sha256"],row["id"]
                ids=array("H");ids.frombytes(raw)
                if sys.byteorder!="little":ids.byteswap()
                complete=row.get("complete_eos",ids[-1]==2)
                text,body=codec.text(ids[:-1] if complete else ids)
                original=ROOT/row.get("original_path",row.get("path"))
                expected=row["original_text_sha256"]
                assert body==original.read_bytes() and file_sha(original)==expected,row["id"]
                records.append(dict(id=row["id"],original_path=str(original.relative_to(ROOT)),
                    source_ids=[lo,hi],source_ids_sha256=row["source_ids_sha256"],original_text_sha256=expected))
    receipt=dict(schema="P106B_EXACT_RAW_REVIEW_SOURCE_PROOF_V1",source_sha256=source_pins,
        verification_source_sha256=file_sha(Path(__file__)),packet_manifests=packet_names,
        tokenizer_sha256=scope["tokenizer"]["sha256"],rows=records,count=len(records),
        all_intervals_and_decoded_original_bytes_match=True,training_authorized=False,
        seconds=time.monotonic()-started)
    target=ROOT/"handoff/audit/hold_recovery_20261026_goalc"/receipt_name
    write_json(target,receipt)
    print(dict(count=len(records),source_sha_match=True,original_text_bytes_match=True,seconds=receipt["seconds"]),flush=True)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("--packet",action="append");p.add_argument("--receipt-name",default="review_source_proof_v1.json")
    a=p.parse_args();main(a.packet,a.receipt_name)
