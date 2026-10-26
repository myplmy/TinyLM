"""Prepare explicit staged content while preserving concurrent shared-file edits.

This command reads Git and writes local patch/payload evidence only. It does not
stage, commit, create a branch, restore files, or alter any working source.
"""
import difflib
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

AUDIT = Path(__file__).resolve().parent
ROOT = AUDIT.parents[2]
sys.path.insert(0, str(ROOT))
from scripts.p106b_native_text_audit import write_json


def git(*args):
    return subprocess.check_output(["git", *args], cwd=ROOT)


def sha(data):
    return hashlib.sha256(data).hexdigest().upper()


def section(text, heading):
    assert text.count(heading) == 1, heading
    start = text.index(heading)
    level = len(heading) - len(heading.lstrip("#"))
    after = text[start + len(heading):]
    stop = re.search(r"(?m)^#{1," + str(level) + r"} ", after)
    return text[start:start + len(heading) + stop.start()] if stop else text[start:]


def main():
    head = git("rev-parse", "HEAD").decode().strip()
    plan = "test_plan/P106B_Bonsai-자동번역-pseudo-SFT-온라인-교사학생-검증.md"
    result = "test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md"
    headings = {
        plan: "### Stage10jW — HOLD 전체 검토와 의미 보존 복구 — CPU 완료(101 §555)",
        result: "## 555. HOLD 전량 재검토와 의미 보존 복구 캐시",
        "docs/EXPERIMENT_BASELINES.md": "### 2026-10-27 HOLD 복구 캐시는 새로운 데이터 조건이다",
        "docs/METHODS.md": "## 2026-10-27 보류 해제와 새 고유 자료의 구별",
        "docs/methods/03_knowledge_quality.md": "## 2026-10-27 — HOLD는 오류 확정률이 아니며 복구는 새 학습이 아니다",
    }
    row_prefixes = {
        "test_plan/실험계획목록.md": "| [P106B]",
        "test_result/실험목록.md": "| **101** | P106B |",
        "handoff/COMPASS.md": "| **토큰·코퍼스** |",
    }
    contract = "docs/research/20261026_전체입력풀_의미보존정제_작업계약.md"
    flags = "scripts/flag_whitelist.tsv"
    shared = list(headings) + list(row_prefixes) + [contract, flags]
    payloads = Path("/tmp/p106b_hold_recovery_01a17740_commit_v1")
    assert not payloads.exists(), "preserve previous payload directory"
    payloads.mkdir()
    records, patches = [], []
    for index, raw in enumerate(shared):
        before = git("show", head + ":" + raw).decode("utf-8")
        current = (ROOT / raw).read_text(encoding="utf-8")
        expected = before
        if raw in headings:
            assert headings[raw] not in before
            block = section(current, headings[raw])
            expected = before.rstrip() + "\n\n" + block.rstrip() + "\n"
            if raw == plan:
                expected = expected.replace("[원장](../handoff/WIP_20261026_작업원장.md)", "[당시 원장(완료 보존)](../handoff/WIP_20261026_작업원장-done.md)")
                assert "Stage11aW" not in expected and "oct27_independent" not in expected
        elif raw in row_prefixes:
            prefix = row_prefixes[raw]
            old_rows = [line for line in before.splitlines() if line.startswith(prefix)]
            new_rows = [line for line in current.splitlines() if line.startswith(prefix)]
            assert len(old_rows) == len(new_rows) == 1
            assert "555" in new_rows[0] and "Stage11" not in new_rows[0]
            expected = before.replace(old_rows[0], new_rows[0])
        elif raw == contract:
            expected = before.replace("[현재 원장](../../handoff/WIP_20261026_작업원장.md)", "[당시 원장(완료 보존)](../../handoff/WIP_20261026_작업원장-done.md)")
            assert expected != before
        elif raw == flags:
            additions = [line for line in current.splitlines() if line.startswith(("--each\t", "--proposal-name\t"))]
            assert len(additions) == 2 and all(line not in before for line in additions)
            expected = before.rstrip() + "\n" + "\n".join(additions) + "\n"
        assert expected != before, raw
        data = expected.encode("utf-8")
        target = payloads / (str(index) + ".txt")
        target.write_bytes(data)
        records.append(dict(path=raw, payload=str(target), payload_sha256=sha(data),
            working_sha256=sha(current.encode("utf-8")), partial_shared_file=expected != current))
        patches.append("".join(difflib.unified_diff(before.splitlines(keepends=True), expected.splitlines(keepends=True), fromfile="a/" + raw, tofile="b/" + raw)))
    patch = payloads / "shared.patch"
    patch.write_text("".join(patches), encoding="utf-8")
    write_json(AUDIT / "owned_shared_changes_v1.json", dict(schema="P106B_OWNED_SHARED_CHANGES_V1",
        head=head, shared_files=records, patch=str(patch), patch_sha256=sha(patch.read_bytes()),
        concurrent_stage11_excluded=True, working_source_writes=0, staging_performed=False,
        use_isolated_commit_index_to_preserve_unrelated_staged_entries=True))
    print(json.dumps(dict(shared_files=len(records), partial_shared_files=[r["path"] for r in records if r["partial_shared_file"]], patch=str(patch)), ensure_ascii=False))


if __name__ == "__main__":
    main()
