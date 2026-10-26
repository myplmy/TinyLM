"""One closed-milestone allowlist, excluding the running teacher namespace."""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parent
EXACT = {
    "AGENTS.md", "ai_dev_tool/Codex/00_WORKING_RULES.md",
    "ai_dev_tool/Codex/00_작업규약_한글판.md",
    "ai_dev_tool/Codex/06_Codex용_프로젝트지침과_메모리.md",
    "ai_dev_tool/Codex/08_AI-미보고-내역-자백원장.md", "checkpoints.tsv",
    "docs/EXPERIMENT_BASELINES.md", "docs/METHODS.md",
    "docs/research/20261023_모델별_벤치마크와_실제답변_종합.md",
    "docs/research/20261026_전체300M_두모델_실제48답_판독.md",
    "experiments.tsv", "handoff/COMPASS.md", "handoff/WIP_20261022_작업원장.md",
    "scripts/diag_p106b_native_format_dialogue.py", "scripts/diag_p106b_native_format_official.py",
    "scripts/summarize_p106b_native_format_pair.py", "scripts/test_p106b_native_format_official.py",
    "test_plan/P005b_Muon-레시피-정렬과-QK-norm-상한.md",
    "test_plan/P106B_Bonsai-자동번역-pseudo-SFT-온라인-교사학생-검증.md",
    "test_plan/실험계획목록.md",
    "test_result/078_20260911_P005b-RMS4는-jordan20을-이겼지만-한-형상이다.md",
    "test_result/101_20260927_P106B-번역9건으로-문턱미달-학생학습0.md", "test_result/실험목록.md",
}
CLOSED = (
    "test_result/evidence/p106b_gemma_capacity_resume_v1_20261026_rootb/",
    "test_result/evidence/p106b_native_format_training_v1_20261026_format_normuon_train/",
    "test_result/evidence/p106b_native_format_official_v1_20261026_",
    "test_result/evidence/p106b_native_format_dialogue_v1_20261026_",
    "test_result/evidence/p106b_native_format_pair_stats_v1_20261026_",
)
LIVE = "test_result/evidence/p106b_gemma_capacity_resume_v1_20261026_rootc/"
LIVE_LOG = "test_result/101_log_20261026_P106B_Stage4fsZbW_capacity_after_eval_resume.txt"


def main(destination_name="full_pair_stage_manifest_v1.json"):
    raw = subprocess.check_output([
        "git", "-c", "status.renames=false", "status", "--porcelain=v1", "-z", "--untracked-files=all",
        "--", ".", ":(exclude)datasets/TinyDataset/**", ":(exclude).agents/**",
        ":(exclude).codex/**", ":(exclude).aws/**"], cwd=ROOT)
    entries, excluded, unexpected = [], [], []
    for part in raw.split(bytes([0])):
        if not part:
            continue
        name = part[3:].decode()
        if name.startswith(LIVE) or name == LIVE_LOG or (
            name.startswith("handoff/audit/oct26_research/postfull_async_v1/")
            and Path(name).name not in ["inputs.json", "step_00.json", "step_01.json", "step_02.json"]
        ):
            excluded.append(name)
            continue
        allowed = (name in EXACT or name.startswith("handoff/audit/oct26_research/")
            or name.startswith(CLOSED) or name.startswith("run_P106B_Stage10") and name.endswith(".sh")
            or name in ["run_P106B_Stage4fsZW_capacity_mtp_continue4h.sh",
                        "run_P106B_Stage4fsZW_capacity_mtp_continue4h-done.sh",
                        "run_P106B_Stage4fsZbW_capacity_after_eval_resume.sh"]
            or name.startswith("test_result/101_log_20261026_P106B_Stage10")
            or name == "test_result/101_log_20261026_P106B_Stage4fsZW_capacity_mtp_continue4h.txt")
        if not allowed:
            unexpected.append(name)
            continue
        path = ROOT / name
        if path.is_symlink():
            raise ValueError("symlink " + name)
        if not path.exists():
            if not name.startswith("run_P106B_") or not name.endswith(".sh"):
                raise ValueError("unverified deletion")
            variants = [ROOT / (name[:-3] + suffix + ".sh") for suffix in ["-done", "-hold"]]
            matches = [p for p in variants if p.is_file()]
            if len(matches) != 1:
                raise ValueError("rename destination")
            head = subprocess.check_output(["git", "show", "HEAD:" + name], cwd=ROOT)
            if matches[0].read_bytes() != head:
                raise ValueError("renamed bytes")
            entries.append(dict(path=name, deleted_after_source_archive=True,
                                rename_preserved_at=str(matches[0].relative_to(ROOT))))
        else:
            if not path.is_file() or path.stat().st_size >= 20_000_000:
                raise ValueError("non-file or oversized " + name)
            content = path.read_bytes()
            entries.append(dict(path=name, bytes=len(content),
                                sha256=hashlib.sha256(content).hexdigest().upper()))
    if unexpected:
        raise ValueError("unclassified paths: " + repr(unexpected))
    audit = json.loads((BASE / "static_precommit7_v5.json").read_text())
    if audit["counts"]["errors"] != 0:
        raise ValueError("current static errors")
    manifest = dict(schema="TINYLM_EXPLICIT_CLOSED_STAGE_V1", files=entries,
        excluded_live_or_unrelated=excluded, protected_access=False, gpu_quality_claim=False,
        current_static_audit="handoff/audit/oct26_research/static_precommit7_v5.json",
        approved_basis="Current autonomous research, exact-path staging and Korean local commits; WIP88-91")
    if Path(destination_name).name != destination_name or not destination_name.endswith(".json"):
        raise ValueError("one fresh local JSON manifest name is required")
    destination = BASE / destination_name
    with destination.open("x", encoding="utf-8") as out:
        json.dump(manifest, out, ensure_ascii=False, indent=2, sort_keys=True)
        out.write(chr(10))
    print(json.dumps(dict(files=len(entries), bytes=sum(x.get("bytes", 0) for x in entries),
        deleted_original_launcher_paths=sum(x.get("deleted_after_source_archive", False) for x in entries),
        excluded_live=excluded, largest=sorted([(x.get("bytes", 0), x["path"]) for x in entries], reverse=True)[:4]),
        ensure_ascii=False))


if __name__ == "__main__":
    main()
