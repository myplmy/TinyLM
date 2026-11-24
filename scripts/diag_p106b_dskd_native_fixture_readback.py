"""Read every sealed CE/KD input used by the queued Native training comparison."""

import hashlib
import json
import os

import numpy as np

from scripts import diag_p106b_dskd_native_batch_cuda as design
from scripts.p106b_feature_window import FeatureWindow
from scripts.p106b_official_lm_adapter import canonical


OUT = design.ROOT / "test_result/evidence/p106b_dskd_native_fixture_readback_cpu_v1_20261118"


def sha(raw):
    return hashlib.sha256(raw).hexdigest().upper()


def check_group(source, profile):
    ce, packed, kd = source["ce"], source["packed"], source["kd"]
    assert len(ce) == len(packed) == 17
    by_id = {}
    targets = 0
    for row, record in zip(ce, packed, strict=True):
        ids, labels, turns = (record[key] for key in ("ids", "labels", "turn_ids"))
        assert len(ids) == len(labels) == len(turns) == row["student_tokens"] == 1024
        assert labels[0] == -100 and turns[0] == 0 and turns[1:] == [1]*1023 and ids[1:] == labels[1:]
        assert all(3 <= token < 32768 for token in ids)
        assert row["record_sha256"] == sha(b"synthetic_record" + canonical(record))
        assert row["source_row_sha256"] == sha(b"synthetic_source" + canonical(record))
        assert row["ce_targets"] == sum(target >= 0 for target in labels[1:]) == 1023
        targets += row["ce_targets"]
        by_id[row["row_id"]] = ids
    assert [row["row_id"] for row in kd] == [ce[i]["row_id"] for i in (0, 7, 8, 16)]
    expected = [(row["row_id"], pos) for row in kd for pos in row["positions"]]
    reader = FeatureWindow(kd, root=design.OUT/"features", identities=profile["declared_synthetic_identities"],
                           split="train", hidden_width=1024, batch_positions=7)
    observed, groups = [], []
    while len(observed) < len(expected):
        batch = reader.prepare()
        groups.append(batch.stop - batch.start)
        for identifier, position, vec in zip(batch.row_ids, batch.positions, batch.values, strict=True):
            student = position["student_predictor_raw_index"]
            teacher = position["teacher_predictor_raw_index"]
            assert position["student_target_raw_index"] == student + 1
            assert position["teacher_target_raw_index"] == teacher + 1
            assert position["student_target_id"] == by_id[identifier][student + 1]
            assert position["teacher_native_argmax"] % 32768 == position["mapped_student_argmax"]
            assert np.flatnonzero(vec).tolist() == [teacher] and vec[teacher] == 1
            observed.append((identifier, position))
        reader.finish()
    assert reader.state_dict()["next_position"] == 20 and observed == expected and groups == [7, 7, 6]
    return dict(ce_targets=targets, kd_positions=len(observed), feature_reader_batch_sizes=groups,
        expected_native_rows=[8, 8, 1], declared_dummy_rows=7, payload_sha256=sha(canonical(source)))


def main():
    assert os.environ.get("CUDA_VISIBLE_DEVICES") == ""
    profile = design.verify()
    if OUT.exists():
        raise FileExistsError("Preserve existing full fixture readback")
    fixture = json.loads(design.DATA.read_bytes())
    assert len(fixture) == 4
    groups = [check_group(source, profile) for source in fixture]
    assert design.verify() == profile
    OUT.mkdir(exist_ok=False)
    result = dict(schema="DSKD_NATIVE_FIXTURE_READBACK_CPU_V1", training_profile_sha256=design.training.digest(design.PROFILE),
        groups=groups, original_ce_targets=sum(g["ce_targets"] for g in groups),
        teacher_positions=sum(g["kd_positions"] for g in groups), models=0, optimizer_updates=0, gpu_calls=0)
    design.training.write(OUT/"report.json",result)
    print("NATIVE_DSKD_INPUT_REPLAY", result["original_ce_targets"], result["teacher_positions"], flush=True)


if __name__ == "__main__":
    main()
