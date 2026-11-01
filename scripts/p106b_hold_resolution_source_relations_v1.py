#!/usr/bin/env python3
"""Diagnose newly written wiki link relationships that have no source pair.

This checks literal pair provenance, not factual identity or general semantic
preservation. Completing a single missing wrapper does not invent its values.
"""
from collections import Counter
import re

LINK_PAIR = re.compile(r"\[+([^\[\]|\n]+)\|([^\[\]\n]+)\]+")


def literal_link_pairs(text):
    return Counter((match[1].strip(), match[2].strip()) for match in LINK_PAIR.finditer(text))


def ungrounded_new_link_pairs(original, cleaned):
    source, candidate = literal_link_pairs(original), literal_link_pairs(cleaned)
    return {pair: count - source[pair] for pair, count in candidate.items() if count > source[pair]}


def missing_source_link_pairs(original, cleaned):
    """Report literal losses for review; a removed navigation pair may be valid."""
    source, candidate = literal_link_pairs(original), literal_link_pairs(cleaned)
    return {pair: count - candidate[pair] for pair, count in source.items() if count > candidate[pair]}
