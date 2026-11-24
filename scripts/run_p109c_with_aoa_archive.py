"""Use the admitted P109C launcher and preserve native intermediate evaluation weights."""

from pathlib import Path
import sys
from unittest.mock import patch

from scripts import run_p109c_scratch330 as entry
from tinylm.train import packed_document_training, trainer


NATIVE_WORKER = entry.gpu_worker


class EvaluationArchive:
    """Archive scheduled primary saves without changing native checkpoint contents."""

    def __init__(self, directory, checkpoint, steps, save):
        self.directory = directory
        self.checkpoint = checkpoint
        self.steps = tuple(steps)
        self.save = save
        self.snapshots = {}

    def __call__(self, path, state):
        self.save(path, state)
        if Path(path) != self.checkpoint:
            return
        step = state["step"]
        if step not in self.steps or step in self.snapshots:
            return
        cursor = state[trainer.CONTEXT_STATE_KEY]["cursor"]["cursor"]
        if cursor["optimizer_updates"] != step:
            raise ValueError("evaluation snapshots require a completed optimizer update")
        head = {key for key in state["model"] if key.startswith("decimal_head.")}
        if head != {"decimal_head.weight", "decimal_head.bias"}:
            raise ValueError("the P109C training-only head differs")
        output = self.directory / f"aoa_step_{step}.pt"
        if output.exists() or output.is_symlink():
            raise FileExistsError(output)
        inference = {key: state[key] for key in ("cfg", "step", "tokenizer_sha256")}
        inference["model"] = {key: value for key, value in state["model"].items() if key not in head}
        self.save(output, inference)
        receipt = dict(step=step, optimizer_updates=step, checkpoint=output.name,
                       sha256=entry.file_sha(output).upper(), bytes=output.stat().st_size,
                       tokenizer_sha256=inference["tokenizer_sha256"],
                       input_slots=step * entry.MICRO * entry.ACCUM * entry.WIDTH)
        entry.publish(output.with_suffix(".json"), receipt)
        self.snapshots[step] = receipt


def worker(path, sha256, resume, record, cutoff, *, reuse_quantization=False):
    archive_dir = record / "evaluation_steps"
    archive_dir.mkdir(exist_ok=False)
    checkpoint = trainer.CKPT / f"{entry.PRESET}_ko-en_330M_{entry.TAG}.pt"
    steps = range(entry.EVAL_EVERY, entry.BOUNDARY + 1, entry.EVAL_EVERY)
    archive = EvaluationArchive(archive_dir, checkpoint, steps, packed_document_training.save_packed_checkpoint)
    entry.publish(archive_dir / "schedule.json", dict(expected_steps=list(steps),
        final_evaluation="../evaluation.pt", parent_manifest_sha256=entry.digest(sha256),
        snapshot_source_sha256=entry.file_sha(Path(__file__)).upper(), resume=resume,
        x_axis="optimizer_updates_and_input_slots", official_aoa_scored=False))
    with patch.object(packed_document_training, "save_packed_checkpoint", archive):
        NATIVE_WORKER(path, sha256, resume, record, cutoff, reuse_quantization=reuse_quantization)
    missing_steps = [step for step in steps if step not in archive.snapshots]
    entry.publish(archive_dir / "index.json", dict(captured=list(archive.snapshots.values()),
        missing_in_this_run=missing_steps, final_evaluation_sha256=entry.file_sha(record / "evaluation.pt").upper()))
    if missing_steps and not resume:
        raise RuntimeError("the completed run lacks scheduled evaluation weights")


def main():
    with patch.object(entry, "gpu_worker", worker):
        return entry.main()


if __name__ == "__main__":
    sys.exit(main())
