"""Lossless PTS layout and explicit HPA visibility; no model import or training."""
from __future__ import annotations

from dataclasses import dataclass
from itertools import accumulate
from typing import Callable, Sequence


class AdmissionHold(ValueError):
    """A complete sample is unadmitted; its original supervision is preserved."""


def _ids(values, label):
    values = tuple(values)
    if not values or any(type(i) is not int or i < 0 for i in values):
        raise AdmissionHold(label + ': nonempty nonnegative native IDs required')
    return values


def canonical_pieces(ids: Sequence[int], decode: Callable[[Sequence[int]], str]):
    ids = _ids(ids, 'canonical')
    previous = ''
    pieces = []
    for end in range(1, len(ids) + 1):
        current = decode(ids[:end])
        if not isinstance(current, str) or not current.startswith(previous):
            raise AdmissionHold('NON_APPEND_PREFIX_DECODER')
        piece = current[len(previous):].encode('utf-8', errors='strict')
        if not piece:
            raise AdmissionHold('EMPTY_CANONICAL_PIECE')
        pieces.append(piece)
        previous = current
    return tuple(pieces)


def expand_piece(piece: bytes, encode_teacher, decode_teacher):
    if not isinstance(piece, bytes) or not piece:
        raise AdmissionHold('NONEMPTY_RAW_BYTES_REQUIRED')
    try:
        text = piece.decode('utf-8', errors='strict')
    except UnicodeError as error:
        raise AdmissionHold('STUDENT_TOKEN_NOT_INDEPENDENT_UTF8') from error
    ids = _ids(encode_teacher(text), 'teacher expansion')
    if decode_teacher(ids) != text:
        raise AdmissionHold('TEACHER_RETOKENIZATION_CHANGED_TEXT')
    return ids


@dataclass(frozen=True)
class AlignmentGroup:
    student: tuple[int, ...]
    teacher: tuple[int, ...]
    byte_start: int
    byte_end: int


def align_piece_groups(student_pieces, teacher_pieces):
    student, teacher = tuple(student_pieces), tuple(teacher_pieces)
    if (not student or not teacher
            or any(not isinstance(p, bytes) or not p for p in (*student, *teacher))):
        raise AdmissionHold('NONEMPTY_LOSSLESS_CANONICAL_PIECES_REQUIRED')
    if b''.join(student) != b''.join(teacher):
        raise AdmissionHold('FULL_TEXT_OR_RESIDUAL_MISMATCH')
    se, te = tuple(accumulate(map(len, student))), tuple(accumulate(map(len, teacher)))
    si = ti = start_s = start_t = byte_start = 0
    groups = []
    while si < len(student) and ti < len(teacher):
        if se[si] < te[ti]:
            si += 1
        elif te[ti] < se[si]:
            ti += 1
        else:
            groups.append(AlignmentGroup(tuple(range(start_s, si + 1)), tuple(range(start_t, ti + 1)), byte_start, se[si]))
            byte_start = se[si]
            si += 1; ti += 1; start_s = si; start_t = ti
    if start_s != len(student) or start_t != len(teacher):
        raise AdmissionHold('UNCLOSED_ALIGNMENT_RESIDUAL')
    return tuple(groups)


@dataclass(frozen=True)
class PTSLayout:
    input_ids: tuple[int, ...]
    position_ids: tuple[int, ...]
    teacher_count: int
    groups: tuple[AlignmentGroup, ...]
    student_groups: tuple[int, ...]
    teacher_groups: tuple[int, ...]
    expansion_owner: tuple[int, ...]
    expansion_offset: tuple[int, ...]
    head_indices: tuple[int, ...]
    student_ids: tuple[int, ...]

    def visible(self, query, key):
        n = len(self.input_ids)
        if type(query) is not int or type(key) is not int or not 0 <= query < n or not 0 <= key < n:
            raise ValueError('physical query/key outside explicit PTS')
        if query < self.teacher_count:
            return key < self.teacher_count and key <= query
        q = query - self.teacher_count
        student = self.expansion_owner[q]
        group = self.student_groups[student]
        if key < self.teacher_count:
            return self.teacher_groups[key] < group
        k = key - self.teacher_count
        previous = self.expansion_owner[k]
        return (self.student_groups[previous] == group
                and (previous < student or (previous == student and self.expansion_offset[k] <= self.expansion_offset[q])))

    def dense_visibility(self, *, max_length=4096):
        if type(max_length) is not int or max_length < 1 or len(self.input_ids) > max_length:
            raise AdmissionHold('PTS_VISIBILITY_LENGTH_CAP')
        return tuple(tuple(self.visible(q, k) for k in range(len(self.input_ids))) for q in range(len(self.input_ids)))

    def branch_indices(self, group):
        if type(group) is not int or not 0 <= group < len(self.groups):
            raise ValueError('alignment group outside layout')
        prefix = tuple(range(self.groups[group].teacher[0]))
        private = tuple(self.teacher_count + i for i, owner in enumerate(self.expansion_owner) if self.student_groups[owner] == group)
        return prefix + private

    def head_targets(self, supervised, *, ignore_index=-100):
        supervised = tuple(supervised)
        if len(supervised) != len(self.student_ids) or any(type(b) is not bool for b in supervised):
            raise AdmissionHold('EXPLICIT_ORIGINAL_STUDENT_TARGET_MASK_REQUIRED')
        return tuple(self.student_ids[i + 1] if i + 1 < len(self.student_ids) and supervised[i + 1] else ignore_index
                     for i in range(len(self.student_ids)))


def build_layout(student_ids, teacher_ids, student_pieces, teacher_pieces, expansions, *, max_length=4096):
    """Lay out previously verified native pieces and expansions; no tokenizer I/O."""
    student_ids, teacher_ids = _ids(student_ids, 'student'), _ids(teacher_ids, 'teacher')
    student_pieces, teacher_pieces = tuple(student_pieces), tuple(teacher_pieces)
    if len(student_ids) != len(student_pieces) or len(teacher_ids) != len(teacher_pieces):
        raise AdmissionHold('EVERY_NATIVE_TOKEN_REQUIRES_ITS_CANONICAL_PIECE')
    expansions = tuple(_ids(e, 'individual expansion') for e in expansions)
    if len(expansions) != len(student_ids):
        raise AdmissionHold('EVERY_STUDENT_TOKEN_REQUIRES_AN_EXPANSION')
    if (type(max_length) is not int or max_length < 1
            or len(teacher_ids) + sum(map(len, expansions)) > max_length):
        raise AdmissionHold('PTS_COMPLETE_SEQUENCE_OVER_LENGTH')
    groups = align_piece_groups(student_pieces, teacher_pieces)
    sg, tg = [-1] * len(student_ids), [-1] * len(teacher_ids)
    for index, group in enumerate(groups):
        for i in group.student:
            sg[i] = index
        for i in group.teacher:
            tg[i] = index
    ids = list(teacher_ids)
    positions = list(range(len(teacher_ids)))
    owners, offsets, heads = [], [], []
    used_in_group = [0] * len(groups)
    for index, expansion in enumerate(expansions):
        group = sg[index]
        logical_start = groups[group].teacher[0] + used_in_group[group]
        ids.extend(expansion)
        positions.extend(range(logical_start, logical_start + len(expansion)))
        owners.extend([index] * len(expansion))
        offsets.extend(range(len(expansion)))
        heads.append(len(ids) - 1)
        used_in_group[group] += len(expansion)
    return PTSLayout(tuple(ids), tuple(positions), len(teacher_ids), groups, tuple(sg), tuple(tg), tuple(owners), tuple(offsets), tuple(heads), student_ids)


def prepare_layout(student_ids, teacher_ids, student_pieces, teacher_pieces, *,
                   decode_student, encode_teacher, decode_teacher, max_length=4096):
    """Tokenizer admission before layout: exact raw bytes and independent tokens."""
    student_ids, teacher_ids = _ids(student_ids, 'student'), _ids(teacher_ids, 'teacher')
    student_pieces, teacher_pieces = tuple(student_pieces), tuple(teacher_pieces)
    if len(student_ids) != len(student_pieces) or len(teacher_ids) != len(teacher_pieces):
        raise AdmissionHold('TOKEN_AND_RAW_PIECE_COUNTS_DIFFER')
    try:
        student_text = b''.join(student_pieces).decode('utf-8', errors='strict')
        teacher_text = b''.join(teacher_pieces).decode('utf-8', errors='strict')
    except (UnicodeError, TypeError) as error:
        raise AdmissionHold('COMPLETE_SEQUENCE_NOT_UTF8_BYTES') from error
    if (student_text != teacher_text or decode_student(student_ids) != student_text
            or decode_teacher(teacher_ids) != teacher_text):
        raise AdmissionHold('NATIVE_FULL_DECODE_OR_TEXT_DIFFERS')
    expansions = []
    for token_id, piece in zip(student_ids, student_pieces):
        expansion = expand_piece(piece, encode_teacher, decode_teacher)
        if decode_student([token_id]) != piece.decode('utf-8', errors='strict'):
            raise AdmissionHold('STANDALONE_STUDENT_DECODE_DIFFERS_FROM_RAW_PIECE')
        expansions.append(expansion)
    return build_layout(student_ids, teacher_ids, student_pieces, teacher_pieces, expansions, max_length=max_length)
