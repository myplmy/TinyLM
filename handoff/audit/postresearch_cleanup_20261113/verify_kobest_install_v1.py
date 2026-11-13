"""평가 환경의 고정5종 의존성과 기존 패키지 불변을 확인한다. 모델/GPU0."""
from importlib import metadata
import argparse
import json
from pathlib import Path
import subprocess
import sys
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name

OUT = Path(__file__).resolve().parent
EXPECTED = {"evaluate": "0.4.6", "scikit-learn": "1.7.2", "scipy": "1.15.3",
            "joblib": "1.5.2", "threadpoolctl": "3.6.0"}


def save(name, value):
    with (OUT / name).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write("\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("before", "after"))
    args = parser.parse_args()
    before = json.loads((OUT / "EVAL_PACKAGES_BEFORE_v1.json").read_text())
    old = {canonicalize_name(k): v for k, v in before["packages"].items()}
    now = {canonicalize_name(p.metadata["Name"]): p.version for p in metadata.distributions()}
    plan = json.loads((OUT / "KOBEST_PIP_PLAN_v1.json").read_text())
    pending = {canonicalize_name(r["metadata"]["name"]): r["metadata"]["version"] for r in plan["install"]}
    assert pending == EXPECTED, pending
    checks = []
    for row in plan["install"]:
        assert row["download_info"]["url"].startswith("https://files.pythonhosted.org/")
        assert row["download_info"]["archive_info"]["hashes"]["sha256"]
        for raw in row["metadata"].get("requires_dist", []):
            req = Requirement(raw)
            if req.marker and not req.marker.evaluate({"extra": ""}):
                continue
            name = canonicalize_name(req.name)
            version = pending.get(name) or now.get(name)
            assert version is not None and (not req.specifier or version in req.specifier), raw
            checks.append(dict(package=row["metadata"]["name"], requirement=raw, available=version))
    changed = {name: (version, now.get(name)) for name, version in old.items() if now.get(name) != version}
    assert not changed, changed
    pip_check = subprocess.run([sys.executable, "-m", "pip", "check"], capture_output=True, text=True)
    result = dict(python=sys.version, executable=sys.executable, expected=EXPECTED,
                  dependency_checks=checks, existing_version_changes=changed,
                  pip_check_returncode=pip_check.returncode, pip_check_output=pip_check.stdout + pip_check.stderr)
    if args.phase == "after":
        added = {name: version for name, version in now.items() if name not in old}
        assert added == EXPECTED, added
        import evaluate
        import scipy
        import sklearn
        import joblib
        import threadpoolctl
        from sklearn.metrics import f1_score
        assert abs(f1_score([0, 1, 1, 0], [0, 1, 0, 0], average="macro") - 11 / 15) < 1e-12
        result.update(packages=now, added=added, imports=True, toy_macro_f1=11 / 15,
                      note="CPU 의존성/지표 준비. 모델 평가·전체 KoBEST 점수는 미실행.")
    save("KOBEST_DEPENDENCIES_" + args.phase.upper() + "_v1.json", result)
    print(args.phase, "dependency checks", len(checks), "existing changes", len(changed),
          "pip_check", pip_check.returncode)


if __name__ == "__main__":
    main()
