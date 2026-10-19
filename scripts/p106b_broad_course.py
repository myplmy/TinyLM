"""Pure broad-course preparation: immutable update groups, two order policies.

Callers supply already read/pinned sources and the tokenizer. This module does
no file I/O, model loading, CUDA work, acquisition or source mutation. Public
metadata is separate from encoded records. Source insufficiency is not a failed
student experiment. Native windows belong to absolute updates, not group IDs.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import copy
import hashlib
import json
from pathlib import Path
import random
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tinylm.chat.canonical import normalize, validate
from tinylm.data.sft import conversation_split_key
from tinylm.train import mtp_sft as core
from scripts import p106b_night_learning as paired
from scripts import p106b_night_qa_data as natural
from scripts import p106b_relation_fields as fields

VERSION = 'P106B_BROAD_COURSE_ORDER_V1'
SELECTION_KEY = 'p106b_broad_curriculum_v1_s1337'
ARMS = ('mixed', 'staged')
CONTEXT, EOT, VOCAB = 1024, 4, 32768
SYNTHETIC_KINDS = frozenset((
    'fictional_relation_fields', 'role_bridge', 'evidence_recovery',
    'arithmetic', 'binding_color', 'binding_department', 'boolean', 'json', 'update'))
CONCEPT_FIELDS = ('root', 'semantic_root_id', 'parent_concept_id',
                  'source_group_id', 'neutral_root', 'group_id', 'parent_group_id')
PROVENANCE_FIELDS = ('source', 'source_repo', 'source_id', 'source_revision',
                     'source_license', 'source_path', 'source_sha256', 'source_split',
                     'source_original_split', 'original_split', 'qa_id')


@dataclass(frozen=True)
class _Geometry:
    """Production defaults are fixed; smaller values are for private fixtures."""
    natural_pairs: int = 8192
    replay_rows: int = 4096
    general_rows: int = 2048
    group_rows: int = 128
    micro_rows: int = 8
    passes: int = 2

    def __post_init__(self):
        values = tuple(self.__dict__.values())
        if (any(type(v) is not int or v < 1 for v in values)
                or self.passes != 2 or self.group_rows % self.micro_rows
                or self.group_rows % 2
                or any(n % self.group_rows for n in
                       (2 * self.natural_pairs, self.replay_rows, self.general_rows))):
            raise ValueError('whole paired rows/groups/micros and exactly two passes required')


@dataclass(frozen=True)
class BroadCourse:
    records: list
    rows: list[dict]
    groups: list[list[int]]
    schedules: dict[str, list[list[int]]]
    report: dict


class SourceUnavailable(ValueError):
    """Keep an inspectable source-admission report before any student execution."""
    def __init__(self, report):
        self.report = copy.deepcopy(report)
        super().__init__('SOURCE_UNAVAILABLE: ' + str(report.get('reason', report.get('status'))))


def sha(value):
    body = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)
    return hashlib.sha256(body.encode('utf-8')).hexdigest().upper()


def _text(message):
    content = message['content']
    if isinstance(content, str):
        return content
    if not isinstance(content, list) or any(
            not isinstance(block, dict) or block.get('type') != 'text'
            or not isinstance(block.get('text'), str) for block in content):
        raise ValueError('text-only original messages required')
    return ''.join(block['text'] for block in content)


def _canonical(row, *, complete=True):
    value = validate(normalize(copy.deepcopy(row)))
    for message in value['messages']:
        _text(message)
    if not any(m['role'] == 'user' for m in value['messages']):
        raise ValueError('original user turn required')
    if complete and value['messages'][-1]['role'] != 'assistant':
        raise ValueError('complete final assistant turn required')
    return value


def _normalized(value):
    return ' '.join(unicodedata.normalize('NFKC', value).casefold().split())


def _word24(text):
    words = _normalized(text).split()
    return {sha(words[i:i + 24]) for i in range(max(0, len(words) - 23))}


def _original_texts(row):
    meta = row['meta']
    if meta.get('kind') in SYNTHETIC_KINDS or meta.get('_broad_synthetic_reference') is True:
        return []  # Shared code templates are not original-world-source overlap.
    explicit = [meta[k] for k in ('context_original', 'source_reference', 'reference_text')
                if isinstance(meta.get(k), str) and meta[k]]
    return list(dict.fromkeys(explicit)) if explicit else [_text(m) for m in row['messages']]


def _identity(row):
    meta = row['meta']
    concepts = {str(meta[k]) for k in CONCEPT_FIELDS
                if isinstance(meta.get(k), (str, int)) and not isinstance(meta[k], bool)}
    source = meta.get('source_repo') or meta.get('source') or meta.get('source_path')
    source_id = meta.get('source_id', meta.get('qa_id'))
    sources = ({sha([source, str(source_id)])} if source and source_id is not None else set())
    split_roots = {'concept:' + key for key in concepts}
    split_roots.update(kind + ':' + str(meta[kind + '_id']) for kind in ('article', 'context')
                       if meta.get(kind + '_id') is not None)
    originals = _original_texts(row)
    grams = set()
    for text in originals:
        grams.update(_word24(text))
    return dict(messages={sha(row['messages'])}, first_user={conversation_split_key(row).hex().upper()},
                source_id=sources, concept={'concept:' + key for key in concepts},
                split_root=split_roots, word24=grams,
                original_text_sha256=[sha(text) for text in originals])


def _references(values):
    """Accept canonical rows, prompt-only eval cases, or natural paired views."""
    for value in values:
        if isinstance(value, dict) and 'messages' in value:
            row = _canonical(value, complete=False)
            for key in (*CONCEPT_FIELDS, *PROVENANCE_FIELDS, 'article_id', 'context_id', 'language'):
                if key in value and key not in row['meta']:
                    row['meta'][key] = copy.deepcopy(value[key])
            if value.get('lane') in ('coded', 'canary'):
                row['meta']['_broad_synthetic_reference'] = True
            yield row
        elif isinstance(value, dict) and isinstance(value.get('views'), dict):
            for key in sorted(value['views']):
                yield _canonical(value['views'][key], complete=False)
        else:
            raise ValueError('canonical reference row or natural pair with views required')


class _Index:
    def __init__(self):
        self.values = {key: defaultdict(set) for key in
                       ('messages', 'first_user', 'source_id', 'concept', 'split_root', 'word24')}

    def add(self, identity, origin, *, split=True, grams=True):
        for kind, table in self.values.items():
            if kind == 'split_root' and not split or kind == 'word24' and not grams:
                continue
            for key in identity[kind]:
                table[key].add(origin)

    def collisions(self, identity, *, split=True, grams=True):
        result = {}
        for kind, table in self.values.items():
            if kind == 'split_root' and not split or kind == 'word24' and not grams:
                continue
            hits = set()
            matched = 0
            for key in identity[kind]:
                if key in table:
                    matched += 1
                    hits.update(table[key])
            if hits:
                result[kind] = dict(matched_keys=matched, origin_count=len(hits), origins=sorted(hits)[:8])
        return result


def _protected(public_val, heldout_rows, monitor_rows):
    index, counts = _Index(), Counter()
    for label, values in (('public_val', public_val), ('heldout', heldout_rows), ('monitor', monitor_rows)):
        for row in _references(values):
            identity = _identity(row)
            index.add(identity, label + ':' + next(iter(identity['messages'])))
            counts[label] += 1
    return index, dict(counts)


def _record_counts(record):
    if (not isinstance(record, core.Record) or not 1 <= len(record.x) <= CONTEXT
            or len(record.y) != len(record.x) or len(record.segments) != len(record.x)
            or any(type(v) is not int or not 0 <= v < VOCAB for v in record.x)
            or any(type(v) is not int or (v != -100 and not 0 <= v < VOCAB) for v in record.y)
            or any(type(v) is not int or v < 0 for v in record.segments)
            or any(y != -100 and s == 0 for y, s in zip(record.y, record.segments))):
        raise ValueError('complete1024 vocabulary/target/owner record required')
    turns = defaultdict(Counter)
    for target, owner in zip(record.y, record.segments):
        if target != -100 and owner > 0:
            turns[owner].update(targets=1, content=int(target != EOT), eot=int(target == EOT))
    targets = sum(value['targets'] for value in turns.values())
    if targets == 0:
        raise ValueError('positive assistant supervision required')
    return dict(x_tokens=len(record.x), assistant_targets=targets,
                content_targets=sum(v['content'] for v in turns.values()),
                eot_targets=sum(v['eot'] for v in turns.values()),
                supervised_turns=len(turns), masked_positive_owner_tokens=sum(
                    y == -100 and s > 0 for y, s in zip(record.y, record.segments)),
                turns=[dict(turn=key, **dict(value)) for key, value in sorted(turns.items())])


def _record_sha(record):
    return sha(dict(x=record.x, y=record.y, segments=record.segments))


def _metadata(row, record, lane, source_index, *, variant=None):
    identity = _identity(row)
    provenance = {k: copy.deepcopy(row['meta'][k]) for k in PROVENANCE_FIELDS if k in row['meta']}
    root = row['meta'].get('neutral_root') or row['meta'].get('semantic_root_id') or row['meta'].get('root')
    root = str(root) if root is not None else sha([sorted(identity['source_id']), sorted(identity['first_user'])])
    record_sha = _record_sha(record)
    return dict(id=sha([VERSION, lane, sha(row), variant, record_sha]), lane=lane,
        language=row['meta']['language'], source_index=source_index, source_index_base=0,
        variant=variant, root=root, source=provenance, messages_sha256=next(iter(identity['messages'])),
        first_user_sha256=next(iter(identity['first_user'])),
        source_identity_sha256=sha(sorted(identity['source_id'])), root_aliases=sorted(identity['concept']),
        original_text_sha256=identity['original_text_sha256'], word24_sha256=sha(sorted(identity['word24'])),
        record_sha256=record_sha, assistant_turns=sum(m['role'] == 'assistant' for m in row['messages']),
        **_record_counts(record))


def _select_general(public_train, tok, *, public_val, heldout_rows, monitor_rows,
                    training_rows, selection_key, goal):
    blocked, protected_counts = _protected(public_val, heldout_rows, monitor_rows)
    used = _Index()
    for row in _references(training_rows):
        identity = _identity(row)
        used.add(identity, 'existing_train:' + next(iter(identity['messages'])), split=False, grams=False)
    incoming, rejected, details, candidates = Counter(), Counter(), [], []
    for index, original in enumerate(public_train):
        raw_meta = original.get('meta') if isinstance(original, dict) else None
        raw_meta = raw_meta if isinstance(raw_meta, dict) else {}
        incoming[str(raw_meta.get('language', 'MISSING'))] += 1
        reason, collision = None, None
        try:
            row = _canonical(original)
            meta = row['meta']
            if meta.get('language') not in ('ko', 'en'):
                reason = 'unregistered_language'
            elif not all(isinstance(meta.get(k), str) and meta[k] for k in
                         ('source', 'source_id', 'source_revision', 'source_license')):
                reason = 'missing_original_source_metadata'
            elif any(meta.get(k, 'train') != 'train' for k in ('original_split', 'source_split')):
                reason = 'not_original_train_split'
            identity = _identity(row)
            if reason is None:
                collision = blocked.collisions(identity)
                if collision:
                    reason = 'reserved_evaluation_collision'
                    # A source variant may expose another alias of the reserved
                    # concept. Keep that alias even though this row is excluded.
                    used.add(identity, 'reserved_general_alias:' + str(index), split=False, grams=False)
            if reason is None:
                record = core.encode_record(row, tok, context=CONTEXT)
                _record_counts(record)
                rank = sha([selection_key, sorted(identity['source_id']),
                            sorted(identity['first_user']), next(iter(identity['messages']))])
                candidates.append((0 if meta['language'] == 'ko' else 1, rank, index, row, record, identity))
        except (ValueError, TypeError, KeyError) as exc:
            reason = 'length_or_encoding_contract' if 'context' in str(exc).lower() else 'canonical_or_metadata_contract'
        if reason is not None:
            rejected[reason] += 1
            details.append(dict(source_index=index, language=raw_meta.get('language'), reason=reason,
                                collision=collision))
    # Resolve alias chains before choosing a representative, so input/hash order
    # cannot select two rows from A--same source ID--B--same first user--C.
    parents, owners = list(range(len(candidates))), {}
    def find(index):
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index
    for index, candidate in enumerate(candidates):
        identity = candidate[5]
        for kind in ('messages', 'first_user', 'source_id', 'concept'):
            for key in identity[kind]:
                alias = (kind, key)
                if alias in owners:
                    parents[find(index)] = find(owners[alias])
                else:
                    owners[alias] = index
    components = defaultdict(list)
    for index, candidate in enumerate(candidates):
        components[find(index)].append(candidate)
    eligible = []
    representatives = []
    for component in components.values():
        component.sort(key=lambda v: (v[0], v[1], v[2]))
        collision = {}
        for candidate in component:
            collision.update(used.collisions(candidate[5], split=False, grams=False))
        if collision:
            discarded = component
        else:
            representatives.append(component[0])
            discarded = component[1:]
        for _, rank, index, row, record, identity in discarded:
            rejected['same_concept_or_exact_conversation'] += 1
            details.append(dict(source_index=index, language=row['meta']['language'],
                reason='same_concept_or_exact_conversation', collision=collision or
                dict(component_representative_source_index=component[0][2])))
    for _, rank, index, row, record, identity in sorted(representatives, key=lambda v: (v[0], v[1], v[2])):
        eligible.append((index, row, record))
    selected = eligible[:goal]  # KO first; EN fills only the remaining unique supply.
    metadata = [_metadata(row, record, 'general', index) for index, row, record in selected]
    available = Counter(row['meta']['language'] for _, row, _ in eligible)
    report = dict(schema=VERSION, status='ADMISSIBLE' if len(selected) == goal else 'SOURCE_UNAVAILABLE',
        reason=None if len(selected) == goal else 'insufficient_unique_eligible_general_train',
        requested_general_rows=goal, input_rows=sum(incoming.values()), input_language_rows=dict(incoming),
        eligible_unique_rows=len(eligible), eligible_language_rows=dict(available),
        selected_rows=len(selected), selected_language_rows=dict(Counter(m['language'] for m in metadata)),
        selected_source_indices=[m['source_index'] for m in metadata], selected_ids_sha256=sha([m['id'] for m in metadata]),
        selected_sources=[dict(source_index=m['source_index'], id=m['id'], root=m['root'],
                               source=m['source'], messages_sha256=m['messages_sha256']) for m in metadata],
        rejected=dict(rejected), exclusions=details, protected_reference_rows=protected_counts,
        selection_key=selection_key, selection='all eligible unique KO first; hash-ranked EN remainder',
        source_split_basis='caller-supplied original public TRAIN plus any explicit row split',
        duplicate_policy='source identity/concept alias/exact messages/normalized first user; not answer similarity',
        word24_scope='original natural context or general messages; shared synthetic templates excluded',
        language_or_knowledge_quality_string_filters=0, repeated_fill_rows=0, model_loaded=False)
    return selected, report, blocked


def inspect_general(public_train, tok, *, public_val, heldout_rows, monitor_rows=(),
                    training_rows=(), selection_key=SELECTION_KEY):
    """Return source admission/exclusions even when the fixed2048 cannot be met."""
    if tok.token_to_id('<|im_end|>') != EOT:
        raise ValueError('pinned chat32 EOT4 required')
    _, report, _ = _select_general(public_train, tok, public_val=public_val,
        heldout_rows=heldout_rows, monitor_rows=monitor_rows, training_rows=training_rows,
        selection_key=selection_key, goal=2048)
    return report


def _aggregate(metadata):
    cells, sources, turns = defaultdict(Counter), Counter(), defaultdict(Counter)
    for row in metadata:
        key = (row['lane'], row['language'])
        cells[key].update(rows=1, assistant_turns=row['assistant_turns'], **{
            k: row[k] for k in ('x_tokens', 'assistant_targets', 'content_targets',
                               'eot_targets', 'supervised_turns', 'masked_positive_owner_tokens')})
        sources[(row['lane'], row['source'].get('source', row['source'].get('source_path', 'CODE_PRODUCER')))] += 1
        for turn in row['turns']:
            turns[(row['lane'], row['language'], turn['turn'])].update(
                targets=turn['targets'], content=turn['content'], eot=turn['eot'])
    totals = Counter()
    for value in cells.values():
        totals.update(value)
    return dict(totals=dict(totals), lane_language=[dict(lane=k[0], language=k[1], **dict(v))
        for k, v in sorted(cells.items())], source_rows=[dict(lane=k[0], source=k[1], rows=v)
        for k, v in sorted(sources.items())], turn_targets=[dict(lane=k[0], language=k[1], turn=k[2], **dict(v))
        for k, v in sorted(turns.items())])


def _build_course(natural_pairs, replay_rows, public_train, tok, *, public_val,
                  heldout_rows, monitor_rows=(), selection_key=SELECTION_KEY, geometry=None):
    geometry = _Geometry() if geometry is None else geometry
    if not isinstance(geometry, _Geometry) or tok.token_to_id('<|im_end|>') != EOT:
        raise ValueError('declared geometry and chat32 EOT4 required')
    pairs, replay, public_train = list(natural_pairs), list(replay_rows), list(public_train)
    if len(pairs) != geometry.natural_pairs or len(replay) != geometry.replay_rows:
        raise SourceUnavailable(dict(status='SOURCE_UNAVAILABLE', reason='fixed_source_counts_differ',
            natural_pairs=len(pairs), replay_rows=len(replay), expected=geometry.__dict__))
    training = [view for pair in pairs for view in pair.get('views', {}).values()] + replay
    selected, admission, blocked = _select_general(public_train, tok, public_val=public_val,
        heldout_rows=heldout_rows, monitor_rows=monitor_rows, training_rows=training,
        selection_key=selection_key, goal=geometry.general_rows)
    if admission['status'] != 'ADMISSIBLE':
        raise SourceUnavailable(admission)
    records, metadata, conflicts, seen_roots = [], [], [], set()
    for source_index, pair in sorted(enumerate(pairs), key=lambda v: sha([selection_key, 'PAIR', v[1].get('root')])):
        if pair.get('split') != 'train' or pair.get('language') not in ('ko', 'en'):
            raise ValueError('only supplied original TRAIN natural pairs required')
        if set(pair.get('views', {})) != {'0', '1'} or not isinstance(pair.get('root'), str):
            raise ValueError('only the two original natural TRAIN wrappers and explicit root required')
        if pair.get('root') in seen_roots:
            raise SourceUnavailable(dict(status='SOURCE_UNAVAILABLE', reason='duplicate_natural_root'))
        seen_roots.add(pair.get('root'))
        encoded = []
        for view in (0, 1):
            row = _canonical(pair['views'][str(view)])
            if row != natural.render_view(pair, view):
                raise ValueError('original natural context/question/answer/wrapper changed')
            collision = blocked.collisions(_identity(row))
            if collision:
                conflicts.append(dict(lane='grounded', source_index=source_index, variant=view, collision=collision))
            rec = core.encode_record(row, tok, context=CONTEXT)
            _record_counts(rec)
            expected = pair['encoding'][str(view)]
            targets = [y for y in rec.y if y != -100]
            if (rec.x_tokens != expected['x_tokens'] or rec.targets != expected['assistant_targets']
                    or sha(targets) != expected['target_ids_sha256']
                    or expected.get('eot_supervised') is not True
                    or next(i for i, y in enumerate(rec.y) if y != -100) != expected['prompt_tokens'] - 1):
                raise ValueError('actual natural consumer differs from sealed encoding')
            encoded.append(rec)
            records.append(rec); metadata.append(_metadata(row, rec, 'grounded', source_index, variant=view))
        paired.paired_positions(encoded, EOT)
    for source_index, original in sorted(enumerate(replay), key=lambda v: sha([selection_key, 'REPLAY', v[1]])):
        row = _canonical(original)
        if row['meta'].get('language') not in ('ko', 'en') or row['meta'].get('source_split', 'train') != 'train':
            raise ValueError('original bilingual TRAIN replay required')
        collision = blocked.collisions(_identity(row))
        if collision:
            conflicts.append(dict(lane='replay', source_index=source_index, collision=collision))
        rec, _ = fields.encode(row, tok)  # Critical: masks C2's old wrong answer.
        records.append(rec); metadata.append(_metadata(row, rec, 'replay', source_index))
    if conflicts:
        raise SourceUnavailable(dict(status='SOURCE_UNAVAILABLE', reason='fixed_training_reserved_evaluation_collision',
                                     conflicts=conflicts, general_admission=admission))
    for source_index, row, rec in sorted(selected, key=lambda v: sha([selection_key, 'GENERAL_GROUP', v[1]])):
        records.append(rec); metadata.append(_metadata(row, rec, 'general', source_index))
    if len({row['id'] for row in metadata}) != len(metadata):
        raise SourceUnavailable(dict(status='SOURCE_UNAVAILABLE', reason='duplicate_full_source_rows'))
    groups = [list(range(i, i + geometry.group_rows)) for i in range(0, len(records), geometry.group_rows)]
    descriptions, lane_groups = [], defaultdict(list)
    for index, group in enumerate(groups):
        rows = [metadata[i] for i in group]
        lanes = {r['lane'] for r in rows}
        if len(lanes) != 1 or len(group) != geometry.group_rows:
            raise ValueError('same complete lane-owned128-row update groups required')
        lane = next(iter(lanes)); lane_groups[lane].append(index)
        descriptions.append(dict(group=index, lane=lane, row_indices_sha256=sha(group),
            row_ids_sha256=sha([r['id'] for r in rows]), record_hashes_sha256=sha([r['record_sha256'] for r in rows]),
            row_metadata_sha256=sha(rows),
            **_aggregate(rows)))
    staged = lane_groups['replay'] + lane_groups['grounded'] + lane_groups['general']
    schedules = dict(mixed=[], staged=[])
    for epoch in range(geometry.passes):
        mixed = list(range(len(groups)))
        random.Random(int(sha([selection_key, 'ORDER', epoch])[:16], 16)).shuffle(mixed)
        schedules['mixed'].append(mixed); schedules['staged'].append(list(staged))
    exposure = _aggregate(metadata)
    report = dict(schema=VERSION, status='BROAD_COURSE_READY', selection_key=selection_key,
        geometry=dict(geometry.__dict__), groups_per_pass=len(groups), updates=len(groups) * geometry.passes,
        per_pass=exposure, two_pass_totals={k: v * geometry.passes for k, v in exposure['totals'].items()},
        padded_sft_slots_per_pass=len(records) * CONTEXT, groups=descriptions, schedules=schedules,
        schedules_sha256=sha(schedules), rows_metadata_sha256=sha(metadata),
        ordered_record_hashes_sha256=sha([r['record_sha256'] for r in metadata]),
        source_input_sha256=dict(natural=sha(pairs), replay=sha(replay), public_train=sha(public_train)),
        general_admission=admission, natural_unique_roots=len(seen_roots),
        original_messages_unique=len({r['messages_sha256'] for r in metadata}),
        shared_group_composition=True, same_two_views_per_pair=True, original_source_mutated=False,
        objective='L0_TOKEN_MEAN_OVER_WHOLE_UPDATE', parent_policy='SAME_FIXED_ORIGINAL_P090B',
        native_binding=dict(kind='ABSOLUTE_OPTIMIZER_UPDATE_NOT_GROUP_OR_ARM', windows_per_update=8,
                            targets_per_update=8192, total_targets=8192 * len(groups) * geometry.passes),
        source_overlap_scope='exact source/root/messages/first-user and original word24; semantic overlap not certified',
        word24_scope='original natural context/general messages; synthetic common templates excluded',
        knowledge_claim='two passes repeat the same unique source material; not twice the unique knowledge',
        source_quality='original public pseudo labels; no full semantic review',
        teacher_calls=0, mtp=False, model_loaded=False, formal_train_ready=False,
        total75m_complete=False, language_or_knowledge_quality_string_filters=0)
    return BroadCourse(records=records, rows=metadata, groups=groups, schedules=schedules, report=report)


def build_course(natural_pairs, replay_rows, public_train, tok, *, public_val,
                 heldout_rows, monitor_rows=(), selection_key=SELECTION_KEY):
    """Build fixed8192/4096/2048, 128-row, two-pass352-update production course."""
    return _build_course(natural_pairs, replay_rows, public_train, tok, public_val=public_val,
        heldout_rows=heldout_rows, monitor_rows=monitor_rows, selection_key=selection_key)


def materialize_group(course, arm, epoch, slot):
    """Return sixteen unchanged eight-record micros for the chosen group order."""
    if (not isinstance(course, BroadCourse) or arm not in ARMS or type(epoch) is not int
            or not 0 <= epoch < 2 or type(slot) is not int
            or not 0 <= slot < len(course.groups)):
        raise ValueError('registered arm/pass/group slot required')
    geometry = course.report['geometry']
    if sha(course.schedules) != course.report['schedules_sha256']:
        raise ValueError('frozen group order changed')
    group_id = course.schedules[arm][epoch][slot]
    if type(group_id) is not int or not 0 <= group_id < len(course.groups):
        raise ValueError('frozen group index differs')
    indices = course.groups[group_id]
    description = course.report['groups'][group_id]
    if (len(indices) != geometry['group_rows'] or len(set(indices)) != len(indices)
            or sha(indices) != description['row_indices_sha256']
            or sha([course.rows[i]['id'] for i in indices]) != description['row_ids_sha256']
            or sha([course.rows[i] for i in indices]) != description['row_metadata_sha256']
            or sha([_record_sha(course.records[i]) for i in indices]) != description['record_hashes_sha256']):
        raise ValueError('immutable update membership or encoded targets changed')
    width = geometry['micro_rows']
    return [[course.records[i] for i in indices[start:start + width]]
            for start in range(0, len(indices), width)]


def native_indices(absolute_update):
    if type(absolute_update) is not int or not 0 <= absolute_update < 352:
        raise ValueError('absolute optimizer update0..351 required')
    return tuple(range(absolute_update * 8, (absolute_update + 1) * 8))


def public_report(course):
    """No original messages or token arrays; root owns versioned persistence."""
    if not isinstance(course, BroadCourse):
        raise ValueError('prepared BroadCourse required')
    return copy.deepcopy(course.report)
