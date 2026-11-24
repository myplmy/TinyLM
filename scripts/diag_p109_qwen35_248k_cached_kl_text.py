"""Measure the native full request for the actual packed teacher-trained G4."""

from hashlib import sha256
from pathlib import Path
from unittest.mock import patch

from scripts import diag_p109_qwen_248k_text as original
from scripts import diag_p109_qwen35_248k_cached_kl as trained


TAG = "p109_qwen35_248k_cached_kl_text_v1_20261119"
OUT = trained.OUT.with_name(TAG)
PRIOR_BUILD = original.OUT / "compiler.json"
DEVICE_COMPILE = original.engine.compile_binaries


def reuse_binaries():
    record = original.io.load(PRIOR_BUILD)
    rendered = [sha256(s).hexdigest().upper() for s in original.render()]
    assert rendered == record["source_sha256"]
    names = ("fp32", "int8", "text")
    binaries = tuple(Path(record["binaries"][k]["path"]) for k in names)
    if not all(p.is_file() for p in binaries):
        return DEVICE_COMPILE()
    assert all(original.io.digest(p)==record["binaries"][k]["sha256"] for k,p in zip(names,binaries,strict=True))
    original.io.write(OUT/"compiler.json",dict(**record,reused_from_sha256=original.io.digest(PRIOR_BUILD)))
    return binaries


def main():
    source = Path(__file__)
    pinned = original.io.digest(source)
    with (
        patch.object(original,"OUT",OUT),
        patch.object(original,"TAG",TAG),
        patch.object(original.learned,"OUT",trained.OUT),
        patch.object(original.learned,"PROFILE",trained.PROFILE),
        patch.object(original.learned,"EXPORT",trained.EXPORT),
        patch.object(original.engine,"compile_binaries",reuse_binaries),
    ):
        status=original.run()
    assert original.io.digest(source)==pinned
    original.io.write(OUT/"dispatch.json",dict(launcher_sha256=pinned,actual_exit=status))
    return status


if __name__ == "__main__":
    raise SystemExit(main())
