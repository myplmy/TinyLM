"""P106B Stage7b: pure native-ID byte alignment, not an ALM loss.

No tokenizer/model imports, I/O, normalization, or token-ID rewriting occur here.
Both streams must reconstruct the *same full input* exactly. Model-specific chat
templates cannot be equated by this helper. Callers own native special-token
metadata, assistant masks, semantic turn IDs, and probability provenance.

SpecialToken.source_bytes explicitly distinguishes a literal marker consumed
from the input from an automatically inserted, zero-byte BOS/EOT. A special
declaration binds an original raw index AND token ID. Empty/missing ordinary
pieces are invalid. No special token is an ALM target, even if CE supervises it.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass


class ByteAlignmentError(ValueError):
    """The supplied native token/byte contract is inconsistent."""


def _bytelevel_inverse() -> dict[str, int]:
    # Same alphabet already used by diag_vocab/diag_val_lang, without importing
    # their numpy/config/prepare dependencies or their lossy display decoding.
    visible = list(range(33, 127)) + list(range(161, 173)) + list(range(174, 256))
    byte_values = visible[:]
    codepoints = visible[:]
    extension = 0
    for value in range(256):
        if value not in visible:
            byte_values.append(value)
            codepoints.append(256 + extension)
            extension += 1
    return {chr(codepoint): value for value, codepoint in zip(byte_values, codepoints)}


_BYTELEVEL_INVERSE = _bytelevel_inverse()


def student_piece_bytes(piece: str) -> bytes:
    """Invert GPT-2 ByteLevel characters; do NOT UTF-8 encode the visible piece."""
    if not isinstance(piece, str):
        raise ByteAlignmentError("student ordinary piece must be a string")
    try:
        return bytes(_BYTELEVEL_INVERSE[char] for char in piece)
    except KeyError as exc:
        raise ByteAlignmentError("student piece contains a non-ByteLevel character") from exc


TeacherPiece = str | list[int] | tuple[int, ...] | None


def teacher_piece_bytes(piece: TeacherPiece) -> bytes:
    """Decode the server's string-or-integer-byte-array union, without repair."""
    if isinstance(piece, str):
        try:
            return piece.encode("utf-8", errors="strict")
        except UnicodeEncodeError as exc:
            raise ByteAlignmentError("teacher string piece is not valid UTF-8") from exc
    if isinstance(piece, (list, tuple)):
        if any(type(value) is not int or not 0 <= value <= 255 for value in piece):
            raise ByteAlignmentError("teacher byte array requires integers in [0, 255]")
        return bytes(piece)
    raise ByteAlignmentError("teacher piece must be a string or integer byte array")


@dataclass(frozen=True)
class SpecialToken:
    raw_index: int
    token_id: int
    kind: str
    source_bytes: bytes


@dataclass(frozen=True)
class TokenByteSpan:
    raw_index: int
    token_id: int
    byte_start: int
    byte_end: int
    data: bytes
    supervised: bool
    turn_id: int
    special_kind: str | None = None


@dataclass(frozen=True)
class ByteStream:
    source: str
    text_utf8: bytes
    tokens: tuple[TokenByteSpan, ...]


class ShiftedTargetIndices(tuple):
    """Immutable sequence tag: an existing shifted map must not be shifted again."""

    __slots__ = ()

    def __new__(cls, values: Sequence[int] = ()) -> ShiftedTargetIndices:
        return super().__new__(cls, values)


@dataclass(frozen=True)
class AlignedChunk:
    byte_start: int
    byte_end: int
    data: bytes
    turn_id: int
    student_raw_indices: tuple[int, ...]
    teacher_raw_indices: tuple[int, ...]
    student_shifted_indices: ShiftedTargetIndices
    teacher_shifted_indices: ShiftedTargetIndices


@dataclass(frozen=True)
class RejectedChunk:
    byte_start: int
    byte_end: int
    student_raw_indices: tuple[int, ...]
    teacher_raw_indices: tuple[int, ...]
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class AlignmentResult:
    chunks: tuple[AlignedChunk, ...]
    rejected: tuple[RejectedChunk, ...]
    student_special_indices: tuple[int, ...]
    teacher_special_indices: tuple[int, ...]
    input_byte_count: int
    covered_byte_count: int
    student_supervised_byte_count: int
    teacher_supervised_byte_count: int


def raw_to_shifted(
    raw_indices: Sequence[int], *, already_shifted: bool = False
) -> ShiftedTargetIndices:
    """Map raw target i to logits/NLL row i-1, once and in original order.

    Returned maps carry an immutable tuple tag which rejects a second call.
    An external untagged copy cannot reveal an earlier shift; callers must set
    already_shifted=True for that provenance. Chunks expose both maps.
    Raw index zero has no preceding logits row and is never a valid target here.
    Rows refer to the full shifted sequence BEFORE IGNORE/valid-token gathering,
    never to positions in an independently compacted NLL vector.
    """
    if (isinstance(raw_indices, ShiftedTargetIndices)
            or type(already_shifted) is not bool or already_shifted):
        raise ByteAlignmentError("only unshifted raw target indices may be mapped")
    indices = tuple(raw_indices)
    previous = 0
    for index in indices:
        if type(index) is not int or index <= previous:
            raise ByteAlignmentError("raw targets must be positive, unique, and increasing")
        previous = index
    return ShiftedTargetIndices(tuple(index - 1 for index in indices))


def _check_token_metadata(token_id: int, supervised: bool, turn_id: int) -> None:
    if type(token_id) is not int or token_id < 0:
        raise ByteAlignmentError("native token IDs must be nonnegative integers")
    if type(supervised) is not bool:
        raise ByteAlignmentError("supervised mask must contain bool values")
    if type(turn_id) is not int or turn_id < 0:
        raise ByteAlignmentError("turn IDs must be nonnegative integers")
    if supervised and turn_id == 0:
        raise ByteAlignmentError("supervised tokens require a positive semantic turn ID")


def _build_stream(
    source: str,
    text: str,
    token_ids: Sequence[int],
    pieces: Sequence[TeacherPiece],
    supervised: Sequence[bool],
    turn_ids: Sequence[int],
    specials: Sequence[SpecialToken],
) -> ByteStream:
    if not isinstance(text, str):
        raise ByteAlignmentError("full source text must be a string")
    try:
        text_utf8 = text.encode("utf-8", errors="strict")
    except UnicodeEncodeError as exc:
        raise ByteAlignmentError("full source text is not valid UTF-8") from exc
    ids = tuple(token_ids)
    piece_values = tuple(pieces)
    mask = tuple(supervised)
    turns = tuple(turn_ids)
    if not (len(ids) == len(piece_values) == len(mask) == len(turns)):
        raise ByteAlignmentError("IDs, pieces, supervised mask, and turn IDs differ in length")
    special_by_index: dict[int, SpecialToken] = {}
    for special in specials:
        if not isinstance(special, SpecialToken):
            raise ByteAlignmentError("special declarations must be SpecialToken records")
        index = special.raw_index
        if type(index) is not int or not 0 <= index < len(ids):
            raise ByteAlignmentError("special raw index is outside the original token stream")
        if index in special_by_index:
            raise ByteAlignmentError("duplicate or overlapping special index declaration")
        if type(special.token_id) is not int or special.token_id != ids[index]:
            raise ByteAlignmentError("special declaration does not bind the native token ID")
        if not isinstance(special.kind, str) or not special.kind.strip():
            raise ByteAlignmentError("special kind must be an explicit nonempty string")
        if type(special.source_bytes) is not bytes:
            raise ByteAlignmentError("special source consumption must be explicit bytes")
        special_by_index[index] = special
    declared_special_ids = {special.token_id for special in special_by_index.values()}
    native_piece_by_id: dict[int, bytes] = {}
    spans = []
    cursor = 0
    for index, (token_id, piece, keep, turn) in enumerate(zip(ids, piece_values, mask, turns)):
        _check_token_metadata(token_id, keep, turn)
        special = special_by_index.get(index)
        if special is None:
            if token_id in declared_special_ids:
                raise ByteAlignmentError("every occurrence of a declared special ID needs its own index declaration")
            if piece is None:
                raise ByteAlignmentError("missing piece is allowed only at a declared special index")
            if source == "student_bytelevel":
                if not isinstance(piece, str):
                    raise ByteAlignmentError("student ordinary piece must be a string")
                data = student_piece_bytes(piece)
            else:
                data = teacher_piece_bytes(piece)
            if not data:
                raise ByteAlignmentError("ordinary token must consume at least one source byte")
            native_piece = data
        else:
            data = special.source_bytes
            if data:
                # Literal markers consume real source bytes; a declaration may
                # not silently replace an inconsistent native piece.
                actual = teacher_piece_bytes(piece)
                if actual != data:
                    raise ByteAlignmentError("literal special piece differs from declared source bytes")
                native_piece = actual
            elif piece is not None:
                # Validate the transport type even though automatic BOS/EOT has
                # a display name which is not present in the original source.
                native_piece = teacher_piece_bytes(piece)
            else:
                native_piece = None
        if native_piece is not None:
            if token_id in native_piece_by_id and native_piece_by_id[token_id] != native_piece:
                raise ByteAlignmentError("one native token ID has inconsistent pieces")
            native_piece_by_id[token_id] = native_piece
        end = cursor + len(data)
        if text_utf8[cursor:end] != data:
            raise ByteAlignmentError(f"source reconstruction mismatch at raw token index {index}")
        spans.append(TokenByteSpan(index, token_id, cursor, end, data, keep, turn,
                                   None if special is None else special.kind))
        cursor = end
    if cursor != len(text_utf8):
        raise ByteAlignmentError("native pieces do not reconstruct the entire source text")
    result = ByteStream(source, text_utf8, tuple(spans))
    validate_stream(result)
    return result


def build_student_stream(
    text: str,
    token_ids: Sequence[int],
    pieces: Sequence[str | None],
    *,
    supervised: Sequence[bool],
    turn_ids: Sequence[int],
    specials: Sequence[SpecialToken] = (),
) -> ByteStream:
    """Build exact spans from the student's existing ByteLevel IDs/pieces.

    Ordinary pieces use the ByteLevel inverse. Declared literal special pieces
    are their literal UTF-8 marker spellings, not ByteLevel-encoded display text.
    """
    return _build_stream("student_bytelevel", text, token_ids, pieces, supervised,
                         turn_ids, specials)


def build_teacher_stream(
    text: str,
    token_ids: Sequence[int],
    pieces: Sequence[TeacherPiece],
    *,
    supervised: Sequence[bool],
    turn_ids: Sequence[int],
    specials: Sequence[SpecialToken] = (),
) -> ByteStream:
    """Build exact spans from native server piece strings/byte arrays."""
    return _build_stream("teacher_native", text, token_ids, pieces, supervised,
                         turn_ids, specials)


def validate_stream(stream: ByteStream) -> None:
    """Reject forged/overlapping spans as well as incomplete reconstruction."""
    if not isinstance(stream, ByteStream) or stream.source not in {
        "student_bytelevel", "teacher_native"
    }:
        raise ByteAlignmentError("unknown byte stream source")
    if type(stream.text_utf8) is not bytes or type(stream.tokens) is not tuple:
        raise ByteAlignmentError("stream payload and native spans must be immutable")
    try:
        stream.text_utf8.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise ByteAlignmentError("complete source must be valid UTF-8") from exc
    cursor = 0
    ordinary_by_id: dict[int, bytes] = {}
    for index, token in enumerate(stream.tokens):
        if not isinstance(token, TokenByteSpan) or type(token.raw_index) is not int or token.raw_index != index:
            raise ByteAlignmentError("native raw indices must be contiguous and unchanged")
        _check_token_metadata(token.token_id, token.supervised, token.turn_id)
        if (type(token.byte_start) is not int or type(token.byte_end) is not int
                or token.byte_start != cursor or token.byte_end < cursor
                or type(token.data) is not bytes or token.byte_end - cursor != len(token.data)):
            raise ByteAlignmentError("overlapping, gapped, or inconsistent native byte spans")
        if token.special_kind is not None and (
            not isinstance(token.special_kind, str) or not token.special_kind.strip()
        ):
            raise ByteAlignmentError("special kind must be explicit")
        if not token.data and token.special_kind is None:
            raise ByteAlignmentError("zero-byte token is not a declared special")
        if token.special_kind is None:
            if token.token_id in ordinary_by_id and ordinary_by_id[token.token_id] != token.data:
                raise ByteAlignmentError("one native ordinary token ID has inconsistent bytes")
            ordinary_by_id[token.token_id] = token.data
        if stream.text_utf8[cursor:token.byte_end] != token.data:
            raise ByteAlignmentError("span bytes differ from original source")
        cursor = token.byte_end
    if cursor != len(stream.text_utf8):
        raise ByteAlignmentError("spans do not cover the complete source exactly")
    special_ids = {token.token_id for token in stream.tokens if token.special_kind is not None}
    if special_ids & ordinary_by_id.keys():
        raise ByteAlignmentError("special and ordinary occurrences of one token ID are ambiguous")


def _interval_tokens(
    stream: ByteStream, boundaries: tuple[int, ...]
) -> tuple[tuple[TokenByteSpan, ...], ...]:
    """Linear sweep; an interior zero-byte special poisons its enclosing chunk."""
    groups: list[list[TokenByteSpan]] = [[] for _ in range(len(boundaries) - 1)]
    if not groups:
        return ()
    interval = 0
    for token in stream.tokens:
        while interval + 1 < len(groups) and token.byte_start >= boundaries[interval + 1]:
            interval += 1
        left, right = boundaries[interval], boundaries[interval + 1]
        if not token.data:
            if left < token.byte_start < right:
                groups[interval].append(token)
            continue
        if token.byte_start < left or token.byte_end > right:
            raise ByteAlignmentError("a token overlaps a supposed common boundary")
        groups[interval].append(token)
    return tuple(tuple(group) for group in groups)


def align_assistant_chunks(student: ByteStream, teacher: ByteStream) -> AlignmentResult:
    """Return shortest common byte chunks, accepting only fully supervised turns.

    Zero-byte specials at a shared boundary are retained in stream metadata but
    not included in either neighbor. An interior special or any consumed literal
    special rejects the enclosing candidate. The result is structural evidence,
    not a probability/gradient/quality assertion.
    """
    validate_stream(student)
    validate_stream(teacher)
    if student.source != "student_bytelevel" or teacher.source != "teacher_native":
        raise ByteAlignmentError("student and teacher byte stream roles were swapped")
    if student.text_utf8 != teacher.text_utf8:
        raise ByteAlignmentError("templates/full source bytes differ; no approximate alignment")
    student_ends = {0} | {token.byte_end for token in student.tokens}
    teacher_ends = {0} | {token.byte_end for token in teacher.tokens}
    boundaries = tuple(sorted(student_ends & teacher_ends))
    student_groups = _interval_tokens(student, boundaries)
    teacher_groups = _interval_tokens(teacher, boundaries)
    chunks = []
    rejected = []
    for left, right, student_group, teacher_group in zip(
        boundaries, boundaries[1:], student_groups, teacher_groups
    ):
        if not student_group or not teacher_group:
            raise ByteAlignmentError("common nonempty byte interval has an empty token side")
        student_raw = tuple(token.raw_index for token in student_group)
        teacher_raw = tuple(token.raw_index for token in teacher_group)
        student_data = b"".join(token.data for token in student_group)
        teacher_data = b"".join(token.data for token in teacher_group)
        if student_data != teacher_data or student_data != student.text_utf8[left:right]:
            raise ByteAlignmentError("equal cumulative lengths conceal different byte content")
        reasons = []
        both = student_group + teacher_group
        if any(token.special_kind is not None for token in both):
            reasons.append("special_token")
        if any(not token.supervised for token in both):
            reasons.append("unsupervised_token")
        student_turns = {token.turn_id for token in student_group}
        teacher_turns = {token.turn_id for token in teacher_group}
        if len(student_turns) != 1 or len(teacher_turns) != 1:
            reasons.append("turn_boundary")
        elif student_turns != teacher_turns:
            reasons.append("turn_mismatch")
        if 0 in student_raw or 0 in teacher_raw:
            reasons.append("unpredictable_first_token")
        if reasons:
            rejected.append(RejectedChunk(left, right, student_raw, teacher_raw, tuple(reasons)))
            continue
        turn_id = next(iter(student_turns))
        if turn_id == 0:
            raise ByteAlignmentError("accepted chunk has no assistant turn ID")
        chunks.append(AlignedChunk(left, right, student_data, turn_id, student_raw,
                                   teacher_raw, raw_to_shifted(student_raw),
                                   raw_to_shifted(teacher_raw)))
    return AlignmentResult(
        tuple(chunks), tuple(rejected),
        tuple(token.raw_index for token in student.tokens if token.special_kind is not None),
        tuple(token.raw_index for token in teacher.tokens if token.special_kind is not None),
        len(student.text_utf8), sum(chunk.byte_end - chunk.byte_start for chunk in chunks),
        sum(len(token.data) for token in student.tokens if token.supervised and token.special_kind is None),
        sum(len(token.data) for token in teacher.tokens if token.supervised and token.special_kind is None),
    )
