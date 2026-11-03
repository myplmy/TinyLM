"""Add one exact basename-heading spelling, preserving v1 rejection guards."""
from exact_review_header_alias_v1 import wrap_review_entries as wrap_v1


def wrap_review_entries(original):
    def explicit_basename_header(payload, allow_sections=False):
        normalized = []
        for entry in original(payload, allow_sections=allow_sections):
            header = entry.get('header')
            if header is not None:
                header = ['출력' if value == '출력 (TXT basename)' else value for value in header]
                entry = dict(entry, header=header)
            normalized.append(entry)
        return normalized
    return wrap_v1(explicit_basename_header)
