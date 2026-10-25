#!/usr/bin/env python3
"""Recheck index bytes and explicitly classify only EOF blank findings."""
from pathlib import Path
import json
import subprocess

ROOT = Path(__file__).resolve().parents[3]
BASE = Path(__file__).resolve().parent

def main():
    prior = json.loads((BASE / "closed_index_verification_v2.json").read_text())
    paths = prior["explicit_paths"]
    names = subprocess.check_output(["git", "diff", "--cached", "--no-renames", "--name-only", "-z"], cwd=ROOT)
    assert set(names.decode().split(chr(0))) - {""} == set(paths)
    for name in paths:
        result = subprocess.run(["git", "show", ":" + name], cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if (ROOT / name).exists():
            assert result.returncode == 0 and result.stdout == (ROOT / name).read_bytes(), name
        else:
            assert result.returncode != 0, name
    source = [name for name in paths if not name.startswith(("test_result/evidence/", "smoketest_logs/"))
        and "_log_" not in name and "/launcher_archive/" not in name and not name.endswith(".txt")]
    checked = subprocess.run(["git", "diff", "--cached", "--check", "--", *source], cwd=ROOT,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    lines = checked.stdout.decode().splitlines()
    assert checked.returncode == 2 and len(lines) == 26
    assert all(line.endswith("new blank line at EOF.") for line in lines)
    assert lines == prior["strict_eof_blank_findings_preserved"]
    value = {"schema": "TINYLM_FROZEN_EOF_REVIEW_V1", "actual_source_diff_check_exit": checked.returncode,
        "findings": lines, "classification": "ONLY_ADDITIONAL_FINAL_BLANK_LINES",
        "all_staged_bytes_reverified": True, "staged_paths": len(paths),
        "full_diff_check_claim": "NOT_PASS", "functional_source_pin_rewrite": False,
        "review_decision": "PRESERVE_FROZEN_BYTES_AND_ALLOW_LOCAL_COMMIT",
        "trailing_spaces_or_other_source_whitespace": 0, "global_git_config_changed": False}
    with (BASE / "closed_index_accepted_eof_v1.json").open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, sort_keys=True)
    print(json.dumps({key:value for key,value in value.items() if key != "findings"}))

if __name__ == "__main__":
    main()
