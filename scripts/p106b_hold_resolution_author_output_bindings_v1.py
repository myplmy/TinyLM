"""Bind an explicit review output to its exact input or assigned author directory."""
from pathlib import Path
import re


def declared_txt_basename(cell, source_id, directory, paths, status):
    directory = Path(directory).resolve()
    absolute = re.findall(r"/[^\s`|()<>]+[.]txt", cell)
    if absolute:
        if len(absolute) != 1:
            raise ValueError("MULTIPLE_EXPLICIT_BODY_OUTPUTS")
        output = Path(absolute[0]).resolve()
    else:
        bare = cell.strip(" `*")
        if not re.fullmatch(r"[^/\s`|()<>]+[.]txt", bare):
            raise ValueError("NO_EXACT_BODY_OUTPUT_PATH")
        if status in {"KEEP_SOURCE", "ADOPT_CANDIDATE"}:
            chosen = Path(paths["original" if status == "KEEP_SOURCE" else "candidate"]["path"])
            if bare != chosen.name:
                raise ValueError("ACCEPT_OUTPUT_IS_NOT_EXACT_ASSIGNED_INPUT")
            output = chosen.resolve()
        else:
            output = directory / bare
    if status in {"KEEP_SOURCE", "ADOPT_CANDIDATE"}:
        chosen = Path(paths["original" if status == "KEEP_SOURCE" else "candidate"]["path"]).resolve()
        if output != chosen:
            raise ValueError("ACCEPT_OUTPUT_IS_NOT_EXACT_ASSIGNED_INPUT")
    else:
        if status != "EDIT_TEXT" or output.parent != directory:
            raise ValueError("AUTHORED_OUTPUT_IS_OUTSIDE_EXACT_ASSIGNED_DIRECTORY")
        number = source_id.rsplit(":", 1)[1]
        if not re.search(r"(?:^|_)" + re.escape(number) + r"(?:_|[.]|$)", output.name):
            raise ValueError("AUTHORED_OUTPUT_FILENAME_HAS_ANOTHER_SOURCE_ID")
    return output.name
