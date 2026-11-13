"""승인된 정리의 읽기 전용 metadata와 환경 사전 상태를 새 파일에 보존한다."""
from pathlib import Path
import collections
import json
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent


def save(name, value):
    with (OUT / name).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def record(path):
    info = path.lstat()
    return dict(path=str(path.relative_to(ROOT)), bytes=info.st_size,
                allocated=info.st_blocks * 512, mtime_ns=info.st_mtime_ns,
                ctime_ns=info.st_ctime_ns, ino=info.st_ino, dev=info.st_dev,
                links=info.st_nlink, symlink=path.is_symlink())


def main():
    verdict = {}
    for line in (ROOT / "checkpoints.tsv").read_text(encoding="utf-8").splitlines():
        cells = line.split("\t")
        if len(cells) >= 4 and cells[0] in ("keep", "hold", "delete"):
            verdict[cells[1]] = cells[0]
    rows = [record(p) for p in sorted((ROOT / "runs/ckpt").glob("*.pt"))]
    for row in rows:
        row["verdict"] = verdict.get(Path(row["path"]).name, "UNLISTED")
    isolated = [record(p) for p in sorted(
        (ROOT / "runs/validation/codex_smoke").glob("*/runs/ckpt/*.pt"))]
    save("CKPT_INVENTORY_BEFORE_v1.json", {
        "schema": "NOV13_CHECKPOINT_METADATA_INVENTORY_V1", "root": rows,
        "isolated": isolated, "note": "파일 metadata만 읽음. 가중치/optimizer 로드0."})
    for name, seq in (("root", rows), ("isolated", isolated)):
        print(name, "count", len(seq), "GiB", sum(r["bytes"] for r in seq) / 2**30,
              "by_verdict", dict(collections.Counter(r.get("verdict") for r in seq)))
    result = subprocess.run([sys.executable, "-X", "utf8", "scripts/cleanup_ckpt.py"],
                            cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, check=False)
    with (OUT / "ROOT_DRYRUN_v1.txt").open("x", encoding="utf-8") as stream:
        stream.write(result.stdout)
    print("root_dryrun", result.returncode, result.stdout[-1800:])
    if result.returncode:
        raise SystemExit(result.returncode)
    code = """from importlib import metadata
import json,sys
d={p.metadata['Name']:p.version for p in metadata.distributions()}
print(json.dumps({'python':sys.version,'executable':sys.executable,'packages':d}))
"""
    runtime = ROOT / "data_cache/p106b_official_eval_runtime/core6_env_20261023/bin/python"
    result = subprocess.run([str(runtime), "-c", code], cwd=ROOT, capture_output=True,
                            text=True, check=True)
    state = json.loads(result.stdout)
    save("EVAL_PACKAGES_BEFORE_v1.json", state)
    for name in ("lm_eval", "numpy", "datasets", "evaluate", "scikit-learn", "scipy",
                 "joblib", "threadpoolctl", "pip"):
        print(name, state["packages"].get(name, "MISSING"))


if __name__ == "__main__":
    main()
