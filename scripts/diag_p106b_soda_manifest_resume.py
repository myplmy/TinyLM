"""Exercise durable source-cursor replay in two separate CPU processes."""

import argparse
import json
import os
import subprocess
import sys

from scripts import diag_p013_native_matched_training as io
from scripts.p106b_public_refill import english_specs
from scripts.p106b_shards import ShardWriter
from scripts.p106b_soda_dialogue_view import BOUNDARY
from scripts.p106b_soda_manifest_source import ManifestSodaSource, digest


OUT = io.ROOT / "test_result/evidence/p106b_soda_manifest_resume_cpu_v1_20261118"
FIXTURE = OUT / "source"
MANIFEST = FIXTURE / "raw_shards_manifest.json"
FILES = ("scripts/diag_p106b_soda_manifest_resume.py", "scripts/p106b_soda_manifest_source.py",
    "scripts/p106b_soda_candidate_wire.py", "scripts/p106b_soda_dialogue_view.py", "scripts/p106b_shards.py")


def read(path):
    return json.loads(path.read_bytes())


def source():
    return ManifestSodaSource(MANIFEST, read(OUT / "profile.json")["manifest_sha256"], english_specs()[4])


def evidence(row):
    group = None
    if row.prepared is not None:
        group = row.prepared.parent_key
        view = row.prepared.evidence_source
        assert "AUTHORED_NARRATIVE_NOT_INPUT" not in view["messages"][0]["content"]
        assert not view["meta"]["corpus_admitted"] and not view["meta"]["original_root_joined"]
    return dict(index=row.index, shard=row.shard, row_in_shard=row.row_in_shard, raw_sha256=row.raw_sha256,
        kind="PREPARED" if group else "HOLD", proposed_parent=group)


def first():
    rows = source()
    cursor = rows.start()
    closed = []
    for _ in range(4):
        row = rows.read_next(cursor)
        closed.append(evidence(row))
        cursor = row.next_cursor
    pending = rows.read_next(cursor)
    io.write(OUT / "part.json", dict(pid=os.getpid(), closed=closed, committed_cursor=cursor,
        observed_uncommitted=evidence(pending)))


def resume():
    rows = source()
    before = read(OUT / "part.json")
    assert before["pid"] != os.getpid()
    cursor = before["committed_cursor"]
    closed = []
    while (row := rows.read_next(cursor)) is not None:
        closed.append(evidence(row))
        cursor = row.next_cursor
    assert closed[0] == before["observed_uncommitted"]
    io.write(OUT / "resumed.json", dict(pid=os.getpid(), closed=closed, terminal_cursor=cursor))


def rejects(action):
    try:
        action()
    except ValueError:
        return
    raise AssertionError("input integrity error was accepted")


def main():
    OUT.mkdir(exist_ok=False)
    writer = ShardWriter(FIXTURE,"raw",limit=650)
    for index in range(9):
        turns = f"Alice: I am reading volume {index}.\n\nBob: I only saw the cover."
        if index in (2,7):
            turns = "This is an unseen narrative with no speakers."
        writer.append(dict(id=index, inputs=turns+BOUNDARY, targets="AUTHORED_NARRATIVE_NOT_INPUT",
            dataset_name="SODA-inst",sub_dataset_name="-",task_type="dialogue",template_id=1,
            language="eng",script="Latn",split="train"))
    manifest = writer.close(lineage=dict(scope="SYNTHETIC_NUMERIC_ID_FIXTURE",corpus_admitted=False))
    pins = {name: io.digest(io.ROOT / name) for name in FILES}
    io.write(OUT / "profile.json", dict(manifest_sha256=io.digest(MANIFEST), source_sha256=pins))

    entries = []
    for child in ("part","resume"):
        code = subprocess.run([sys.executable,"-B","-m","scripts.diag_p106b_soda_manifest_resume",child],
            cwd=io.ROOT,timeout=30).returncode
        assert code == 0
        entries.append(code)
    before, after = (read(OUT / name) for name in ("part.json","resumed.json"))
    results = before["closed"] + after["closed"]
    assert [row["index"] for row in results] == list(range(9))
    assert [row["index"] for row in results if row["kind"] == "HOLD"] == [2,7]
    concatenated = [digest(line+b"\n") for desc in manifest["shards"]
        for line in (FIXTURE / desc["path"]).read_bytes()[:-1].split(b"\n")]
    assert concatenated == [row["raw_sha256"] for row in results]
    assert before["closed"][-1]["shard"] != after["closed"][0]["shard"]

    rows = source()
    assert rows.read_next(after["terminal_cursor"]) is None
    rejects(lambda: rows.read_next(dict(manifest_sha256="0"*64,next_row=0)))
    rejects(lambda: rows.read_next(dict(rows.start(),next_row=10)))
    tampered = OUT / "tampered_control"
    tampered.mkdir(exist_ok=False)
    for desc in manifest["shards"]:
        data = (FIXTURE / desc["path"]).read_bytes()
        if desc == manifest["shards"][0]:
            data = data.replace(b"Alice",b"Elice",1)
        with (tampered / desc["path"]).open("xb") as stream:
            stream.write(data)
    with (tampered / MANIFEST.name).open("xb") as stream:
        stream.write(MANIFEST.read_bytes())
    rejects(lambda: ManifestSodaSource(tampered / MANIFEST.name,io.digest(MANIFEST),english_specs()[4]))
    assert all(io.digest(io.ROOT / name)==sha for name,sha in pins.items())
    io.write(OUT / "report.json",dict(read_rows=9,prepared_rows=7,held_rows=2,shards=len(manifest["shards"]),
        closed_rows=results,child_exit=entries,exact_uncommitted_replay=True,rejected_bad_cursors=2,
        rejected_same_size_source_change=True,manifest_sha256=io.digest(MANIFEST),operating_producer_calls=0,
        teacher_requests=0,admitted_train_rows=0))
    print("SODA_MANIFEST_RESUME_CPU",len(results),len(manifest["shards"]),entries,flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase",choices=("run","part","resume"))
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""
    {"run":main,"part":first,"resume":resume}[parser.parse_args().phase]()
