"""Use the frozen common P109C evaluation for the visit-count training arm."""

from pathlib import Path
from unittest.mock import patch

from scripts import eval_p109c_mixed_v2 as common


MODEL_NAME = "p109c-scratch-mixed-v2-balanced-visits"
original_sources = common.pinned_sources
original_worker = common.worker


def sources():
    files = original_sources()
    path = Path(__file__).resolve()
    files[str(path.relative_to(common.original.ROOT))] = common.original.core6.digest(path)
    return files


def worker(*args):
    with patch.object(common, "MODEL_NAME", MODEL_NAME), patch.object(common, "pinned_sources", sources):
        original_worker(*args)


if __name__ == "__main__":
    with patch.object(common, "worker", worker), patch.object(common, "pinned_sources", sources):
        raise SystemExit(common.main())
