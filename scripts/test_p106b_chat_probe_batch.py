"""CPU JSON/tokenizer/emitter fixtures only; no learned model or checkpoint loads."""
from __future__ import annotations

from contextlib import ExitStack, contextmanager, nullcontext, redirect_stderr, redirect_stdout
import copy
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import p106b_chat_probe_batch as b


class Tokenizer:
    def encode(self, text): return NS(ids=[10 + i % 200 for i in range(len(text))])


def questions():
    return [dict(id='code', language='ko', category='code_arithmetic', question='6 곱하기 7은?', expected_exact='42'),
            dict(id='open', language='en', category='explanation', question='Explain why sleep matters.', expected_exact=None)]


def receipt(proof, *, reason='STOP_SEQUENCE', max_new=8):
    ids = [11, 12, 4] if reason == 'STOP_SEQUENCE' else [11, 2] if reason == 'EOS' else [11] * max_new
    terminal = [4] if reason == 'STOP_SEQUENCE' else [2] if reason == 'EOS' else []
    return dict(finish_reason=reason, generated_tokens=len(ids), generated_ids=ids,
        prompt_tokens=proof['prompt_tokens'], prompt_sha256=proof['prompt_sha256'],
        precision='FP32_MATH', tf32=False, actual_history=False, mtp=False, use_cache=True,
        temperature=0., top_k=1, terminal_only_removed=True, terminal_ids=terminal,
        content_tokens=len(ids) - bool(terminal), matched_stop_sequence=[4] if reason == 'STOP_SEQUENCE' else None)


def inputs():
    rows = questions(); proofs = b.question_proofs(rows, Tokenizer(), 8)
    lineage = dict(model='SYNTHETIC_CPU_FIXTURE', checkpoint_sha256='A' * 64, core_sha256='B' * 64,
        tokenizer_sha256='C' * 64, source=dict(sha256='D' * 64),
        questions_sha256=b.common.sha(rows), proofs_sha256=b.common.sha(proofs))
    by_question = {row['question']: (row, proof) for row, proof in zip(rows, proofs)}
    def emit(question):
        row, proof = by_question[question]
        return ('42' if row['expected_exact'] else 'A human should review this explanation.'), receipt(proof)
    return rows, proofs, lineage, emit


class Guarded(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack(); self.addCleanup(self.stack.close)
        self.stack.enter_context(patch('builtins.input', side_effect=AssertionError('no input prompt')))
        self.stack.enter_context(patch.object(b.ui, 'selected_runtime', side_effect=AssertionError('no learned model runtime')))
        self.stack.enter_context(patch.object(b.ui, 'emit', side_effect=AssertionError('no actual generation')))


class DataAndDiagnosticTests(Guarded):
    def test_exact_utf8_source_and_schema_are_preserved(self):
        raw = ''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in questions()).encode('utf-8')
        with tempfile.TemporaryDirectory(prefix='chat_probe_source_') as folder:
            root = Path(folder); path = root / 'questions.jsonl'; path.write_bytes(raw)
            rows, source = b.load_questions(path, root)
        self.assertEqual(rows, questions()); self.assertEqual(source['count'], 2)
        self.assertEqual(source['sha256'], hashlib.sha256(raw).hexdigest().upper())

    def test_duplicate_empty_unknown_language_extra_history_and_bad_expected_are_refused(self):
        variants = [[]]
        for field, value in (('id', ''), ('question', ' '), ('language', 'fr'), ('expected_exact', ''), ('expected_exact', 42)):
            rows = questions(); rows[0][field] = value; variants.append(rows)
        rows = questions(); rows[1]['id'] = rows[0]['id']; variants.append(rows)
        rows = questions(); rows[0]['history'] = []; variants.append(rows)
        for rows in variants:
            with self.assertRaises(ValueError): b.validate_questions(rows)

    def test_duplicate_json_fields_blank_rows_invalid_utf8_are_refused(self):
        with tempfile.TemporaryDirectory(prefix='chat_probe_bad_') as folder:
            root = Path(folder); path = root / 'questions.jsonl'
            for value in (b'\n', b'\xff\n', b'{"id":"x","id":"y"}\n'):
                path.write_bytes(value)
                with self.assertRaises((ValueError, UnicodeError)): b.load_questions(path, root)

    def test_expected_answer_cannot_change_actual_question_prompt(self):
        rows = questions(); before = b.question_proofs(rows, Tokenizer(), 8)
        rows[0]['expected_exact'] = 'a secret answer that must not be sent to the model'
        self.assertEqual(before, b.question_proofs(rows, Tokenizer(), 8))
        from tinylm.chat.serialize import serialize
        prompt = serialize(dict(messages=b.ui.prompt_messages(rows[0]['question'], ())), 'chatml', add_generation_prompt=True)
        self.assertNotIn(rows[0]['expected_exact'], prompt)

    def test_oversized_complete_prompt_is_not_truncated(self):
        rows = questions(); rows[0]['question'] = 'x' * 1024
        with self.assertRaises(ValueError): b.question_proofs(rows, Tokenizer(), 8)
        for value in (0, True, 1025):
            with self.assertRaises(ValueError): b.question_proofs(questions(), Tokenizer(), value)

    def test_open_explanation_has_no_automatic_correctness_and_whitespace_is_only_normalization(self):
        self.assertIsNone(b.whitespace_diagnostic('Any answer.', None)['whitespace_exact'])
        self.assertTrue(b.whitespace_diagnostic(' \n 4\t2  ', '4 2')['whitespace_exact'])
        for actual, expected in (('42', '4 2'), ('paris', 'Paris'), ('Paris.', 'Paris'), ('-5', '5'), ('1.5', '15')):
            self.assertFalse(b.whitespace_diagnostic(actual, expected)['whitespace_exact'])


class ReceiptAndSummaryTests(Guarded):
    def test_eot_eos_and_cap_receipts_are_preserved(self):
        proof = inputs()[1][0]
        for reason in ('STOP_SEQUENCE', 'EOS', 'MAX_NEW'):
            self.assertTrue(b.validate_generation(receipt(proof, reason=reason), proof, 8))

    def test_invalid_history_precision_prompt_tokens_terminal_or_count_is_refused(self):
        proof = inputs()[1][0]
        for field, value in (('actual_history', True), ('precision', 'BF16'), ('tf32', True), ('prompt_sha256', 'changed'),
                ('prompt_tokens', 0), ('generated_tokens', 0), ('generated_tokens', True), ('terminal_ids', []),
                ('content_tokens', 99), ('generated_ids', [2, 11, 4]), ('finish_reason', 'UNKNOWN')):
            meta = receipt(proof); meta[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError): b.validate_generation(meta, proof, 8)

    def test_empty_answer_is_preserved_and_never_promoted_by_stopping(self):
        rows, proofs, _, _ = inputs(); meta = receipt(proofs[0])
        meta.update(generated_ids=[4], generated_tokens=1, content_tokens=0)
        event = b.event_for(rows[0], proofs[0], '', meta, 0., 8)
        self.assertEqual(event['answer'], '')
        self.assertFalse(event['diagnostic']['whitespace_exact'])

    def test_summary_has_string_diagnostics_and_human_review_counts_but_no_chat_accuracy(self):
        rows, proofs, _, emit = inputs()
        events = [b.event_for(r, p, *emit(r['question']), .1, 8) for r, p in zip(rows, proofs)]
        report = b.summarize(events, rows, proofs, 8)
        self.assertEqual(report['responses'], 2)
        self.assertEqual(report['counts']['code_defined_diagnostics'], 1)
        self.assertEqual(report['counts']['whitespace_exact'], 1)
        self.assertEqual(report['counts']['human_review_required'], 1)
        self.assertNotIn('accuracy', report); self.assertFalse(report['history_carried_between_questions'])

    def test_missing_duplicate_source_answer_or_diagnostic_mutation_is_refused(self):
        rows, proofs, _, emit = inputs()
        raw = [b.event_for(r, p, *emit(r['question']), .1, 8) for r, p in zip(rows, proofs)]
        variants = [raw[:-1], raw + [raw[0]], [raw[0], raw[0]]]
        bad = copy.deepcopy(raw); bad[0]['source']['question'] = 'changed'; variants.append(bad)
        bad = copy.deepcopy(raw); bad[0]['diagnostic']['whitespace_exact'] = False; variants.append(bad)
        for value in variants:
            with self.assertRaises(ValueError): b.summarize(value, rows, proofs, 8)


class StorageAndLifecycleTests(Guarded):
    def test_completion_waits_for_context_exit_and_exports_new_human_review(self):
        rows, proofs, lineage, emit = inputs()
        with tempfile.TemporaryDirectory(prefix='chat_probe_output_') as folder:
            root = Path(folder); output = root / 'batch'; review = root / 'review_request' / 'answers.md'
            result, events = b.collect_batch(output, rows, proofs, lineage, emit, 8, root)
            self.assertFalse((output / 'report.json').exists()); self.assertFalse(review.exists())
            with self.assertRaises(ValueError): b.publish_batch(output, review, result, events, rows, proofs, 8, root)
            result['strict_model_context_exit_verified'] = True  # Synthetic context-success receipt.
            report = b.publish_batch(output, review, result, events, rows, proofs, 8, root)
            self.assertEqual(report['status'], 'CHAT_FIRST_ANSWERS_RECORDED_HUMAN_REVIEW_PENDING')
            text = review.read_text(encoding='utf-8'); self.assertIn(rows[0]['question'], text); self.assertIn(events[1]['answer'], text)
            self.assertIn('자동 정답 점수 없음', text); self.assertEqual(report['review']['sha256'], b.common.file_sha(review))
            self.assertTrue(all(p.stat().st_size < 20_000_000 for p in output.iterdir()))
            before = review.read_bytes()
            with self.assertRaises(FileExistsError): b.publish_batch(output, review, result, events, rows, proofs, 8, root)
            self.assertEqual(review.read_bytes(), before)

    def test_partial_generation_failure_preserves_first_answer(self):
        rows, proofs, lineage, emit = inputs(); calls = []
        def fail_second(question):
            calls.append(question)
            if len(calls) == 2: raise RuntimeError('synthetic generation failure')
            return emit(question)
        with tempfile.TemporaryDirectory(prefix='chat_probe_partial_') as folder:
            root = Path(folder); output = root / 'batch'
            with self.assertRaises(RuntimeError): b.collect_batch(output, rows, proofs, lineage, fail_second, 8, root)
            failure = json.loads((output / 'error.json').read_text())
            self.assertEqual(failure['first_answers_preserved'], 1)
            self.assertFalse((output / 'report.json').exists())
            self.assertIn('42', (output / 'answers_000000.jsonl').read_text())

    def test_raw_or_lineage_mutation_cannot_create_success_or_human_report(self):
        rows, proofs, lineage, emit = inputs()
        with tempfile.TemporaryDirectory(prefix='chat_probe_mutated_') as folder:
            root = Path(folder); output = root / 'batch'; review = root / 'review_request' / 'answers.md'
            result, events = b.collect_batch(output, rows, proofs, lineage, emit, 8, root)
            result['strict_model_context_exit_verified'] = True
            changed = copy.deepcopy(result); changed['lineage']['checkpoint_sha256'] = 'changed'
            with self.assertRaises(ValueError): b.publish_batch(output, review, changed, events, rows, proofs, 8, root)
            changed_events = copy.deepcopy(events); changed_events[0]['answer'] = 'rewritten answer'
            with self.assertRaises(ValueError): b.publish_batch(output, review, result, changed_events, rows, proofs, 8, root)
            self.assertFalse(review.exists()); self.assertFalse((output / 'report.json').exists())

    def test_wrong_proof_count_prevents_generation_and_output_creation(self):
        rows, proofs, lineage, _ = inputs(); emit = Mock(side_effect=AssertionError('must not generate'))
        with tempfile.TemporaryDirectory(prefix='chat_probe_proofs_') as folder:
            root = Path(folder); output = root / 'batch'
            with self.assertRaises(ValueError): b.collect_batch(output, rows, proofs[:-1], lineage, emit, 8, root)
            emit.assert_not_called(); self.assertFalse(output.exists())

    def test_human_review_path_is_new_markdown_inside_review_request_and_fences_preserve_text(self):
        rows, proofs, lineage, emit = inputs(); events = [b.event_for(r, p, *emit(r['question']), .1, 8) for r, p in zip(rows, proofs)]
        events[1]['answer'] = '```\nraw <html> and ` tokens\n```'
        text = b.human_markdown(events, lineage)
        self.assertIn(events[1]['answer'], text); self.assertIn('``````text', text)
        with tempfile.TemporaryDirectory(prefix='chat_probe_review_paths_') as folder:
            root = Path(folder)
            for path in (root / 'elsewhere.md', root / 'review_request/file.txt', root / 'datasets/TinyDataset/x.md'):
                with self.assertRaises(ValueError): b.review_path(path, root)

    def test_execute_reuses_ui_emit_once_per_question_with_no_history_and_no_gold_input(self):
        from scripts import p106b_gate_runtime as runtime
        with tempfile.TemporaryDirectory(prefix='chat_probe_execute_fixture_') as folder:
            root = Path(folder); source = root / 'questions.jsonl'
            source.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in questions()), encoding='utf-8')
            args = NS(model='native595-f', data=str(source), output=str(root / 'batch'),
                      review_output=str(root / 'review_request/out.md'), max_wall_sec=60, max_new=8)
            rows, proofs, _, fake_emit = inputs()
            active = dict(name=args.model, tokenizer=Tokenizer(), tokenizer_sha256=b.ui.TOKENIZER_SHA,
                precision='FP32_MATH', checkpoint='SYNTHETIC_NOT_A_WEIGHT_FILE', checkpoint_sha256='A' * 64,
                core_sha256='B' * 64, report_sha256='C' * 64, manifest_sha256='D' * 64, quantization_route={'synthetic': True})
            @contextmanager
            def selected(spec, root): yield active
            def ui_emit(value, question, max_new, history):
                self.assertIs(value, active); self.assertEqual(max_new, 8); self.assertEqual(history, ())
                return fake_emit(question)
            with patch.object(b, 'ROOT', root), patch.object(b, 'CODE', ()), \
                    patch.object(b.ui, 'verify_manifest', return_value={}), patch.object(b.ui, 'local_tokenizer', return_value=Tokenizer()), \
                    patch.object(b.ui, 'selected_runtime', side_effect=selected), patch.object(b.ui, 'emit', side_effect=ui_emit) as calls, \
                    patch.object(runtime, 'wall_limit', return_value=nullcontext()), redirect_stdout(io.StringIO()):
                self.assertEqual(b.execute(args), 0)
            self.assertEqual(calls.call_count, 2)
            self.assertEqual([c.args[1] for c in calls.call_args_list], [r['question'] for r in questions()])

    def test_strict_context_exit_failure_leaves_raw_pending_and_no_review_or_success(self):
        from scripts import p106b_gate_runtime as runtime
        with tempfile.TemporaryDirectory(prefix='chat_probe_exit_fixture_') as folder:
            root = Path(folder); source = root / 'questions.jsonl'
            source.write_text(''.join(json.dumps(r) + '\n' for r in questions()), encoding='utf-8')
            args = NS(model='native595-f', data=str(source), output=str(root / 'batch'),
                      review_output=str(root / 'review_request/out.md'), max_wall_sec=60, max_new=8)
            active = dict(name=args.model, tokenizer=Tokenizer(), tokenizer_sha256=b.ui.TOKENIZER_SHA, precision='FP32_MATH',
                checkpoint='SYNTHETIC', checkpoint_sha256='A' * 64, core_sha256='B' * 64,
                report_sha256='C' * 64, manifest_sha256='D' * 64, quantization_route={})
            @contextmanager
            def fail_on_exit(spec, root):
                yield active
                raise RuntimeError('synthetic core changed at strict exit')
            emit = inputs()[3]
            with patch.object(b, 'ROOT', root), patch.object(b, 'CODE', ()), patch.object(b.ui, 'verify_manifest', return_value={}), \
                    patch.object(b.ui, 'local_tokenizer', return_value=Tokenizer()), patch.object(b.ui, 'selected_runtime', side_effect=fail_on_exit), \
                    patch.object(b.ui, 'emit', side_effect=lambda active, question, **kw: emit(question)), \
                    patch.object(runtime, 'wall_limit', return_value=nullcontext()):
                with self.assertRaises(RuntimeError): b.execute(args)
            self.assertFalse(Path(args.review_output).exists()); self.assertFalse((Path(args.output) / 'report.json').exists())
            self.assertTrue((Path(args.output) / 'answers_shards_manifest.json').exists())
            self.assertEqual(json.loads((Path(args.output) / 'error.json').read_text())['status'], 'INCOMPLETE')


class CliTests(Guarded):
    def test_registered_six_names_are_exact_and_check_only_never_loads_models(self):
        self.assertEqual(set(b.MODELS), {'native595-q', 'native595-f', 'old299-broad-q', 'old299-broad-f', 'new595-broad-q', 'new595-broad-f'})
        with tempfile.TemporaryDirectory(prefix='chat_probe_cli_') as folder:
            root = Path(folder); source = root / 'questions.jsonl'
            source.write_text(''.join(json.dumps(r) + '\n' for r in questions()), encoding='utf-8')
            with patch.object(b, 'ROOT', root), patch.object(b, 'execute', side_effect=AssertionError('no execute')), redirect_stdout(io.StringIO()):
                self.assertEqual(b.main(['--model', 'native595-f', '--data', str(source), '--output', str(root / 'batch'),
                    '--review-output', str(root / 'review_request/out.md'), '--check-only']), 0)
            self.assertFalse((root / 'batch').exists()); self.assertFalse((root / 'review_request').exists())

    def test_invalid_names_missing_action_or_generation_caps_fail_before_file_reads(self):
        common = ['--model', 'native595-f', '--data', 'missing', '--output', 'out', '--review-output', 'review_request/out.md']
        for argv in (common, common + ['--execute', '--check-only'], common + ['--check-only', '--max-new', '0'],
                     common + ['--check-only', '--max-wall-sec', '59'], ['--model', '1']):
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as raised: b.main(argv)
            self.assertEqual(raised.exception.code, 2)

    def test_direct_help_is_noninteractive_and_asset_free(self):
        result = subprocess.run([sys.executable, '-B', '-I', str(ROOT / 'scripts/p106b_chat_probe_batch.py'), '--help'],
            stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('--review-output', result.stdout); self.assertIn('new595-broad-f', result.stdout)


if __name__ == '__main__': unittest.main()
