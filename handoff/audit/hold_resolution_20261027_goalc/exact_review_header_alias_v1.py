"""Recognize one exact human output heading without guessing any body path."""
OUTPUT_HEADERS = frozenset({'출력', '정확 출력', '산출물'})
OUTPUT_ALIASES = {'출력 TXT': '출력'}


def wrap_review_entries(original):
    def review_entries(payload, allow_sections=False):
        entries = original(payload, allow_sections=allow_sections)
        normalized = []
        for entry in entries:
            header = entry.get('header')
            if header is None:
                normalized.append(entry)
                continue
            canonical = [OUTPUT_ALIASES.get(label, label) for label in header]
            if sum(label in OUTPUT_HEADERS for label in canonical) > 1:
                raise ValueError('AMBIGUOUS_EXPLICIT_OUTPUT_HEADERS')
            normalized.append(dict(entry, header=canonical))
        return normalized
    return review_entries
