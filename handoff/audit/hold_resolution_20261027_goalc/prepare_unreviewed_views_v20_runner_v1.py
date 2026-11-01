"""Reuse the exact ordered-view implementation for the new disjoint cohort."""
from pathlib import Path

base = Path(__file__).resolve().parent
source = (base / "prepare_selected_readback_views_v2.py").read_text(encoding="utf-8")
assert source.count('"root_selected_signal_counter_v2"') == 1
source = source.replace('"root_selected_signal_counter_v2"', '"remaining_unreviewed_context_v20_v1"')
with (base / "prepare_unreviewed_reading_views_v20_v1.py").open("x", encoding="utf-8") as out:
    out.write(source)
