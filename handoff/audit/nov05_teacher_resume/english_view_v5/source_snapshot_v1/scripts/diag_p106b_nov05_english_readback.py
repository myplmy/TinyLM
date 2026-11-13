"""Verify a closed English-only batch and write a human-readable source/QA view."""
import json
from pathlib import Path
import sys

from scripts import diag_p106b_nov05_english_production as fork
from scripts.diag_p106b_nov05_supported_ready import sha
from scripts.p106b_shards import verify
from scripts.p108_readback import write_small


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ('pilot', 'window'):
        raise SystemExit('pilot or window required')
    mode = sys.argv[1]
    prepared = json.loads((fork.AUDIT / 'PREPARE_v1.json').read_text(encoding='utf-8'))
    if sha(Path(fork.__file__)) != prepared['source_code_sha256']:
        raise ValueError('prepared English fork source changed')
    fork.check_parent()
    with fork.scope(fork.OUTPUT) as (producer, info):
        if info != prepared['input']:
            raise ValueError('fork input differs')
        if mode == 'pilot':
            fork.ORIGINAL_REQUIRE(info, destination=fork.OUTPUT)
        base = producer.control.base_report()
        from tokenizers import Tokenizer
        tokenizer = Tokenizer.from_file(str(producer.TOKENIZER))
        state, cursor, count = producer.state_from_saved(tokenizer, base)
        if not count:
            raise ValueError('no published English batch')
        directory = fork.OUTPUT / ('batch_' + str(count - 1).zfill(6))
        report = json.loads((directory / 'report.json').read_text(encoding='utf-8'))
        rows = list(producer.control.rows(directory, report['candidate_manifest']))
        if len(rows) != report['accepted_groups']:
            raise ValueError('published candidate count differs')
        for key in ('raw_manifest', 'candidate_manifest'):
            verify(directory, report[key])
        if report['input'] != info or tuple(report['cursor']) != cursor:
            raise ValueError('batch input/cursor differs')
        current = state.report()
        before = prepared['quotas']
        if current['nonpadding_tokens']['train:ko'] != before['nonpadding_tokens']['train:ko']:
            raise ValueError('English-only fork changed Korean input quantity')
        windows = sorted((fork.AUDIT / 'windows').glob('window_*.json'))
        window = json.loads(windows[-1].read_text(encoding='utf-8'))
        if not window['owned_teacher_closed'] or not window['parent_files_unchanged']:
            raise ValueError('owned server closure or parent integrity incomplete')
        summary = dict(schema='P106B_ENGLISH_CLOSED_READBACK_V1', mode=mode,
            report_sha256=sha(directory / 'report.json'), closed_batches=count,
            cursor=list(cursor), last_batch_candidates=len(rows), returncode=report['returncode'],
            status=report['status'], quantities=current, source_code_sha256=prepared['source_code_sha256'],
            parent_files_unchanged=True, owned_teacher_closed=True,
            semantic_quality='ROOT_READING_REQUIRED_NOT_AUTOMATIC', formal_train_ready=False,
            model_loading=False)
        label = 'batch_' + str(count - 1).zfill(6)
        fork.write(fork.AUDIT / (label + '_READBACK_v1.json'), summary)
        text = ['# Closed English candidates: complete learner input and answer', '',
                'This is candidate review, not an official benchmark or student result.', '']
        # Preserve all first pilot cases; later windows expose a fixed even sample.
        chosen = list(range(len(rows))) if mode == 'pilot' else sorted({
            round(i * (len(rows) - 1) / 23) for i in range(min(24, len(rows)))})
        for index in chosen:
            row = rows[index]
            text.extend(['## Candidate ' + str(index), '',
                'Source: ' + row['meta']['source_id'], ''])
            for message in row['messages']:
                content = message['content']
                if isinstance(content, list):
                    content = ''.join(part.get('text', '') for part in content)
                text.extend([message['role'] + ':', '', *['    ' + line for line in content.splitlines()], ''])
        write_small(fork.AUDIT / (label + '_PAIRS_v1.md'), chr(10).join(text) + chr(10))
        print('[ENGLISH_CLOSED] ' + json.dumps({k: summary[k] for k in
              ('mode', 'closed_batches', 'cursor', 'last_batch_candidates', 'status', 'returncode',
               'parent_files_unchanged', 'owned_teacher_closed')}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
