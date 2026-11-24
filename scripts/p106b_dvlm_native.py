"""Native HPA hidden-state oracle; Torch is imported only by explicit callers."""
from __future__ import annotations

from scripts.p106b_dvlm_pts import AlignmentGroup, PTSLayout, AdmissionHold


def restore_layout(value):
    fields = dict(value)
    fields['groups'] = tuple(AlignmentGroup(tuple(g['student']), tuple(g['teacher']),
        g['byte_start'], g['byte_end']) for g in fields['groups'])
    for name in ('input_ids', 'position_ids', 'student_groups', 'teacher_groups',
                 'expansion_owner', 'expansion_offset', 'head_indices', 'student_ids'):
        fields[name] = tuple(fields[name])
    result = PTSLayout(**fields)
    validate_layout(result)
    return result


def validate_layout(layout):
    n, t = len(layout.input_ids), layout.teacher_count
    s = len(layout.student_ids)
    if (type(t) is not int or not 0 < t < n or not s
            or len(layout.position_ids) != n or len(layout.teacher_groups) != t
            or len(layout.student_groups) != s or len(layout.head_indices) != s
            or len(layout.expansion_owner) != n-t or len(layout.expansion_offset) != n-t
            or any(type(i) is not int or i < 0 for i in (*layout.input_ids, *layout.position_ids, *layout.student_ids))):
        raise AdmissionHold('native PTS dimensions/IDs differ')
    if (tuple(i for g in layout.groups for i in g.teacher) != tuple(range(t))
            or tuple(i for g in layout.groups for i in g.student) != tuple(range(s))):
        raise AdmissionHold('native PTS complete ordered group coverage differs')
    expected_s = tuple(j for j, group in enumerate(layout.groups) for _ in group.student)
    expected_t = tuple(j for j, group in enumerate(layout.groups) for _ in group.teacher)
    if layout.student_groups != expected_s or layout.teacher_groups != expected_t:
        raise AdmissionHold('native PTS group ownership differs')
    if layout.position_ids[:t] != tuple(range(t)):
        raise AdmissionHold('native teacher positions differ')
    if any(type(owner) is not int or not 0 <= owner < s for owner in layout.expansion_owner):
        raise AdmissionHold('native private owners outside original students')
    consumed = 0
    for student in range(s):
        offsets = [i for i, owner in enumerate(layout.expansion_owner) if owner == student]
        if not offsets or offsets != list(range(consumed, consumed + len(offsets))):
            raise AdmissionHold('native private expansion coverage differs')
        if (tuple(layout.expansion_offset[i] for i in offsets) != tuple(range(len(offsets)))
                or layout.head_indices[student] != t+offsets[-1]):
            raise AdmissionHold('native expansion offsets/head locations differ')
        consumed += len(offsets)
    if consumed != n-t:
        raise AdmissionHold('native private owners outside original students')
    for index in range(len(layout.groups)):
        branch = layout.branch_indices(index)
        if tuple(layout.position_ids[i] for i in branch) != tuple(range(len(branch))):
            raise AdmissionHold('native serial branch logical positions differ')
    return layout


def compare_hidden(torch, left, right, *, atol, rtol):
    if left.shape != right.shape or left.ndim != 2 or left.numel() == 0:
        raise ValueError('complete matching nonempty hidden matrices required')
    finite = bool(torch.isfinite(left).all() and torch.isfinite(right).all())
    difference = (left-right).abs()
    close = torch.isclose(left, right, atol=atol, rtol=rtol)
    return dict(rows=left.shape[0], hidden_size=left.shape[1], finite=finite,
        atol=atol, rtol=rtol, passed=finite and bool(close.all()),
        violations=int((~close).sum().item()), max_abs=float(difference.max().item()) if finite else None,
        max_scaled=float((difference/(atol+rtol*right.abs())).max().item()) if finite else None)


def pts_hidden(torch, model, layout, *, ids=None):
    validate_layout(layout)
    device = next(model.parameters()).device
    token_ids = layout.input_ids if ids is None else tuple(ids)
    if len(token_ids) != len(layout.input_ids):
        raise ValueError('counterfactual keeps complete PTS length')
    inputs = torch.tensor([token_ids], dtype=torch.long, device=device)
    positions = torch.tensor([layout.position_ids], dtype=torch.long, device=device)
    visible = torch.tensor(layout.dense_visibility(max_length=1024), dtype=torch.bool, device=device)
    mask = torch.zeros(visible.shape, dtype=torch.float32, device=device)
    mask.masked_fill_(~visible, torch.finfo(torch.float32).min)
    output = model.model(input_ids=inputs, attention_mask=mask[None,None],
        position_ids=positions, use_cache=False)
    if output.past_key_values is not None:
        raise ValueError('native HPA must not create a KV cache')
    return output.last_hidden_state[0]


def native_case(torch, model, layout, *, atol, rtol, guard=lambda: None):
    """Full PTS versus independent native teacher/group-serial causal forwards."""
    layout = validate_layout(layout)
    guard()
    device = next(model.parameters()).device
    whole = pts_hidden(torch, model, layout)
    teacher_ids = torch.tensor([layout.input_ids[:layout.teacher_count]], dtype=torch.long, device=device)
    native = model.model(input_ids=teacher_ids, use_cache=False).last_hidden_state[0]
    teacher = compare_hidden(torch, whole[:layout.teacher_count], native, atol=atol, rtol=rtol)
    groups = []
    all_serial = torch.empty_like(whole[layout.teacher_count:])
    for index in range(len(layout.groups)):
        guard()
        branch = layout.branch_indices(index)
        ids = torch.tensor([[layout.input_ids[i] for i in branch]], dtype=torch.long, device=device)
        serial = model.model(input_ids=ids, use_cache=False).last_hidden_state[0]
        prefix = layout.groups[index].teacher[0]
        private = tuple(i for i in branch if i >= layout.teacher_count)
        actual = whole[list(private)]
        expected = serial[prefix:]
        comparison = compare_hidden(torch, actual, expected, atol=atol, rtol=rtol)
        for physical, vector in zip(private, expected):
            all_serial[physical-layout.teacher_count] = vector
        groups.append(dict(group=index, prefix_tokens=prefix, private_tokens=len(private), comparison=comparison))
    guard()
    # Perturb every token which the first private query cannot causally observe.
    query = layout.teacher_count
    changed = tuple(i for i in range(len(layout.input_ids)) if not layout.visible(query, i))
    replacement = tuple((token+1) % model.config.vocab_size if i in changed else token
                        for i, token in enumerate(layout.input_ids))
    altered = pts_hidden(torch, model, layout, ids=replacement)
    first_private = compare_hidden(torch, whole[query:query+1], altered[query:query+1], atol=atol, rtol=rtol)
    # Original native teacher rows cannot depend on any private student expansion.
    changed_private = tuple(i for i in range(layout.teacher_count, len(layout.input_ids)))
    replacement = tuple((token+1) % model.config.vocab_size if i in changed_private else token
                        for i, token in enumerate(layout.input_ids))
    altered_private = pts_hidden(torch, model, layout, ids=replacement)
    native_invariant = compare_hidden(torch, whole[:layout.teacher_count],
        altered_private[:layout.teacher_count], atol=atol, rtol=rtol)
    response = None
    for group in layout.groups:
        if len(group.student) >= 2:
            preceding, later = group.student[0], group.student[-1]
            changed_row = layout.teacher_count + layout.expansion_owner.index(preceding)
            query = layout.head_indices[later]
            ids = list(layout.input_ids); ids[changed_row] = (ids[changed_row]+1) % model.config.vocab_size
            changed_hidden = pts_hidden(torch, model, layout, ids=ids)
            response = dict(group=layout.student_groups[later], changed_row=changed_row, observed_query=query,
                max_abs=float((whole[query]-changed_hidden[query]).abs().max().item()),
                policy='OBSERVATION_ONLY;NO_REQUIRED_POSITIVE_RESPONSE_OR_QUALITY_CLAIM')
            break
    report = dict(teacher=teacher, groups=groups,
        first_private_blocked_future_invariance=dict(changed_tokens=len(changed), comparison=first_private),
        native_private_invariance=native_invariant, same_group_response=response,
        passed=teacher['passed'] and all(item['comparison']['passed'] for item in groups)
            and first_private['passed'] and native_invariant['passed'],
        position_reference='SERIAL_DEFAULT_CAUSAL_POSITIONS;PTS_EXPLICIT_LOGICAL_POSITIONS',
        original_head_calls=0, training=False, quality_claim=False)
    return report, dict(pts_native=whole[:layout.teacher_count].detach().cpu(),
        serial_native=native.detach().cpu(), pts_private=whole[layout.teacher_count:].detach().cpu(),
        serial_private=all_serial.detach().cpu(), head_indices=layout.head_indices)
