"""Versioned resume reader seam; frozen V5 generation inputs stay unchanged."""
from contextlib import contextmanager
import json
from pathlib import Path
from unittest.mock import patch

from scripts import diag_p106b_nov05_english_passage as view
from scripts import diag_p106b_supported_production8h as supported

ORIGINAL_BATCHES = supported.batches
AUDIT = view.AUDIT / 'resume_adapter_v1'


def batches(control, destination):
    """Override a version only while advancing the exact V5 reader."""
    if Path(destination) != view.OUTPUT:
        yield from ORIGINAL_BATCHES(control, destination)
        return
    iterator = iter(ORIGINAL_BATCHES(control, destination))
    while True:
        try:
            with patch.object(supported, 'VERSION', view.VIEW):
                item = next(iterator)
        except StopIteration:
            return
        yield item


@contextmanager
def runtime():
    with patch.object(supported, 'batches', batches):
        yield


class BeforeTeacherAssets(Exception):
    pass


def prepare():
    """Execute the real resume prefix, stop before assets/server/new batch."""
    from scripts import diag_p106b_nov05_english_production as base
    original_files = base.ready_files()
    reached = []

    def stop(*args, **kwargs):
        reached.append(True)
        raise BeforeTeacherAssets('real resume prefix reached the asset gate')

    with runtime(), view.variant(), view.scope(view.OUTPUT) as (producer, info):
        if info != json.loads((view.OUTPUT / 'inputs.json').read_text(encoding='utf-8')):
            raise ValueError('frozen V5 generation inputs changed')
        base.require_pilot(info)
        with patch.object(producer.teacher, 'assets', stop):
            try:
                producer.production(resume=True, max_wall_sec=600)
            except BeforeTeacherAssets:
                pass
            else:
                raise RuntimeError('resume did not reach the expected preteacher boundary')
    if reached != [True] or base.check_parent()['original_files'] != original_files:
        raise ValueError('resume prefix closure or parent identity failed')
    value = dict(schema='P106B_V5_RESUME_READER_SEAM_V1',
        status='ACTUAL_RESUME_PREFIX_VERIFIED_BEFORE_TEACHER',
        source_sha256=base.sha(Path(__file__)),
        view_source_sha256=base.sha(Path(view.__file__)),
        generation_inputs_sha256=base.sha(view.OUTPUT / 'inputs.json'),
        pilot_report_sha256=base.sha(view.OUTPUT / 'batch_000000/report.json'),
        root_review_sha256=base.sha(view.AUDIT / 'ROOT_PILOT_REVIEW_v1.json'),
        prepared_sha256=base.sha(view.AUDIT / 'PREPARE_v1.json'),
        old_original_files_unchanged=True,
        teacher_started=False, gpu_query=False, new_batch_created=False,
        change='Only latest-batch enumeration accepts the already declared V5 article contract. No prompt, source, sampler, quota or generation-contract changes.')
    base.write(AUDIT / 'PREPARE_v1.json', value)
    print('[RESUME_PREFIX] ' + json.dumps(value), flush=True)


def main():
    import sys
    if sys.argv[1:] == ['prepare-resume']:
        prepare()
        return 0
    with runtime():
        return view.main()


if __name__ == '__main__':
    raise SystemExit(main())
