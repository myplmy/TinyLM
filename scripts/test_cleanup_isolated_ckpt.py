#!/usr/bin/env python3
"""CPU 임시폴더 시험. 실제 저장소의 체크포인트·모델·GPU를 사용하지 않는다."""
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timedelta, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import shlex
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cleanup_isolated_ckpt as cleaner


def no_busy(*_):
    return set()


class IsolatedCleanupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="tinylm_cleanup_test_")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.sid = "fixture_v1"
        self.runtime = cleaner.RUNTIME / self.sid
        self.stem = "tiny_synthetic_2M_sm_base"
        self.result = self.runtime / "runs/logs" / (self.stem + ".json")
        self.report = cleaner.EVIDENCE / self.sid / "smoke_report.json"
        self.raw = Path("smoketest_logs/fixture_v1.txt")
        self.checkpoints = [self.runtime / "runs/ckpt" / (self.stem + end)
                            for end in (".pt", "_best.pt")]
        self.write(Path("runs/ckpt/research_keep.pt"), b"unrelated research checkpoint")
        (self.root / "runs/logs").mkdir(parents=True)
        self.write(Path("checkpoints.tsv"), b"verdict\tfile\tmb\twhy\nkeep\tresearch_keep.pt\t1\tparent\n")
        for item in self.checkpoints:
            self.write(item, b"synthetic checkpoint fixture bytes")
        self.write_json(self.result, dict(preset="tiny", data="synthetic", arch="dense",
                        tag=self.stem, steps=3, final=dict(val_loss=1.0), init_from_src=None))
        child = [sys.executable, "run100m.py", "train", "--tiny", "--data", "synthetic",
                 "--tokens", "2M", "--arch", "dense", "--tag", "sm_base", "--steps", "3"]
        summary = [sys.executable, "scripts/summarize_smoke.py", "--log", str(self.root / self.raw)]
        outer = [sys.executable, "scripts/runlog.py", "--name", "smoke_codex_" + self.sid, "--"]
        actions = [dict(kind="run", line=1, argv=outer + child, seconds=0),
                   dict(kind="sleep", line=2, argv=[], seconds=1)]
        receipts = [dict(index=0, kind="run", line=1, executed_argv=outer + child,
                         child=True, status="COMPLETE", returncode=0, error=None,
                         unsafe_process_state=False, interrupted_during_cleanup=False,
                         launch_state="OWNED", process_started=True),
                    dict(index=1, kind="sleep", line=2, executed_argv=[], child=False,
                         status="COMPLETE", returncode=0, error=None, duration_sec=1.1)]
        raw = "".join(f"[runlog] cmd={shlex.join(cmd)}\nfixture body\n[runlog] 종료코드 0 소요 0\n"
                      for cmd in (child, summary)).encode("utf-8")
        self.write(self.raw, raw)
        pins = {"scripts/batch/tool_smoke.bat": "1" * 64, "scripts/codex_smoke.py": "2" * 64,
                "scripts/smoke_execution_contract.py": "3" * 64}
        self.write_json(self.report, dict(schema="TINYLM_CODEX_SMOKE_EXECUTION_V1",
            profile_id="codex_isolated_smoke_v1", session_id=self.sid, runtime=str(self.runtime),
            started_at=(datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(),
            finished_at=datetime.now(timezone.utc).isoformat(),
            source="scripts/batch/tool_smoke.bat", driver="scripts/codex_smoke.py",
            complete=True, returncode=0, failed_calls=0, failed_run_calls=0,
            summary_returncode=0, summary_status="COMPLETE", interrupted=False, timed_out=False,
            snapshot_errors=[], safety_errors=[], source_pins_before=pins,
            source_pins_after=pins, source_pins_unchanged=True,
            source_sha256="1" * 64, driver_sha256="2" * 64, contract_module_sha256="3" * 64,
            action_manifest=actions, receipts=receipts, action_count=2, child_count=1,
            training_count=1, log=str(self.raw), log_bytes=len(raw),
            log_sha256=hashlib.sha256(raw).hexdigest().upper(), summary_command=outer + summary))

    def write(self, name, raw):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)

    def write_json(self, name, value):
        self.write(name, json.dumps(value, ensure_ascii=False).encode("utf-8"))

    def edit_json(self, name, **values):
        data = json.loads((self.root / name).read_text())
        data.update(values)
        self.write_json(name, data)

    def plan(self):
        return cleaner.build_plan(self.root, busy_check=no_busy)

    def assert_hold(self, plan=None):
        row = (self.plan() if plan is None else plan)["rows"][0]
        self.assertEqual("HOLD", row["status"], row)
        self.assertEqual([], row["files"])
        self.assertTrue(all((self.root / p).exists() for p in self.checkpoints))

    def main(self, args, answer=None):
        with patch.object(cleaner, "ROOT", self.root), patch.object(cleaner, "busy_sessions", no_busy), \
                patch.object(cleaner, "build_plan", wraps=lambda root, ids=None, **kw:
                             cleaner_plan(root, ids, busy_check=no_busy)), \
                patch("builtins.input", return_value=answer), redirect_stdout(io.StringIO()), \
                redirect_stderr(io.StringIO()):
            return cleaner.main(args)

    def test_preview_proves_paths_without_reading_weights(self):
        plan = self.plan()
        self.assertEqual("ELIGIBLE", plan["rows"][0]["status"])
        self.assertEqual(set(map(str, self.checkpoints)), {x["path"] for x in plan["rows"][0]["files"]})
        self.assertFalse(any(name.endswith(".pt") for name in plan["inputs"]))
        before = {p: cleaner.identity(self.root / p) for p in self.checkpoints}
        self.assertEqual(0, self.main([]))
        self.assertEqual(before, {p: cleaner.identity(self.root / p) for p in self.checkpoints})
        self.assertFalse((self.root / cleaner.AUDIT).exists())

    def test_cancel(self):
        self.assertEqual(0, self.main(["--interactive"], "no"))
        self.assertTrue(all((self.root / p).exists() for p in self.checkpoints))

    def test_interactive_yes_deletes_frozen_fixture(self):
        with patch.object(cleaner, "apply_plan", wraps=lambda plan, root:
                          cleaner_apply(plan, root, busy_check=no_busy)):
            self.assertEqual(0, self.main(["--interactive"], "YES"))
        self.assertTrue(all(not (self.root / p).exists() for p in self.checkpoints))

    def test_delete_only_proven_files_and_keep_evidence(self):
        plan = self.plan()
        keep = {p: (self.root / p).read_bytes() for p in
                [self.result, self.report, self.raw, Path("runs/ckpt/research_keep.pt"), Path("checkpoints.tsv")]}
        receipt = cleaner.apply_plan(plan, self.root, busy_check=no_busy)
        self.assertEqual(("COMPLETE", 2), (receipt["status"], receipt["deleted"]))
        self.assertTrue(all(not (self.root / p).exists() for p in self.checkpoints))
        self.assertEqual(keep, {p: (self.root / p).read_bytes() for p in keep})
        self.assertTrue((self.root / self.checkpoints[0].parent).is_dir())
        self.assertEqual("EMPTY", self.plan()["rows"][0]["status"])

    def test_repeated_empty_apply_does_not_create_another_audit(self):
        for p in self.checkpoints:
            (self.root / p).unlink()
        self.assertEqual("EMPTY", cleaner.apply_plan(self.plan(), self.root, busy_check=no_busy)["status"])
        self.assertFalse((self.root / cleaner.AUDIT).exists())

    def test_failed_incomplete_and_interrupted_receipts_are_held(self):
        original = (self.root / self.report).read_bytes()
        for fields in [dict(returncode=1), dict(complete=False), dict(interrupted=True), dict(timed_out=True)]:
            with self.subTest(fields=fields):
                self.write(self.report, original)
                self.edit_json(self.report, **fields)
                self.assert_hold()

    def test_current_source_does_not_need_to_equal_old_execution(self):
        self.assertEqual("ELIGIBLE", self.plan()["rows"][0]["status"])
        # fixture의 과거 소스 SHA는 현재 checkout과 의도적으로 다르다.
        self.edit_json(self.report, source_pins_after={"unmatched": "F" * 64})
        self.assert_hold()

    def test_raw_log_change_is_held(self):
        self.write(self.raw, b"changed raw log")
        self.assert_hold()

    def test_malformed_report_is_held(self):
        self.edit_json(self.report, started_at=None)
        self.assert_hold()

    def test_forged_synthetic_filename_is_not_enough(self):
        self.edit_json(self.result, data="ko-en")
        self.assert_hold()

    def test_checkpoint_overwritten_after_smoke_is_held(self):
        path = self.root / self.checkpoints[0]
        info = path.stat()
        os.utime(path, ns=(info.st_atime_ns, info.st_mtime_ns + 10**12))
        self.assert_hold()

    def test_real_data_command_is_held(self):
        data = json.loads((self.root / self.report).read_text())
        argv = data["action_manifest"][0]["argv"]
        argv[argv.index("--data") + 1] = "ko-en"
        data["receipts"][0]["executed_argv"] = argv
        self.write_json(self.report, data)
        self.assert_hold()

    def test_unknown_file_holds_whole_session(self):
        self.write(self.checkpoints[0].parent / "unlisted.pt", b"unknown")
        self.assert_hold()

    def test_symlink_checkpoint_is_held(self):
        path = self.root / self.checkpoints[0]
        path.unlink()
        path.symlink_to(self.root / "runs/ckpt/research_keep.pt")
        self.assert_hold()

    def test_symlink_ancestor_is_held(self):
        path = self.root / self.checkpoints[0].parent
        alternate = path.with_name("preserved")
        path.rename(alternate)
        path.symlink_to(alternate, target_is_directory=True)
        self.assert_hold()

    def test_hardlink_is_held(self):
        os.link(self.root / self.checkpoints[0], self.root / "another_link.pt")
        self.assert_hold()

    def test_other_run_parent_reference_protects_pair(self):
        self.write_json(Path("runs/logs/consumer.json"), dict(kd_teacher=self.checkpoints[1].name))
        self.assert_hold()

    def test_same_session_parent_reference_is_allowed(self):
        self.edit_json(self.result, init_from_src=self.checkpoints[0].name)
        self.assertEqual("ELIGIBLE", self.plan()["rows"][0]["status"])

    def test_other_isolated_sessions_internal_same_name_does_not_protect_this_one(self):
        other = cleaner.RUNTIME / "fixture_v2"
        shutil.copytree(self.root / self.runtime, self.root / other)
        self.edit_json(other / "runs/logs" / (self.stem + ".json"),
                       init_from_src=self.checkpoints[0].name)
        plan = cleaner.build_plan(self.root, [self.sid], busy_check=no_busy)
        self.assertEqual("ELIGIBLE", plan["rows"][0]["status"])

    def test_explicit_cross_session_reference_protects_target(self):
        other = cleaner.RUNTIME / "fixture_v2"
        shutil.copytree(self.root / self.runtime, self.root / other)
        self.edit_json(other / "runs/logs" / (self.stem + ".json"),
                       init_from_src=str(self.root / self.checkpoints[0]))
        self.assert_hold(cleaner.build_plan(self.root, [self.sid], busy_check=no_busy))

    def test_uncertain_parent_reference_is_held(self):
        self.write_json(Path("runs/logs/uncertain_parent.json"),
                        dict(init_from_src=str(cleaner.RUNTIME / "elsewhere/.." / self.sid
                                              / "runs/ckpt" / self.checkpoints[0].name)))
        self.assert_hold()

    def test_registry_keep_protects_pair(self):
        self.write(Path("checkpoints.tsv"), f"hold\t{self.checkpoints[0].name}\t1\tkeep\n".encode())
        self.assert_hold()

    def test_active_session_is_held(self):
        self.assert_hold(cleaner.build_plan(self.root, busy_check=lambda *_: {self.sid}))

    def test_unreadable_process_guard_is_fail_closed(self):
        def refused(*_):
            raise PermissionError("cannot inspect proc")
        self.assert_hold(cleaner.build_plan(self.root, busy_check=refused))

    def test_self_open_checkpoint_is_detected(self):
        item = cleaner.identity(self.root / self.checkpoints[0])
        with (self.root / self.checkpoints[0]).open("rb"):
            try:
                active = cleaner.busy_sessions(self.root, [self.sid], [(self.sid, item)])
            except cleaner.SafetyError as exc:
                self.assertIn("확인할 수 없습니다", str(exc))
            else:
                self.assertIn(self.sid, active)

    def test_changed_target_after_preview_stops_before_deletion(self):
        plan = self.plan()
        self.write(self.checkpoints[0], b"replacement")
        with self.assertRaises(cleaner.SafetyError):
            cleaner.apply_plan(plan, self.root, busy_check=no_busy)
        self.assertTrue(all((self.root / p).exists() for p in self.checkpoints))

    def test_new_reference_after_preview_stops_before_deletion(self):
        plan = self.plan()
        self.write_json(Path("runs/logs/new_parent.json"), dict(init_from_src=self.checkpoints[0].name))
        with self.assertRaises(cleaner.SafetyError):
            cleaner.apply_plan(plan, self.root, busy_check=no_busy)
        self.assertTrue(all((self.root / p).exists() for p in self.checkpoints))

    def test_changed_evidence_after_preview_stops_before_deletion(self):
        plan = self.plan()
        self.edit_json(self.result, steps=4)
        with self.assertRaises(cleaner.SafetyError):
            cleaner.apply_plan(plan, self.root, busy_check=no_busy)
        self.assertTrue(all((self.root / p).exists() for p in self.checkpoints))

    def test_final_unlink_identity_check(self):
        item = self.plan()["rows"][0]["files"][0]
        self.write(Path(item["path"]), b"different")
        with self.assertRaises(cleaner.SafetyError):
            cleaner.delete_one(self.root, item)
        self.assertTrue((self.root / item["path"]).exists())

    def test_parent_directory_replaced_at_unlink_is_rejected(self):
        item = self.plan()["rows"][0]["files"][0]
        parent = (self.root / item["path"]).parent
        parent.rename(parent.with_name("moved_ckpt"))
        parent.mkdir()
        self.write(Path(item["path"]), b"different directory")
        with self.assertRaises(cleaner.SafetyError):
            cleaner.delete_one(self.root, item)
        self.assertTrue((self.root / item["path"]).exists())

    def test_partial_io_failure_keeps_receipt_and_journal(self):
        plan = self.plan()
        calls = []
        def fail_second(root, item):
            if calls:
                raise OSError("fixture failure on second unlink")
            cleaner.delete_one(root, item)
            calls.append(item)
        with self.assertRaises(OSError):
            cleaner.apply_plan(plan, self.root, busy_check=no_busy, unlink=fail_second)
        files = list((self.root / cleaner.AUDIT).glob("*/receipt.json"))
        self.assertEqual(1, len(files))
        receipt = json.loads(files[0].read_text())
        self.assertEqual(("PARTIAL_ERROR", 1), (receipt["status"], receipt["deleted"]))
        events = [json.loads(line)["event"] for line in (files[0].parent / "journal_0001.jsonl").read_text().splitlines()]
        self.assertEqual(["INTENT", "DELETED", "INTENT"], events)
        self.assertEqual(1, sum((self.root / p).exists() for p in self.checkpoints))
        self.assertTrue((self.root / self.raw).exists())

    def test_manifest_sha_and_explicit_apply(self):
        name = cleaner.AUDIT / "approved_fixture.json"
        self.assertEqual(0, self.main(["--output", str(name)]))
        raw = (self.root / name).read_bytes()
        self.assertEqual(2, self.main(["--apply", "--manifest", str(name), "--manifest-sha256", "0" * 64]))
        self.assertTrue(all((self.root / p).exists() for p in self.checkpoints))
        # main의 apply도 임시 root를 명시적으로 사용한다.
        with patch.object(cleaner, "apply_plan", wraps=lambda plan, root:
                          cleaner_apply(plan, root, busy_check=no_busy)):
            self.assertEqual(0, self.main(["--apply", "--manifest", str(name), "--manifest-sha256",
                                         hashlib.sha256(raw).hexdigest()]))
        self.assertTrue(all(not (self.root / p).exists() for p in self.checkpoints))

    def test_write_once_and_audit_path_boundary(self):
        name = cleaner.AUDIT / "preview.json"
        cleaner.write_new(self.root, name, self.plan())
        before = (self.root / name).read_bytes()
        with self.assertRaises(FileExistsError):
            cleaner.write_new(self.root, name, self.plan())
        self.assertEqual(before, (self.root / name).read_bytes())
        for name in [Path("datasets/TinyDataset/not_allowed.json"), Path("../escape.json")]:
            with self.subTest(name=name), self.assertRaises(cleaner.SafetyError):
                cleaner.write_new(self.root, name, {})

    def test_no_bare_yes_option_or_apply_without_sha(self):
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            cleaner.main(["--yes"])
        self.assertEqual(2, self.main(["--apply"]))
        self.assertTrue(all((self.root / p).exists() for p in self.checkpoints))


cleaner_plan = cleaner.build_plan
cleaner_apply = cleaner.apply_plan

if __name__ == "__main__":
    unittest.main(verbosity=2)
