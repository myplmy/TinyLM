"""User-selected inference contracts; no model/GPU loading or asset discovery."""
from __future__ import annotations

from dataclasses import dataclass
import copy
import hashlib
from pathlib import Path
import re
from tinylm.chat.serialize import serialize


def file_sha(path):
    digest=hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b""):digest.update(chunk)
    return digest.hexdigest().upper()


def selected_metadata(state):
    if not isinstance(state,dict) or not isinstance(state.get("cfg"),dict):
        raise ValueError("선택한 체크포인트에 저장 cfg가 없습니다.")
    settings=dict(state["cfg"])
    if type(settings.get("vocab_size")) is not int or settings["vocab_size"]<2:
        raise ValueError("저장 cfg의 어휘 크기가 올바르지 않습니다.")
    if type(settings.get("tie_mlp")) is not bool:
        raise ValueError("저장 cfg의 MLP 공유 여부가 없어 구조를 추정하지 않습니다.")
    return dict(cfg=settings,arch="tied" if settings["tie_mlp"] else "dense",
        tokenizer_sha256=state.get("tokenizer_sha256"),
        chat_family=state.get("chat_family"),step=state.get("step"),epoch=state.get("epoch"))


@dataclass(frozen=True)
class TokenizerRoute:
    path:Path
    sha256:str
    verified:bool
    reason:str


def resolve_tokenizer(record,metadata,cache_dir,explicit=None):
    """Match saved tokenizer SHA to two exact local candidates, never a download."""
    expected=metadata.get("tokenizer_sha256")
    if expected is not None:
        if not isinstance(expected,str) or re.fullmatch(r"[0-9a-fA-F]{64}",expected) is None:
            raise ValueError("저장된 tokenizer SHA 형식이 올바르지 않습니다.")
        expected=expected.upper()
    data=record.data
    if explicit is not None:candidates=[Path(explicit)]
    else:
        if not re.fullmatch(r"[A-Za-z0-9-]+",data or ""):
            raise ValueError("data를 확인할 수 없습니다. --tokenizer로 정확한 JSON을 지정하세요.")
        size=metadata["cfg"]["vocab_size"];root=Path(cache_dir)
        candidates=[root/f"tok-{data}-{size}.json",root/f"tok-{data}-{size}-chat32.json"]
    present=[(p,file_sha(p)) for p in candidates if p.is_file()]
    if expected:
        matches=[(p,h) for p,h in present if h==expected]
        if not matches:raise ValueError("학습 tokenizer SHA와 같은 로컬 JSON이 없습니다. --tokenizer를 확인하세요.")
        path,identity=matches[0]
        return TokenizerRoute(path.resolve(),identity,True,"CHECKPOINT_SHA_MATCH")
    if explicit is not None:
        if not present:raise ValueError("지정한 tokenizer JSON이 없습니다.")
        path,identity=present[0]
        return TokenizerRoute(path.resolve(),identity,False,"EXPLICIT_WITHOUT_SAVED_SHA")
    family=metadata.get("chat_family")
    if family not in (None,"legacy32","chat32"):
        raise ValueError("미지원 chat_family입니다. --tokenizer로 정확한 JSON을 지정하세요.")
    desired=candidates[1] if family=="chat32" else candidates[0]
    match=next(((p,h) for p,h in present if p==desired),None)
    if match is None:raise ValueError("기존 규약의 tokenizer JSON이 없습니다. --tokenizer를 명시하세요.")
    if family is None and "chat32" in record.stem.lower():
        raise ValueError("chat32처럼 보이는 이름만으로 어휘를 추정하지 않습니다. --tokenizer를 명시하세요.")
    return TokenizerRoute(match[0].resolve(),match[1],False,"LEGACY_OR_DECLARED_CONVENTION_WITHOUT_SAVED_SHA")


def validate_vocabulary(tokenizer,cfg,*,allow_extra_special=False):
    """An opt-in text-only contract, never resize or remap the tokenizer.

    Some HF text models omit a newly added image marker from their output
    matrix. Permit only a complete unchanged base vocabulary plus individually
    declared special IDs beyond that matrix. Encoding still needs a range
    check at the actual model boundary.
    """
    size=cfg["vocab_size"];full_size=tokenizer.get_vocab_size()
    if type(size) is not int or size<2 or type(full_size) is not int:
        raise ValueError("어휘 크기는 유효한 정수여야 합니다.")
    if full_size==size and not allow_extra_special:
        return dict(policy="EXACT_VOCAB_SIZE",model_vocab_size=size,
                    tokenizer_vocab_size=full_size,extra_special_tokens={})
    if not allow_extra_special:
        raise ValueError(f"체크포인트와 tokenizer 어휘 크기가 다릅니다: 모델={size}, tokenizer={full_size}. "
                         "추가 특수 토큰만 있는 경우에도 명시 허용과 입력 범위 검사가 필요합니다.")
    if tokenizer.get_vocab_size(with_added_tokens=False)!=size:
        raise ValueError("추가 특수 토큰 허용은 기본 어휘가 모델과 정확히 같은 경우에만 가능합니다.")
    base=tokenizer.get_vocab(with_added_tokens=False);full=tokenizer.get_vocab()
    if (len(base)!=size or len(full)!=full_size or set(base.values())!=set(range(size))
            or any(type(value) is not int for value in full.values())
            or len(set(full.values()))!=full_size
            or any(full.get(token)!=ident for token,ident in base.items())
            or any(ident<size and base.get(token)!=ident for token,ident in full.items())):
        raise ValueError("기존 토큰의 ID 변경·중복·빈 구간 또는 다른 기본 어휘를 허용하지 않습니다.")
    extra={token:ident for token,ident in full.items() if ident>=size}
    if not extra and full_size==size:
        return dict(policy="EXACT_VOCAB_SIZE",model_vocab_size=size,
                    tokenizer_vocab_size=full_size,extra_special_tokens={})
    added=tokenizer.get_added_tokens_decoder()
    if not extra or any(ident not in added or not added[ident].special
                        or added[ident].content!=token for token,ident in extra.items()):
        raise ValueError("모델 범위를 벗어난 ID는 모두 명시된 추가 특수 토큰이어야 합니다.")
    return dict(policy="EXPLICIT_EXTRA_SPECIAL_TEXT_ONLY",model_vocab_size=size,
                tokenizer_vocab_size=full_size,base_ids_unchanged=True,
                extra_special_tokens=extra,input_range_check_required=True,
                historical_training_identity="SEPARATE_FROM_VOCAB_RANGE_COMPATIBILITY")


def validate_input_ids(ids,vocab_size):
    if not ids or any(type(ident) is not int or not 0<=ident<vocab_size for ident in ids):
        raise ValueError("입력에 모델 어휘 범위 밖 토큰 ID가 있습니다. 추가 이미지/특수 토큰은 이 텍스트 모델에서 지원하지 않습니다.")


def resolve_mode(tokenizer,cfg,requested="auto",*,allow_extra_special=False):
    validate_vocabulary(tokenizer,cfg,allow_extra_special=allow_extra_special)
    markers=[tokenizer.token_to_id(name) for name in ("<|im_start|>","<|im_end|>")]
    available=all(type(v) is int and 0<=v<cfg["vocab_size"] for v in markers) and markers[0]!=markers[1]
    mode=("chatml" if available else "plain") if requested=="auto" else requested
    if mode not in ("chatml","plain"):raise ValueError("auto/chatml/plain 모드만 지원합니다.")
    if mode=="chatml" and not available:raise ValueError("이 tokenizer에는 단일 ChatML 경계 토큰이 없습니다.")
    return mode,([markers[1]] if mode=="chatml" else [])


def make_prompt(question,mode,history=()):
    if not isinstance(question,str) or not question.strip():raise ValueError("빈 질문은 생성하지 않습니다.")
    if mode=="plain":
        if history:raise ValueError("plain 이어쓰기에는 자동 대화 이력을 붙이지 않습니다.")
        return question
    if mode!="chatml":raise ValueError("명시된 입력 모드가 필요합니다.")
    messages=copy.deepcopy(list(history))
    messages.append(dict(role="user",content=[dict(type="text",text=question)]))
    return serialize(dict(messages=messages),"chatml",add_generation_prompt=True)


def answer_from_ids(tokenizer,prompt_ids,all_ids,generated_count):
    if (not isinstance(all_ids,list) or all_ids[:len(prompt_ids)]!=list(prompt_ids)
            or type(generated_count) is not int or len(all_ids)-len(prompt_ids)!=generated_count):
        raise ValueError("실제 생성 토큰과 입력 경계/계측이 일치하지 않습니다.")
    return tokenizer.decode(all_ids[len(prompt_ids):],skip_special_tokens=True)


def add_turn(history,question,answer):
    result=copy.deepcopy(list(history))
    result.extend([dict(role=role,content=[dict(type="text",text=text)])
        for role,text in (("user",question),("assistant",answer))])
    return result
