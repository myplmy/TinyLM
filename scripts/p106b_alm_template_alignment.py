"""답 본문만의 opt-in byte 정렬. 전체 template 일치나 확률 정합을 뜻하지 않는다.

모든 span은 각 원본 전체 UTF-8 입력의 반열린 byte 구간이다. 각 full stream은
기존 validate_stream으로 독립 검산한다. 같은 본문 안에서도 native token을 부분
절단하거나 재토큰화하지 않는다. byte_start/end는 답 내부 상대 좌표이며 별도
student/teacher_byte_start/end는 각 원본 전체 입력의 절대 좌표다.

순수 표준 라이브러리와 기존 불변 byte 계약만 사용한다. I/O, tokenizer, 모델,
교사 요청, 정규화, native ID 변경, loss/품질 판정은 없다.
"""
from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass

from scripts.p106b_alm_bytes import (
    AlignedChunk,
    AlignmentResult,
    ByteAlignmentError,
    ByteStream,
    RejectedChunk,
    TokenByteSpan,
    raw_to_shifted,
    validate_stream,
)


@dataclass(frozen=True)
class AnswerAlignedChunk(AlignedChunk):
    """기존 native raw/shift map과 양쪽 전체 입력 절대 구간."""

    student_byte_start: int
    student_byte_end: int
    teacher_byte_start: int
    teacher_byte_end: int


@dataclass(frozen=True)
class AnswerRejectedChunk(RejectedChunk):
    """미포함 이유. 경계의 zero-byte special은 길이0 기록으로 남긴다."""

    student_byte_start: int
    student_byte_end: int
    teacher_byte_start: int
    teacher_byte_end: int


@dataclass(frozen=True)
class AnswerAlignmentResult:
    chunks: tuple[AnswerAlignedChunk, ...]
    rejected: tuple[AnswerRejectedChunk, ...]
    student_span: tuple[int, int]
    teacher_span: tuple[int, int]
    student_input_byte_count: int
    teacher_input_byte_count: int
    answer_byte_count: int
    covered_byte_count: int
    uncovered_byte_count: int
    boundary_uncovered_byte_count: int
    student_uncovered_ranges: tuple[tuple[int, int], ...]
    teacher_uncovered_ranges: tuple[tuple[int, int], ...]
    student_boundary_crossing_indices: tuple[int, ...]
    teacher_boundary_crossing_indices: tuple[int, ...]
    student_special_indices: tuple[int, ...]
    teacher_special_indices: tuple[int, ...]
    student_supervised_byte_count: int
    teacher_supervised_byte_count: int
    common_answer_boundaries: tuple[int, ...]
    alignment_scope: str = "ANSWER_CONTENT_BYTES_ONLY"

    @property
    def alignment(self) -> AlignmentResult:
        """기존 소비자가 쓰는 본문 상대 AlignmentResult. metadata와 함께 기록."""
        return AlignmentResult(
            self.chunks, self.rejected,
            self.student_special_indices, self.teacher_special_indices,
            self.answer_byte_count, self.covered_byte_count,
            self.student_supervised_byte_count, self.teacher_supervised_byte_count,
        )

    @property
    def metadata(self) -> dict:
        """bytes 없이 JSON 가능한 새 사전. 전체 template 일치 주장은 항상 OFF."""
        def ranges(item):
            return dict(byte_start=item.byte_start, byte_end=item.byte_end,
                        student_span=[item.student_byte_start, item.student_byte_end],
                        teacher_span=[item.teacher_byte_start, item.teacher_byte_end])
        return dict(
            alignment_scope=self.alignment_scope, full_template_equality_claim=False,
            coordinate_system="ANSWER_RELATIVE_BYTE_OFFSETS",
            student_span=list(self.student_span), teacher_span=list(self.teacher_span),
            student_input_byte_count=self.student_input_byte_count,
            teacher_input_byte_count=self.teacher_input_byte_count,
            answer_byte_count=self.answer_byte_count, covered_byte_count=self.covered_byte_count,
            uncovered_byte_count=self.uncovered_byte_count,
            boundary_uncovered_byte_count=self.boundary_uncovered_byte_count,
            student_uncovered_ranges=[list(value) for value in self.student_uncovered_ranges],
            teacher_uncovered_ranges=[list(value) for value in self.teacher_uncovered_ranges],
            student_boundary_crossing_indices=list(self.student_boundary_crossing_indices),
            teacher_boundary_crossing_indices=list(self.teacher_boundary_crossing_indices),
            student_special_indices=list(self.student_special_indices),
            teacher_special_indices=list(self.teacher_special_indices),
            student_supervised_byte_count=self.student_supervised_byte_count,
            teacher_supervised_byte_count=self.teacher_supervised_byte_count,
            common_answer_boundaries=list(self.common_answer_boundaries),
            accepted_ranges=[ranges(item) for item in self.chunks],
            rejected_ranges=[dict(ranges(item), reasons=list(item.reasons),
                                  student_raw_indices=list(item.student_raw_indices),
                                  teacher_raw_indices=list(item.teacher_raw_indices))
                             for item in self.rejected],
        )


def _span(value, stream: ByteStream, name: str) -> tuple[int, int]:
    if (not isinstance(value, (tuple, list)) or len(value) != 2
            or any(type(index) is not int for index in value)):
        raise ByteAlignmentError(name + " span must contain two integer byte offsets")
    start, end = value
    if not 0 <= start < end <= len(stream.text_utf8):
        raise ByteAlignmentError(name + " answer span must be nonempty and within full input")
    return start, end


def _boundaries(stream: ByteStream, span: tuple[int, int]) -> set[int]:
    start, end = span
    return {point - start for token in stream.tokens
            for point in (token.byte_start, token.byte_end) if start <= point <= end}


def _groups(
    stream: ByteStream, span: tuple[int, int], boundaries: tuple[int, ...]
) -> tuple[tuple[TokenByteSpan, ...], ...]:
    """원 token을 그대로 참조한다. 경계 교차 token은 이유 기록용으로만 포함."""
    start, end = span
    groups: list[list[TokenByteSpan]] = [[] for _ in range(len(boundaries) - 1)]
    for token in stream.tokens:
        if not token.data:
            position = token.byte_start - start
            # 양쪽 공통 경계/본문 끝의 special은 이웃 chunk를 오염시키지 않는다.
            # 공통 경계 안쪽 special은 원 helper와 같이 enclosing chunk를 거부한다.
            if 0 < position < end - start and position not in boundaries:
                groups[bisect_right(boundaries, position) - 1].append(token)
            continue
        if token.byte_end <= start or token.byte_start >= end:
            continue
        left = max(0, token.byte_start - start)
        right = min(end - start, token.byte_end - start)
        index = bisect_right(boundaries, left) - 1
        while index < len(groups) and boundaries[index] < right:
            groups[index].append(token)
            index += 1
    return tuple(tuple(group) for group in groups)


def _crossing_indices(stream: ByteStream, span: tuple[int, int]) -> tuple[int, ...]:
    start, end = span
    return tuple(token.raw_index for token in stream.tokens
                 if token.data and token.byte_start < end and token.byte_end > start
                 and (token.byte_start < start or token.byte_end > end))


def _supervised_bytes(stream: ByteStream, span: tuple[int, int]) -> int:
    """통계용 교집합 byte 수이며 부분 token을 학습 대상으로 사용하지 않는다."""
    start, end = span
    return sum(max(0, min(end, token.byte_end) - max(start, token.byte_start))
               for token in stream.tokens
               if token.supervised and token.special_kind is None)


def align_answer_contents(
    student_stream: ByteStream,
    teacher_stream: ByteStream,
    student_span: tuple[int, int],
    teacher_span: tuple[int, int],
) -> AnswerAlignmentResult:
    """같은 지정 본문 bytes에서 가장 짧은 완전 native-token 공통 chunk만 수락.

    범위 끝이 native token 안에 있으면 그 token을 자르지 않고 해당 가장자리
    byte 구간을 거부한다. raw index0은 선행 logits가 없어 거부한다. special,
    무감독, 서로 다른 semantic turn은 제외하되 원 raw/shift/범위를 보존한다.
    어떤 byte도 남지 않아도 coverage0과 이유를 반환하며 행을 고치지 않는다.

    caller가 실제 assistant 본문 span/turn/mask를 인증해야 한다. 이 함수는
    서로 다른 prefix의 조건부 확률이 같거나 의미/정답이 같다고 주장하지 않는다.
    """
    validate_stream(student_stream)
    validate_stream(teacher_stream)
    if (student_stream.source != "student_bytelevel"
            or teacher_stream.source != "teacher_native"):
        raise ByteAlignmentError("student and teacher byte stream roles were swapped")
    student_span = _span(student_span, student_stream, "student")
    teacher_span = _span(teacher_span, teacher_stream, "teacher")
    s0, s1 = student_span
    t0, t1 = teacher_span
    answer = student_stream.text_utf8[s0:s1]
    if answer != teacher_stream.text_utf8[t0:t1]:
        raise ByteAlignmentError("answer content bytes differ; no normalization or approximate alignment")
    length = len(answer)
    common = tuple(sorted(_boundaries(student_stream, student_span)
                          & _boundaries(teacher_stream, teacher_span)))
    # 범위 끝은 검산용 partition에만 추가한다. native 공통 경계로 승격하지 않는다.
    boundaries = tuple(sorted({0, length, *common}))
    student_groups = _groups(student_stream, student_span, boundaries)
    teacher_groups = _groups(teacher_stream, teacher_span, boundaries)
    chunks = []
    rejected = []
    for left, right, sg, tg in zip(boundaries, boundaries[1:], student_groups, teacher_groups):
        if not sg or not tg:
            raise ByteAlignmentError("full input has no token for a nonempty answer interval")
        sr = tuple(token.raw_index for token in sg)
        tr = tuple(token.raw_index for token in tg)
        absolute = (s0 + left, s0 + right, t0 + left, t0 + right)
        reasons = []
        for name, group, start, end in (
            ("student", sg, absolute[0], absolute[1]),
            ("teacher", tg, absolute[2], absolute[3]),
        ):
            if any(token.byte_start < start or token.byte_end > end for token in group):
                reasons.append(name + "_boundary_crossing")
        if not reasons:
            sd = b"".join(token.data for token in sg)
            td = b"".join(token.data for token in tg)
            if sd != td or sd != answer[left:right]:
                raise ByteAlignmentError("native answer interval bytes differ")
        both = sg + tg
        if any(token.special_kind is not None for token in both):
            reasons.append("special_token")
        if any(not token.supervised for token in both):
            reasons.append("unsupervised_token")
        st = {token.turn_id for token in sg}
        tt = {token.turn_id for token in tg}
        if len(st) != 1 or len(tt) != 1:
            reasons.append("turn_boundary")
        elif st != tt:
            reasons.append("turn_mismatch")
        if 0 in sr or 0 in tr:
            reasons.append("unpredictable_first_token")
        if reasons:
            rejected.append(AnswerRejectedChunk(left, right, sr, tr, tuple(reasons), *absolute))
            continue
        turn = next(iter(st))
        if turn == 0:
            raise ByteAlignmentError("accepted answer chunk lacks an assistant turn")
        chunks.append(AnswerAlignedChunk(
            left, right, answer[left:right], turn, sr, tr,
            raw_to_shifted(sr), raw_to_shifted(tr), *absolute,
        ))

    # zero-byte special이 정확한 경계에 있으면 이웃은 수락할 수 있지만 그
    # special 자체의 제외 이유/원 index/각 절대 위치는 별도로 잃지 않는다.
    zero_specials: dict[int, list[list[int]]] = {}
    for side, stream, (start, end) in (
        (0, student_stream, student_span), (1, teacher_stream, teacher_span),
    ):
        for token in stream.tokens:
            position = token.byte_start - start
            if (token.special_kind is not None and not token.data
                    and start <= token.byte_start <= end and position in boundaries):
                zero_specials.setdefault(position, [[], []])[side].append(token.raw_index)
    for position, (sr, tr) in zero_specials.items():
        rejected.append(AnswerRejectedChunk(
            position, position, tuple(sr), tuple(tr),
            ("special_token", "zero_byte_special_at_boundary"),
            s0 + position, s0 + position, t0 + position, t0 + position,
        ))
    rejected.sort(key=lambda item: (item.byte_start, item.byte_end))
    uncovered = [item for item in rejected if item.byte_start < item.byte_end]
    covered_count = sum(item.byte_end - item.byte_start for item in chunks)
    uncovered_count = sum(item.byte_end - item.byte_start for item in uncovered)
    if covered_count + uncovered_count != length:
        raise ByteAlignmentError("answer byte accounting does not partition the declared content")
    return AnswerAlignmentResult(
        tuple(chunks), tuple(rejected), student_span, teacher_span,
        len(student_stream.text_utf8), len(teacher_stream.text_utf8),
        length, covered_count, uncovered_count,
        sum(item.byte_end - item.byte_start for item in uncovered
            if any(reason.endswith("_boundary_crossing") for reason in item.reasons)),
        tuple((item.student_byte_start, item.student_byte_end) for item in uncovered),
        tuple((item.teacher_byte_start, item.teacher_byte_end) for item in uncovered),
        _crossing_indices(student_stream, student_span),
        _crossing_indices(teacher_stream, teacher_span),
        tuple(token.raw_index for token in student_stream.tokens if token.special_kind is not None),
        tuple(token.raw_index for token in teacher_stream.tokens if token.special_kind is not None),
        _supervised_bytes(student_stream, student_span),
        _supervised_bytes(teacher_stream, teacher_span),
        common,
    )
