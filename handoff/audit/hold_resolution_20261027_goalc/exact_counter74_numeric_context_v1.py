"""Close only the two previously read source-bound numeric flags for ID74."""
import hashlib

from numeric_atom_integrity_v1 import ATOM

EXPECTED_ID = 'expanded_train:74'
SOURCE_SHA = '36FE55933DE0D02263CE3AA5DA39DFBD10342AE88A373E6B30E4B79555C69427'
BODY_SHA = 'B9A9D58BB57EE3284B33E376FF2C9BA0330C267FD7E4B67266BBF0DA6C1E7D90'


def verify_exact_context(item, key, source_pin, body_pin, review, original, body, flags):
    assert key == item['id'] == EXPECTED_ID
    assert source_pin == item['original'] and body_pin == item['body']
    assert source_pin['sha256'] == SOURCE_SHA
    assert body_pin['sha256'] == BODY_SHA
    assert hashlib.sha256(original.encode('utf-8')).hexdigest().upper() == SOURCE_SHA
    assert hashlib.sha256(body.encode('utf-8')).hexdigest().upper() == BODY_SHA
    assert review == item['review']
    for field in ['root_full_original_body_and_diff_read',
                  'positive_integer_two_integer_square_sum_and_order_conditions_preserved',
                  'missing_power_Legendre_and_divisor_parameters_stay_HOLD',
                  'missing_four_explicit_representations_not_generated']:
        assert item[field] is True
    assert item['numeric_flags'] == flags
    assert len(flags) == len(item['closed_flags']) == 2
    assert [r['flag'] for r in item['closed_flags']] == flags
    source_atoms = {(a.start(), a.end()): a.group() for a in ATOM.finditer(original)}
    body_atoms = {(a.start(), a.end()): a.group() for a in ATOM.finditer(body)}
    source_anchor, body_anchor = item['source_anchor'], item['body_anchor']
    assert original.count(source_anchor) == body.count(body_anchor) == 1
    source_start, body_start = original.index(source_anchor), body.index(body_anchor)
    expected = [([1276, 1277], [369, 370], '1'), ([1300, 1301], [386, 387], '4')]
    for closed, (source_span, body_span, token) in zip(item['closed_flags'], expected):
        flag = closed['flag']
        assert closed['source_span'] == source_span and flag['body_span'] == body_span
        assert flag['body_token'] == token
        assert source_atoms[tuple(source_span)] == body_atoms[tuple(body_span)] == token
        assert source_start <= source_span[0] < source_span[1] <= source_start + len(source_anchor)
        assert body_start <= body_span[0] < body_span[1] <= body_start + len(body_anchor)
        assert closed['outcome'] == 'EXACT_SOURCE_RESULT_IN_SAME_ORDERED_TWO_SQUARE_CONTEXT'
    return True
