"""Join the accepted v1.1 cache to the verified correction-first P109C course."""

import argparse
from copy import deepcopy
import json
import os
from pathlib import Path
from shutil import copyfile
from tempfile import NamedTemporaryFile

from scripts import build_p109c_position_cache as position
from scripts import run_p109c_scratch330 as entry
from tinylm.train.context_training_state import cache_identity


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data_cache"
HANDOFF = DATA / "20261120_정제데이터셋v1.1.최종채택.json"
HANDOFF_SHA = "6dd3833367db576660b88226d6c9765992ae3cb8a7387764dc160f04ec7e80ef"
CACHE = DATA / "ko-en_p109c_adopted_v11_20261121_chat32"
COURSE = ROOT / "test_result/evidence/p109c_authored_curriculum_correction_only_cpu_v1_20261121/compiled_manifest.json"
COURSE_PLAN = "3BFCC93106EB39886CEC64F83DE807A5EFFB0A6DBDD84E6211475D975A71CE5C"
COURSE_DIR = DATA / "p109c_authored_correction_20261121"
MANIFEST = DATA / "p109c_scratch330_v1_admitted_bundle_20261121.json"


def seal():
    handoff = json.loads(entry.manifest_bytes(HANDOFF, HANDOFF_SHA))
    if (handoff["schema"], handoff["source_release"]) != ("P109C_ADOPTED_V11_HANDOFF_V1", entry.RELEASE):
        raise ValueError("the selected training release differs")
    for name in ("decision_archive", "tokenizer"):
        position.pinned_file(DATA, handoff[name])
    position.regular_file(CACHE / "meta.json")
    cache_meta = json.loads((CACHE / "meta.json").read_bytes())
    if (cache_meta["raw_manifest_sha256"] != HANDOFF_SHA.upper()
            or cache_meta["position_revision"] != handoff["baseline_revision"]
            or cache_meta["source_release"] != entry.RELEASE
            or cache_meta["complete_train_val_overlap"] != handoff["normalized_train_val_document_overlap"]
            or cache_meta["additional_decisions_sha256"] != entry.digest(handoff["supplement"]["sha256"])
            or cache_meta["additional_documents"] != handoff["additional_decisions"]["EDIT"]
            or any(cache_meta[split + "_documents"] != expected for split, expected in handoff["admitted_documents"].items())):
        raise ValueError("the cache differs from the exact team-selected release")
    cache_id = cache_identity(CACHE)["files"]

    course_raw = COURSE.read_bytes()
    course = json.loads(course_raw)
    if (course["schema"] != "P109C_COMPILED_COURSE_V1" or course["source_release"] != entry.RELEASE
            or course["course_schedule_sha256"] != COURSE_PLAN
            or course["admission"]["course"] != "LOCAL_AUTHORED_CORRECTION_ONLY_CANDIDATE"
            or entry.digest(course["tokenizer"]["sha256"]) != cache_meta["tokenizer_sha256"]):
        raise ValueError("the prevalidated authored course is not the selected schedule")
    selected = deepcopy(course["course"])
    if MANIFEST.exists() or MANIFEST.is_symlink():
        raise FileExistsError(MANIFEST)
    COURSE_DIR.mkdir(exist_ok=True)
    for name in ("plain", "all_axes", "decimal"):
        spec = selected[name]
        path, stamp = position.pinned_file(COURSE.parent, spec)
        target = COURSE_DIR / path.name
        if not os.path.lexists(target):
            with NamedTemporaryFile(dir=COURSE_DIR) as temporary:
                copyfile(path, temporary.name)
                if entry.file_sha(Path(temporary.name)).upper() != entry.digest(spec["sha256"]):
                    raise ValueError(f"the copied course file differs: {name}")
                os.link(temporary.name, target)
        position.regular_file(target)
        if entry.file_sha(target).upper() != entry.digest(spec["sha256"]) or entry.file_stamp(path) != stamp:
            raise ValueError(f"the copied course file differs: {name}")
        spec["file"] = target.relative_to(DATA).as_posix()

    manifest = dict(schema=entry.SCHEMA, source_release=entry.RELEASE,
        admission=dict(raw=handoff["admission"], course="검산된 내부 작성 교정 전용 교과와 원천 분리"),
        cache=dict(directory=CACHE.name, sha256={name: row["sha256"] for name, row in cache_id.items()}),
        tokenizer=handoff["tokenizer"], course=selected,
        provenance=dict(selected_handoff=HANDOFF.name, selected_handoff_sha256=HANDOFF_SHA.upper(),
                        local_course=str(COURSE.relative_to(ROOT)), course_sha256=entry.file_sha(COURSE).upper(),
                        verified_course_schedule_sha256=COURSE_PLAN))
    with NamedTemporaryFile(mode="w", encoding="utf-8", dir=DATA) as temporary:
        json.dump(manifest, temporary, ensure_ascii=False, indent=2)
        temporary.flush()
        os.fsync(temporary.fileno())
        draft = Path(temporary.name)
        sha256 = entry.file_sha(draft)
        bundle = entry.load_bundle(draft, sha256)
        os.link(draft, MANIFEST)
    print(json.dumps(dict(manifest=str(MANIFEST), sha256=sha256, receipt=bundle.receipt()), ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    seal()


if __name__ == "__main__":
    main()
