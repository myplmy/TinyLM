#!/usr/bin/env python3
"""Static validator for the isolated TinyLM Codex project environment.

The validator uses an explicit allowlist of environment paths. It never walks the
protected dataset tree and it does not run project, model, training, or smoke code.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable
from urllib.parse import unquote

REPO_ROOT = Path(__file__).resolve().parents[1]
AGENTS_PATH = REPO_ROOT / "AGENTS.md"
AGENTS_ROOT = REPO_ROOT / ".agents"
CODEX_ROOT = REPO_ROOT / ".codex"
MEMORY_ROOT = REPO_ROOT / "ai_dev_tool" / "Codex"
ROOT_09 = REPO_ROOT / "ai_dev_tool" / "09_구현검증_필요목록.md"
WORKING_RULES_EN = MEMORY_ROOT / "00_WORKING_RULES.md"
WORKING_RULES_KO = MEMORY_ROOT / "00_작업규약_한글판.md"
PROPOSAL = (
    REPO_ROOT
    / "proposal"
    / "done"
    / "20260911_Codex-작업환경-완전분리-구축-approved.md"
)
MIGRATION_MAP = MEMORY_ROOT / "temp_AGENTS.MD_항목별_00_08_이식목록.md"
VALIDATION_REPORT = MEMORY_ROOT / "P7_정적종합검증_보고.md"

EXPECTED_SKILLS = {
    "check-and-verify",
    "exp-plan",
    "exp-preflight",
    "grill-me",
    "grill-with-docs",
    "impact-analysis",
    "log-to-result",
    "plan-doc",
    "pr-workflow",
    "run-batch",
    "session-handoff",
    "setup-matt-pocock-skills",
    "to-issues",
    "to-prd",
    "triage",
    "wip-ledger",
    "zoom-out",
}

TEXT_SUFFIXES = {
    ".md",
    ".json",
    ".toml",
    ".py",
    ".ps1",
    ".sh",
    ".tsv",
}

SKILL_CONTRACT_PATTERNS = {
    "trigger": re.compile(
        r"(?i)use when|사용|요청|지시|asks?|wants?|invok|언제 쓰|when to"
    ),
    "input": re.compile(
        r"(?i)입력|input|context|문서|로그|plan|issue|request|사용자|대화|코드"
    ),
    "permission": re.compile(
        r"(?i)승인|permission|권한|사용자|confirm|ask|명시|read.only|외부"
    ),
    "output": re.compile(
        r"(?i)산출|output|보고|작성|생성|갱신|정리|문서|결과|요약|create|update|draft"
    ),
    "prohibited": re.compile(
        r"(?i)금지|하지|않|아니|never|do not|don't|without|only after|out of scope|제외|막"
    ),
}

RULE_LINE_RE = re.compile(
    r"(?m)^-\s+(?:★+)?\*\*R(?P<id>\d{2})\*\*\s+`\[(?P<tag>[^]]+)\]`"
)
RULE_METADATA = {
    "en": {
        "date": re.compile(r"\*\*Last updated\*\*:\s*(\d{4}-\d{2}-\d{2})"),
        "labels": {"gate": "gate", "human": "human", "fact": "fact"},
    },
    "ko": {
        "date": re.compile(r"\*\*최신 갱신일자\*\*:\s*(\d{4}-\d{2}-\d{2})"),
        "labels": {"게이트": "gate", "사람": "human", "사실": "fact"},
    },
}


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    detail: str


class Ledger:
    def __init__(self) -> None:
        self.results: list[CheckResult] = []

    def record(self, name: str, passed: bool, detail: str) -> None:
        self.results.append(CheckResult(name, passed, detail))

    def guarded(self, name: str, check: Callable[[], tuple[bool, str]]) -> None:
        try:
            passed, detail = check()
        except Exception as exc:
            passed = False
            detail = f"{type(exc).__name__}: {exc}"
        self.record(name, passed, detail)

    def emit(self) -> int:
        for item in self.results:
            state = "PASS" if item.passed else "FAIL"
            print(f"[{state}] {item.name}: {item.detail}")
        failures = sum(not item.passed for item in self.results)
        print(
            f"SUMMARY checks={len(self.results)} "
            f"passed={len(self.results) - failures} failed={failures}"
        )
        return 0 if failures == 0 else 1


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def read_utf8(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def parse_working_rules(path: Path, language: str) -> tuple[str, dict[str, int], dict[int, str]]:
    """Parse declared metadata and the first classification tag on every Rxx rule."""
    text = read_utf8(path)
    metadata_line = next(
        (line for line in text.splitlines()[:12] if "Rule counts" in line or "규칙 개수" in line),
        "",
    )
    config = RULE_METADATA[language]
    date_match = config["date"].search(metadata_line)
    if date_match is None:
        raise ValueError("top metadata has no update date")

    declared: dict[str, int] = {}
    for source_label, canonical_label in config["labels"].items():
        match = re.search(rf"`\[{re.escape(source_label)}\]`\s+(\d+)", metadata_line)
        if match is None:
            raise ValueError(f"top metadata has no [{source_label}] count")
        declared[canonical_label] = int(match.group(1))

    rules: dict[int, str] = {}
    for match in RULE_LINE_RE.finditer(text):
        rule_id = int(match.group("id"))
        source_tag = match.group("tag")
        canonical_tag = config["labels"].get(source_tag)
        if canonical_tag is None:
            raise ValueError(f"R{rule_id:02d} has unknown tag [{source_tag}]")
        if rule_id in rules:
            raise ValueError(f"duplicate rule id R{rule_id:02d}")
        rules[rule_id] = canonical_tag
    if not rules:
        raise ValueError("no classified Rxx rules found")
    return date_match.group(1), declared, rules


def check_working_rule_parity() -> tuple[bool, str]:
    en_date, en_declared, en_rules = parse_working_rules(WORKING_RULES_EN, "en")
    ko_date, ko_declared, ko_rules = parse_working_rules(WORKING_RULES_KO, "ko")

    problems: list[str] = []
    if en_date != ko_date:
        problems.append(f"document dates differ en={en_date} ko={ko_date}")
    if en_declared != ko_declared:
        problems.append(f"declared counts differ en={en_declared} ko={ko_declared}")
    if en_rules != ko_rules:
        missing_en = sorted(set(ko_rules) - set(en_rules))
        missing_ko = sorted(set(en_rules) - set(ko_rules))
        tag_drift = sorted(
            rule_id for rule_id in set(en_rules) & set(ko_rules)
            if en_rules[rule_id] != ko_rules[rule_id]
        )
        problems.append(
            f"rule parity differs missing_en={missing_en} missing_ko={missing_ko} tag_drift={tag_drift}"
        )

    derived = {
        label: sum(tag == label for tag in en_rules.values())
        for label in ("gate", "human", "fact")
    }
    if en_declared != derived:
        problems.append(f"declared counts do not match rules declared={en_declared} derived={derived}")

    for path, declared_date in ((WORKING_RULES_EN, en_date), (WORKING_RULES_KO, ko_date)):
        metadata_date = dt.datetime.fromtimestamp(path.stat().st_mtime).date().isoformat()
        if metadata_date != declared_date:
            problems.append(
                f"{path.name} date differs document={declared_date} metadata={metadata_date}"
            )

    detail = (
        f"date={en_date}; rules={len(en_rules)}; "
        f"gate={derived['gate']} human={derived['human']} fact={derived['fact']}"
    )
    return not problems, detail if not problems else " | ".join(problems)


def collect_tree(root: Path) -> tuple[list[Path], list[Path], list[Path]]:
    """Collect files without following reparse points or links."""

    files: list[Path] = []
    reparse_points: list[Path] = []
    hardlinks: list[Path] = []
    stack = [root]
    reparse_flag = getattr(os.stat_result, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)

    while stack:
        current = stack.pop()
        with os.scandir(current) as entries:
            for entry in entries:
                path = Path(entry.path)
                stat_result = entry.stat(follow_symlinks=False)
                attributes = getattr(stat_result, "st_file_attributes", 0)
                is_reparse = entry.is_symlink() or bool(attributes & reparse_flag)
                if is_reparse:
                    reparse_points.append(path)
                    continue
                if entry.is_dir(follow_symlinks=False):
                    stack.append(path)
                elif entry.is_file(follow_symlinks=False):
                    files.append(path)
                    if stat_result.st_nlink > 1:
                        hardlinks.append(path)
    return sorted(files), sorted(reparse_points), sorted(hardlinks)


def relative_list(paths: Iterable[Path]) -> str:
    return ", ".join(path.relative_to(REPO_ROOT).as_posix() for path in paths)


def parse_frontmatter(path: Path) -> tuple[dict[str, str], str]:
    text = read_utf8(path)
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError("missing opening frontmatter marker")
    try:
        end = next(index for index in range(1, len(lines)) if lines[index].strip() == "---")
    except StopIteration as exc:
        raise ValueError("missing closing frontmatter marker") from exc

    metadata: dict[str, str] = {}
    for line in lines[1:end]:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip()
    return metadata, text


INLINE_LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
REFERENCE_LINK_RE = re.compile(r"(?m)^\s*\[[^\]]+\]:\s*(\S+)")
FENCED_CODE_RE = re.compile(
    r"(?ms)^[ \t]*(?:```|~~~).*?^[ \t]*(?:```|~~~)[ \t]*$"
)
PLACEHOLDER_LINK_RE = re.compile(
    r"(?i)(?:\.\.\.|P(?:xx|yy|##)|CPR_(?:scope|[^/]*title))"
)


def markdown_targets(text: str) -> Iterable[str]:
    for pattern in (INLINE_LINK_RE, REFERENCE_LINK_RE):
        for match in pattern.finditer(text):
            raw = match.group(1).strip()
            if raw.startswith("<") and ">" in raw:
                yield raw[1 : raw.index(">")]
            else:
                yield raw.split(maxsplit=1)[0]


def broken_markdown_links(paths: Iterable[Path]) -> list[str]:
    broken: list[str] = []
    for source in paths:
        text = FENCED_CODE_RE.sub("", read_utf8(source))
        for raw_target in markdown_targets(text):
            lowered = raw_target.lower()
            if (
                not raw_target
                or raw_target.startswith("#")
                or lowered.startswith(("http://", "https://", "mailto:"))
                or "{" in raw_target
                or "}" in raw_target
                or PLACEHOLDER_LINK_RE.search(raw_target)
            ):
                continue
            target_without_fragment = raw_target.split("#", 1)[0].split("?", 1)[0]
            if not target_without_fragment:
                continue
            target_text = unquote(target_without_fragment).replace("/", os.sep)
            target = (source.parent / target_text).resolve()
            try:
                target.relative_to(REPO_ROOT)
            except ValueError:
                broken.append(
                    f"{source.relative_to(REPO_ROOT).as_posix()} -> outside:{raw_target}"
                )
                continue
            if not target.exists():
                broken.append(
                    f"{source.relative_to(REPO_ROOT).as_posix()} -> {raw_target}"
                )
    return broken


def find_git_bash() -> Path | None:
    completed = subprocess.run(
        ["git", "--exec-path"],
        cwd=REPO_ROOT,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        return None
    git_exec = Path(completed.stdout.strip())
    if len(git_exec.parents) >= 3:
        candidate = git_exec.parents[2] / "bin" / "bash.exe"
        if candidate.is_file():
            return candidate
    return None


def to_msys_path(path: Path) -> str:
    resolved = path.resolve()
    drive = resolved.drive.rstrip(":").lower()
    if drive:
        tail = resolved.as_posix().split(":", 1)[1].lstrip("/")
        return f"/{drive}/{tail}"
    return resolved.as_posix()


def syntax_errors(files: Iterable[Path]) -> list[str]:
    errors: list[str] = []
    files = list(files)

    for path in (item for item in files if item.suffix.lower() == ".py"):
        try:
            compile(read_utf8(path), str(path), "exec")
        except SyntaxError as exc:
            errors.append(f"{path.relative_to(REPO_ROOT).as_posix()}: {exc}")

    powershell_files = [item for item in files if item.suffix.lower() == ".ps1"]
    for path in powershell_files:
        path_literal = str(path).replace("'", "''")
        parser_command = (
            "$tokens=$null; $errors=$null; "
            "[System.Management.Automation.Language.Parser]::ParseFile("
            f"'{path_literal}',[ref]$tokens,[ref]$errors) | Out-Null; "
            "if($errors.Count -gt 0){$errors | ForEach-Object {$_.Message}; exit 1}"
        )
        completed = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                parser_command,
            ],
            cwd=REPO_ROOT,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout).strip()
            errors.append(f"{path.relative_to(REPO_ROOT).as_posix()}: {detail}")

    shell_files = [item for item in files if item.suffix.lower() == ".sh"]
    bash = find_git_bash()
    if shell_files and bash is None:
        errors.append("Git Bash not found for shell syntax validation")
    elif bash is not None:
        for path in shell_files:
            completed = subprocess.run(
                [str(bash), "-n", to_msys_path(path)],
                cwd=REPO_ROOT,
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                check=False,
            )
            if completed.returncode != 0:
                detail = (completed.stderr or completed.stdout).strip()
                errors.append(f"{path.relative_to(REPO_ROOT).as_posix()}: {detail}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root09-sha256",
        required=True,
        help="P0 baseline SHA-256 for the shared root 09 ledger",
    )
    args = parser.parse_args()
    ledger = Ledger()

    if Path.cwd().resolve() != REPO_ROOT:
        print(f"FAIL: run from repository root {REPO_ROOT}", file=sys.stderr)
        return 2

    agents_files, agents_reparse, agents_hardlinks = collect_tree(AGENTS_ROOT)
    codex_files, codex_reparse, codex_hardlinks = collect_tree(CODEX_ROOT)
    environment_files = agents_files + codex_files
    text_files = [
        path for path in environment_files if path.suffix.lower() in TEXT_SUFFIXES
    ]

    ledger.record(
        "environment allowlist",
        all(
            path == AGENTS_PATH
            or AGENTS_ROOT in path.parents
            or CODEX_ROOT in path.parents
            or MEMORY_ROOT in path.parents
            for path in [AGENTS_PATH, *environment_files]
        ),
        "only AGENTS.md, .agents, .codex, Codex memory and named evidence files",
    )

    linked = agents_reparse + codex_reparse
    ledger.record(
        "no symbolic link or junction",
        not linked,
        "0 reparse points" if not linked else relative_list(linked),
    )
    hardlinked = agents_hardlinks + codex_hardlinks
    ledger.record(
        "no hardlinked environment file",
        not hardlinked,
        "all link counts are 1" if not hardlinked else relative_list(hardlinked),
    )

    def check_json_toml() -> tuple[bool, str]:
        project = json.loads(read_utf8(AGENTS_ROOT / "project.json"))
        hooks = json.loads(read_utf8(CODEX_ROOT / "hooks.json"))
        config = tomllib.loads(read_utf8(CODEX_ROOT / "config.toml"))
        if not isinstance(project, dict) or not isinstance(hooks, dict) or not isinstance(config, dict):
            return False, "top-level object is not a mapping"
        return True, "project.json, hooks.json and config.toml parsed"

    ledger.guarded("JSON and TOML syntax", check_json_toml)

    ledger.guarded(
        "working-rule date and classification parity",
        check_working_rule_parity,
    )

    errors = syntax_errors(environment_files)
    ledger.record(
        "Python, PowerShell and shell syntax",
        not errors,
        "all environment source files parsed" if not errors else " | ".join(errors),
    )

    def check_project_roles() -> tuple[bool, str]:
        project = json.loads(read_utf8(AGENTS_ROOT / "project.json"))
        config = tomllib.loads(read_utf8(CODEX_ROOT / "config.toml"))
        required_project = {
            "skillRoot",
            "codexLongTermMemory",
            "planDir",
            "planDoneDir",
            "handoffDir",
            "sharedImplementationLedger",
            "singleSource",
            "domainAxes",
            "docImpactTargets",
            "excludedPaths",
            "evidenceStates",
        }
        missing = sorted(required_project - set(project))
        if missing:
            return False, f"project.json missing {missing}"
        if project["skillRoot"] != ".agents/skills":
            return False, "skillRoot is not .agents/skills"
        if project["codexLongTermMemory"] != "ai_dev_tool/Codex":
            return False, "long-term memory path is not Codex-only"
        if project["sharedImplementationLedger"] != "ai_dev_tool/09_구현검증_필요목록.md":
            return False, "shared root 09 pointer changed"
        allowed_config = {
            "project_doc_max_bytes",
            "project_doc_fallback_filenames",
            "project_root_markers",
        }
        extra_config = sorted(set(config) - allowed_config)
        if extra_config:
            return False, f"config.toml mixes non-native metadata: {extra_config}"
        return True, "repository metadata and native Codex settings remain separated"

    ledger.guarded("project and native setting roles", check_project_roles)

    skill_files = {
        path.parent.name: path
        for path in agents_files
        if path.name == "SKILL.md" and path.parent.parent.name == "skills"
    }
    ledger.record(
        "skill inventory",
        set(skill_files) == EXPECTED_SKILLS,
        (
            "17 expected skills found"
            if set(skill_files) == EXPECTED_SKILLS
            else f"found={sorted(skill_files)}"
        ),
    )

    skill_contract_errors: list[str] = []
    for skill_name, path in sorted(skill_files.items()):
        try:
            metadata, text = parse_frontmatter(path)
        except ValueError as exc:
            skill_contract_errors.append(f"{skill_name}: {exc}")
            continue
        if metadata.get("name") != skill_name:
            skill_contract_errors.append(f"{skill_name}: frontmatter name mismatch")
        description = metadata.get("description", "")
        if not description:
            skill_contract_errors.append(f"{skill_name}: empty description")
        if not SKILL_CONTRACT_PATTERNS["trigger"].search(description):
            skill_contract_errors.append(f"{skill_name}: no trigger in description")
        for field in ("input", "permission", "output", "prohibited"):
            if not SKILL_CONTRACT_PATTERNS[field].search(text):
                skill_contract_errors.append(f"{skill_name}: no {field} contract anchor")
    ledger.record(
        "skill static contracts",
        not skill_contract_errors,
        (
            "name, description, trigger, input, permission, output and prohibition anchors found"
            if not skill_contract_errors
            else " | ".join(skill_contract_errors)
        ),
    )

    strict_text_files = [
        path
        for path in text_files
        if AGENTS_ROOT in path.parents or CODEX_ROOT in path.parents
    ]
    forbidden_tokens = (
        "." + "claude",
        "CLAUDE" + ".md",
        "AskUser" + "Question",
        ".Codex" + "/project.json",
        "Bash" + "|PowerShell",
    )
    forbidden_hits: list[str] = []
    for path in strict_text_files:
        text = read_utf8(path)
        for token in forbidden_tokens:
            if token.lower() in text.lower():
                forbidden_hits.append(
                    f"{path.relative_to(REPO_ROOT).as_posix()}:{token}"
                )

    active_markdown_files = [
        AGENTS_PATH,
        MEMORY_ROOT / "README.md",
        MEMORY_ROOT / "00_WORKING_RULES.md",
        MEMORY_ROOT / "00_작업규약_한글판.md",
        MEMORY_ROOT / "02_핸드오프_규약.md",
        MEMORY_ROOT / "03_실험착수_절차.md",
        MEMORY_ROOT / "06_Codex용_프로젝트지침과_메모리.md",
        MEMORY_ROOT / "07_Codex_작업지시_권장.md",
        VALIDATION_REPORT,
    ]
    active_markdown_files.extend(
        path for path in agents_files if path.suffix.lower() == ".md"
    )
    for path in active_markdown_files:
        text = FENCED_CODE_RE.sub("", read_utf8(path))
        for target in markdown_targets(text):
            normalized = unquote(target).replace("\\", "/").lower()
            if "." + "claude" in normalized or "claude" + ".md" in normalized:
                forbidden_hits.append(
                    f"{path.relative_to(REPO_ROOT).as_posix()}:runtime-link:{target}"
                )
                continue
            local_target = target.split("#", 1)[0].split("?", 1)[0]
            if not local_target or local_target.lower().startswith(("http://", "https://")):
                continue
            resolved = (path.parent / local_target).resolve()
            if (
                resolved.parent == REPO_ROOT / "ai_dev_tool"
                and re.match(r"^0[0-8](?:_|\.)", resolved.name)
            ):
                forbidden_hits.append(
                    f"{path.relative_to(REPO_ROOT).as_posix()}:root-memory-link:{target}"
                )
    ledger.record(
        "no forbidden runtime dependency",
        not forbidden_hits,
        "0 hits" if not forbidden_hits else " | ".join(forbidden_hits),
    )

    historical_files = [
        MEMORY_ROOT / "01_계측함정_원장.md",
        MEMORY_ROOT / "04_의사결정함정_원장.md",
        MEMORY_ROOT / "05_폐기된_규약_원장.md",
        MEMORY_ROOT / "08_AI-미보고-내역-자백원장.md",
    ]
    historical_errors: list[str] = []
    for path in historical_files:
        text = read_utf8(path)
        if "Claude" in text:
            preamble = "\n".join(text.splitlines()[:20])
            if not (
                ("역사" in preamble or "과거" in preamble)
                and ("활성" in preamble or "현재" in preamble)
            ):
                historical_errors.append(path.name)
    ledger.record(
        "historical environment mentions are marked inactive",
        not historical_errors,
        "all four ledgers have historical/inactive preambles"
        if not historical_errors
        else ", ".join(historical_errors),
    )

    markdown_files = [AGENTS_PATH, PROPOSAL, MIGRATION_MAP, VALIDATION_REPORT]
    markdown_files.extend(
        path for path in environment_files if path.suffix.lower() == ".md"
    )
    markdown_files.extend(MEMORY_ROOT.glob("0[0-8]*.md"))
    markdown_files.append(MEMORY_ROOT / "README.md")
    markdown_files = sorted(set(markdown_files))
    broken = broken_markdown_links(markdown_files)
    ledger.record(
        "Markdown relative links",
        not broken,
        f"{len(markdown_files)} files checked" if not broken else " | ".join(broken),
    )

    codex_09_copies = sorted(MEMORY_ROOT.glob("09*"))
    ledger.record(
        "no Codex 09 copy",
        not codex_09_copies,
        "0 files" if not codex_09_copies else relative_list(codex_09_copies),
    )
    current_root09 = sha256(ROOT_09)
    expected_root09 = args.root09_sha256.upper()
    ledger.record(
        "shared root 09 invariant",
        current_root09 == expected_root09,
        f"sha256={current_root09}",
    )

    agents_text = read_utf8(AGENTS_PATH)
    agents_size = AGENTS_PATH.stat().st_size
    safety_anchors = (
        "datasets/TinyDataset/**",
        "run_smoke_check.bat",
        "git add .",
        "ai_dev_tool/Codex/README.md",
        "ai_dev_tool/09_구현검증_필요목록.md",
        "." + "claude/**",
        "wip-ledger",
        "session-handoff",
        "E2E_NOT_RUN",
    )
    missing_anchors = [anchor for anchor in safety_anchors if anchor not in agents_text]
    ledger.record(
        "AGENTS size and safety anchors",
        agents_size <= 16 * 1024 and not missing_anchors,
        f"bytes={agents_size}; missing={missing_anchors or 'none'}",
    )
    hardcoded_handoff = re.search(r"handoff[/\\]\d{12}_HANDOFF\.md", agents_text)
    ledger.record(
        "AGENTS has no hardcoded current handoff",
        hardcoded_handoff is None,
        "dynamic selection rule retained"
        if hardcoded_handoff is None
        else hardcoded_handoff.group(0),
    )

    migration_text = read_utf8(MIGRATION_MAP)
    covered: set[int] = set()
    for line in migration_text.splitlines():
        match = re.match(r"^\|\s*(\d+)(?:~(\d+))?\s*\|", line)
        if not match:
            continue
        start = int(match.group(1))
        end = int(match.group(2) or start)
        if 1 <= start <= end <= 890:
            covered.update(range(start, end + 1))
    missing_lines = sorted(set(range(1, 891)) - covered)
    longest_missing_run = 0
    current_missing_run = 0
    for line_number in range(1, 891):
        if line_number in covered:
            current_missing_run = 0
        else:
            current_missing_run += 1
            longest_missing_run = max(longest_missing_run, current_missing_run)
    coverage_ok = (
        1 in covered
        and 890 in covered
        and len(missing_lines) <= 30
        and longest_missing_run <= 5
    )
    ledger.record(
        "legacy AGENTS migration coverage",
        coverage_ok,
        (
            f"mapped={len(covered)}/890; structural gaps={len(missing_lines)}; "
            f"longest gap={longest_missing_run}"
        ),
    )

    def check_hook_contract() -> tuple[bool, str]:
        hooks = json.loads(read_utf8(CODEX_ROOT / "hooks.json"))
        config_text = read_utf8(CODEX_ROOT / "config.toml")
        if re.search(r"(?m)^\s*\[+hooks", config_text):
            return False, "inline hook declaration duplicates hooks.json"
        event_map = hooks.get("hooks")
        if not isinstance(event_map, dict) or set(event_map) != {"PreToolUse"}:
            return False, "hooks.json must have only PreToolUse"
        groups = event_map["PreToolUse"]
        if not isinstance(groups, list) or len(groups) != 1:
            return False, "PreToolUse must have one group"
        group = groups[0]
        if group.get("matcher") != "^Bash$":
            return False, "canonical shell matcher is not exact"
        commands = group.get("hooks")
        if not isinstance(commands, list) or len(commands) != 1:
            return False, "PreToolUse must have one command hook"
        command_hook = commands[0]
        if command_hook.get("type") != "command":
            return False, "hook type is not command"
        command = command_hook.get("command")
        if not isinstance(command, str) or "guard_backslash.py" not in command:
            return False, "command does not resolve the independent guard"
        if re.search(r"(?i)\b[A-Z]:[\\/]", command):
            return False, "command contains an absolute drive path"

        windows_command = command_hook.get("commandWindows")
        if not isinstance(windows_command, str):
            return False, "commandWindows is missing"
        if re.search(r"(?i)\b[A-Z]:[\\/]", windows_command):
            return False, "commandWindows contains an absolute drive path"
        if '"' in windows_command:
            return False, "commandWindows can be broken by Codex cmd /C outer quoting"
        if not windows_command.startswith("cmd.exe /d /q /c powershell.exe "):
            return False, "commandWindows lacks the quote-free nested cmd entrypoint"
        root_expression = (
            "-Command . (Join-Path (git rev-parse --show-toplevel) "
            "'.codex/hooks/guard_backslash_windows.ps1')"
        )
        if not windows_command.endswith(root_expression):
            return False, "commandWindows does not resolve the wrapper from the Git root"

        wrapper_text = read_utf8(
            CODEX_ROOT / "hooks" / "guard_backslash_windows.ps1"
        )
        wrapper_required = (
            "guard_backslash.py",
            "$PSScriptRoot",
            "[Console]::In.ReadToEnd()",
            "systemMessage",
        )
        wrapper_missing = [
            item for item in wrapper_required if item not in wrapper_text
        ]
        if wrapper_missing:
            return False, f"Windows wrapper missing contract keys {wrapper_missing}"
        guard_text = read_utf8(CODEX_ROOT / "hooks" / "guard_backslash.py")
        required = (
            "hookSpecificOutput",
            "permissionDecision",
            "permissionDecisionReason",
            "systemMessage",
            "tool_input",
        )
        missing = [item for item in required if item not in guard_text]
        if missing:
            return False, f"guard missing output/input keys {missing}"
        return True, (
            "single hooks.json source, canonical matcher, quote-free Windows wrapper, "
            "portable commands and structured deny"
        )

    ledger.guarded("Codex hook contract", check_hook_contract)

    completed = subprocess.run(
        [
            sys.executable,
            "-I",
            "-B",
            str(CODEX_ROOT / "hooks" / "test_guard_backslash.py"),
        ],
        cwd=REPO_ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    hook_test_detail = (
        "16 hook tests passed"
        if completed.returncode == 0
        else (completed.stderr or completed.stdout).strip()
    )
    ledger.record("Codex hook mock suite", completed.returncode == 0, hook_test_detail)

    handoff_skill = read_utf8(
        AGENTS_ROOT / "skills" / "session-handoff" / "SKILL.md"
    )
    wip_skill = read_utf8(AGENTS_ROOT / "skills" / "wip-ledger" / "SKILL.md")
    codex_handoff_checker = (
        AGENTS_ROOT
        / "skills"
        / "session-handoff"
        / "scripts"
        / "check_handoff_codex.py"
    )
    ledger.record(
        "handoff and WIP ownership contract",
        (
            "scripts/new_handoff.py" in handoff_skill
            and "Codex 02" in handoff_skill
            and codex_handoff_checker.is_file()
            and "python -I -B .agents/skills/session-handoff/scripts/check_handoff_codex.py"
            in handoff_skill
            and "python scripts/check_handoff.py" not in handoff_skill
            and "09" in wip_skill
            and "복사" in wip_skill
            and "이관" in wip_skill
        ),
        "TinyLM generator, independent Codex checker, Codex 02 and root 09 exception",
    )

    status = subprocess.run(
        [
            "git",
            "status",
            "--short",
            "--",
            "AGENTS.md",
            ".agents",
            ".codex",
            "ai_dev_tool/Codex",
            "proposal/done/20260911_Codex-작업환경-완전분리-구축-approved.md",
        ],
        cwd=REPO_ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    ledger.record(
        "scoped worktree inspection",
        status.returncode == 0,
        (
            f"named environment paths only; entries={len(status.stdout.splitlines())}"
            if status.returncode == 0
            else status.stderr.strip()
        ),
    )

    return ledger.emit()


if __name__ == "__main__":
    raise SystemExit(main())
