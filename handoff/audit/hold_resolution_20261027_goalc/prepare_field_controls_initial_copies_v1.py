"""Reuse the verified unchanged-body bootstrap for the controls field queue."""
from pathlib import Path
import ast
import contextlib
import hashlib
import json

ROOT = Path(__file__).resolve().parents[3]
AUDIT = Path(__file__).resolve().parent
BASE = ROOT / 'data_cache/p106b_hold_resolution_v1_20261027_goalc'
frozen = AUDIT / 'prepare_birth_controls_initial_copies_v1.py'
template = frozen.read_text(encoding='utf-8')
rows = []
log_path = AUDIT / 'FIELD_CONTROLS_INITIAL_COPIES_BUILD_V1.log'
with log_path.open('x', encoding='utf-8') as log:
    for page in range(1, 37):
        cohort = f'remaining_field_title_page_{page:03}_counter_v1'
        manifest = json.loads((BASE / cohort / 'manifest.json').read_bytes())
        expected = sum(row['role'] == 'context_controls' for row in manifest['rows'])
        assert 0 < expected < 520
        receipt_name = f'FIELD_CONTROLS_PAGE_{page:03}_INITIAL_COPIES_VERIFIED_V1.json'
        tree = ast.parse(template)
        parent_checks = 0
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare) and ast.unparse(node.left) == 'source.parent':
                assert len(node.comparators) == 1
                node.comparators[0] = ast.parse(repr(str(BASE / 'remaining_field_title_native_proofs_v1/pages' / f'page_{page:03}' / 'inputs')), mode='eval').body
                node.comparators[0] = ast.Call(func=ast.Name(id='Path', ctx=ast.Load()), args=[node.comparators[0]], keywords=[])
                parent_checks += 1
        assert parent_checks == 1
        mapping = {'birth_root11_independent_v1': cohort,
                   'BIRTH_CONTROLS_INITIAL_COPIES_VERIFIED_V1.json': receipt_name,
                   '고정reader문서의 한 줄은 Python 실행파일을 이미 포함하는 완결명령이다. cmd앞에 Python을 다시 붙이지 않는다.':
                   '고정field짧은호출은 bash로 시작하는 완결명령이며 별도Python을 붙이지 않는다. 인수는 PAGE ID PACKET [PIECE]다.'}

        class BindPage(ast.NodeTransformer):
            def visit_Constant(self, node):
                if type(node.value) is int and node.value == 1354:
                    return ast.copy_location(ast.Constant(expected), node)
                if isinstance(node.value, str):
                    value = mapping.get(node.value, node.value).replace('1354', str(expected))
                    return ast.copy_location(ast.Constant(value), node)
                return node

        tree = BindPage().visit(tree)
        ast.fix_missing_locations(tree)
        with contextlib.redirect_stdout(log):
            exec(compile(tree, str(frozen), 'exec'), {'__file__': __file__, '__name__': 'fixed_field_initial_copies'})
        receipt_path = AUDIT / receipt_name
        data = receipt_path.read_bytes()
        value = json.loads(data)
        assert value['sources'] == len(value['rows']) == expected
        rows.append(dict(page=page, sources=expected, guide=value['guide'],
                         receipt=dict(path=str(receipt_path.relative_to(ROOT)), sha256=hashlib.sha256(data).hexdigest().upper())))
        log.flush()
assert len(rows) == 36 and sum(row['sources'] for row in rows) == 3248
result = dict(status='EXACT_UNCHANGED_CONTROLS_FIELD_INITIAL_COPIES_VERIFIED_NOT_REVISIONS',
              pages=rows, sources=3248, root_authored_cleaned_bodies=0, new_reviews=0,
              original_or_candidate_changed=False, protected_body_reads=0,
              input_pins=[dict(path=str(path.relative_to(ROOT)), sha256=hashlib.sha256(path.read_bytes()).hexdigest().upper())
                          for path in (frozen, Path(__file__).resolve(), log_path)],
              cache_admitted=0, goal_complete=False)
with (AUDIT / 'FIELD_CONTROLS_INITIAL_COPIES_COMPLETE_V1.json').open('x', encoding='utf-8') as stream:
    json.dump(result, stream, ensure_ascii=False, indent=2)
    stream.write(chr(10))
print(json.dumps(dict(status=result['status'], pages=36, unchanged_initial_copies=3248,
                     new_cleaned_bodies=0, admitted=0), ensure_ascii=False))
