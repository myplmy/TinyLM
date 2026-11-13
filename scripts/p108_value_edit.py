"""ROME core adaptations: token-local value intervention and covariance write.

No model loading, disk I/O, training recipe or product defaults live here.
Only the auxiliary value tensor is optimized by the experiment driver.
"""
from contextlib import contextmanager
import math
import torch


def subject_position(encoding, start, end):
    if type(start) is not int or type(end) is not int or not 0 <= start < end:
        raise ValueError('invalid subject character span')
    hits = [i for i, (a, b) in enumerate(encoding.offsets) if b > a and a < end and b > start]
    if not hits or encoding.offsets[hits[0]][0] > start or encoding.offsets[hits[-1]][1] < end:
        raise ValueError('token offsets do not cover subject')
    return hits[-1]


def target_window(prompt_ids, answer_ids, terminal=4):
    if not prompt_ids or not answer_ids or type(terminal) is not int:
        raise ValueError('nonempty prefix and answer required')
    target = list(answer_ids) + [terminal]
    return list(prompt_ids) + target[:-1], target, len(prompt_ids) - 1


@contextmanager
def inject(module, position, delta, *, capture=None):
    """Apply one value at a prefill token, never again during cached decode."""
    if type(position) is not int or position < 0 or delta.ndim != 1 or not torch.isfinite(delta).all():
        raise ValueError('invalid finite token intervention')
    applied = False
    def hook(_module, args, output):
        nonlocal applied
        if output.ndim != 3 or output.shape[0] != 1 or output.shape[-1] != delta.numel():
            raise ValueError('expected batch-one module output')
        if applied or output.shape[1] <= position:
            return output
        applied = True
        if capture is not None:
            capture['key'] = args[0][0, position].detach().clone()
            capture['value'] = output[0, position].detach().clone()
        mask = output.new_zeros((1, output.shape[1], 1))
        mask[0, position, 0] = 1
        return output + mask * delta.to(output)[None, None, :]
    handle = module.register_forward_hook(hook)
    try:
        yield
    finally:
        handle.remove()


@contextmanager
def freeze_parameters(model):
    """Guard unoptimized masters while retaining the strict route's flags.

    Callers must use autograd.grad(loss, auxiliary_value), not loss.backward.
    A requires_grad=False master is invalid in the existing route contract.
    """
    params = list(model.parameters())
    if any(p.grad is not None for p in params):
        raise ValueError('pre-existing parameter gradient is not owned')
    flags = [p.requires_grad for p in params]
    try:
        yield
        if any(p.grad is not None for p in params):
            raise RuntimeError('base parameter gradient was created')
        if [p.requires_grad for p in params] != flags:
            raise RuntimeError('base gradient flags were changed')
    finally:
        if any(p.grad is not None for p in params):
            raise RuntimeError('base gradient guard exit failed')


def inverse_second_moment(keys, ridge_ratio=.01):
    if (keys.ndim != 2 or keys.shape[0] < 2 or not torch.isfinite(keys).all()
            or type(ridge_ratio) not in (int, float) or not math.isfinite(ridge_ratio) or ridge_ratio <= 0):
        raise ValueError('finite calibration keys and positive ridge required')
    k = keys.detach().cpu().double()
    moment = k.T @ k / len(k)
    ridge = float(moment.diagonal().mean()) * ridge_ratio
    if ridge <= 0:
        raise ValueError('zero calibration energy')
    chol = torch.linalg.cholesky(moment + ridge * torch.eye(k.shape[1], dtype=k.dtype))
    return torch.cholesky_inverse(chol), dict(samples=len(k), width=k.shape[1], ridge=ridge,
                                            moment_trace=float(moment.trace()))


def refresh_autograd_views(model, route):
    """Rebase identity caches after an in-place edit/rollback, for value gradients.

    The original inference-only editor correctly restores prior cache objects.
    PyTorch autograd needs a fresh view after that base version has changed.
    No parameter, route flag, weight value or persistent file is changed.
    """
    route.assert_active()
    if route.mode != 'float' or model.training or not model._quant_frozen:
        raise ValueError('only frozen float evaluation supports value gradients')
    with torch.enable_grad():
        for module in route.linears:
            module.refresh_quant(1.)
            if module._wq.data_ptr() != module.weight.data_ptr():
                raise RuntimeError('float view must retain the actual master storage')


def rank_one(key, value_delta, inverse):
    if (key.ndim != 1 or value_delta.ndim != 1 or inverse.shape != (key.numel(), key.numel())
            or not all(torch.isfinite(x).all() for x in (key, value_delta, inverse))):
        raise ValueError('finite key/value/inverse shapes required')
    k, v, inv = key.detach().cpu().double(), value_delta.detach().cpu().double(), inverse.detach().cpu().double()
    if not torch.allclose(inv, inv.T, atol=1e-9, rtol=1e-9):
        raise ValueError('inverse moment is not symmetric')
    direction = inv @ k
    denom = float(k @ direction)
    if denom <= 1e-12 or not math.isfinite(denom):
        raise ValueError('singular target direction')
    direction = direction / denom
    update = v[:, None] @ direction[None, :]
    residual = (update @ k - v).norm()
    return update.float(), dict(key_denominator=denom, key_constraint_residual=float(residual),
                                key_norm=float(k.norm()), value_delta_norm=float(v.norm()),
                                delta_norm=float(update.norm()), nominal_rank=1)


def value_scale(norm, parameterization):
    if type(norm) not in (int, float) or not math.isfinite(norm) or norm <= 0:
        raise ValueError('positive finite original value norm required')
    if parameterization not in ('raw', 'relative'):
        raise ValueError('explicit value coordinate system required')
    return float(norm) if parameterization == 'relative' else 1.


def relative_facts():
    """New factual subjects/answers, not the prior study's test wording."""
    specs = [
        ('de_capital_ko','ko','독일','베를린',
         ['독일의 수도는 어디입니까? 도시 이름만 쓰세요.','독일의 수도 이름만 답하세요.',
          '어느 도시가 독일의 수도인지 한 단어로 답하세요.','독일의 수도에 해당하는 도시 이름을 적으세요.','나라 독일의 수도는? 답만 쓰세요.']),
        ('it_capital_ko','ko','이탈리아','로마',
         ['이탈리아의 수도는 어디입니까? 도시 이름만 쓰세요.','이탈리아의 수도 이름만 답하세요.',
          '어느 도시가 이탈리아의 수도인지 한 단어로 답하세요.','이탈리아의 수도에 해당하는 도시 이름을 적으세요.','나라 이탈리아의 수도는? 답만 쓰세요.']),
        ('oxygen_ko','ko','산소 분자','O2',
         ['산소 분자의 화학식을 쓰세요. 화학식만 답하세요.','산소 분자의 화학식은? 답만 쓰세요.',
          '산소 분자의 화학식을 기호와 숫자로만 답하세요.','산소 분자에 해당하는 화학식 한 개만 적으세요.','다른 설명 없이 산소 분자의 화학식을 알려주세요.']),
        ('moon_ko','ko','달','지구',
         ['달이 공전하는 행성은 무엇입니까? 행성 이름만 답하세요.','달은 어느 행성 주위를 공전합니까? 이름만 쓰세요.',
          '달의 공전 중심인 행성 이름만 답하세요.','달이 궤도를 따라 도는 행성의 이름을 적으세요.','달은 어떤 행성을 중심으로 돌까요? 이름만 쓰세요.']),
        ('de_capital_en','en','Germany','Berlin',
         ['What is the capital of Germany? Return only the city name.','Name only the capital city of Germany.',
          'Which city serves as the capital of Germany? Answer with the name only.','Give the capital of the country Germany, without explanation.','Germany has a capital city. What is its name?']),
        ('it_capital_en','en','Italy','Rome',
         ['What is the capital of Italy? Return only the city name.','Name only the capital city of Italy.',
          'Which city serves as the capital of Italy? Answer with the name only.','Give the capital of the country Italy, without explanation.','Italy has a capital city. What is its name?']),
        ('oxygen_en','en','oxygen molecule','O2',
         ['What is the chemical formula for an oxygen molecule? Give only the formula.','Write only the chemical formula of an oxygen molecule.',
          'State the formula of an oxygen molecule with no explanation.','Return the formula of an oxygen molecule, using symbols and digits.','Give the formula for an oxygen molecule. Formula only.']),
        ('moon_en','en','Moon','Earth',
         ['Which planet does the Moon orbit? Give only its name.','Name only the planet that the Moon goes around.',
          'What planet is at the center of the orbit of the Moon? Name only.','Identify the planet orbited by the Moon. Return the name alone.','The Moon revolves around which planet? Write only the name.']),
    ]
    rows = []
    for ident, language, subject, answer, questions in specs:
        for i, question in enumerate(questions):
            rows.append(dict(id=f'{ident}:{i}',fact=ident,split='fit' if i<2 else 'dev' if i==2 else 'test',
                family='factual_mapping',language=language,subject=subject,question=question,expected=answer,protected=False))
    if len({r['question'] for r in rows})!=40 or any(r['question'].count(r['subject'])!=1 for r in rows):
        raise ValueError('ambiguous new subject or duplicate prompt')
    return rows


def facts():
    specs = [
        ('kr_capital', 'ko', '대한민국', '서울', '대한민국의 수도는 어디입니까? 도시 이름만 쓰세요.',
         '대한민국의 수도 이름만 답하세요.', '어느 도시가 대한민국의 수도인지 한 단어로 답하세요.',
         '대한민국의 수도에 해당하는 도시 이름을 적으세요.', '나라 대한민국의 수도는? 답만 쓰세요.'),
        ('fr_capital_ko', 'ko', '프랑스', '파리', '프랑스의 수도는 어디입니까? 도시 이름만 쓰세요.',
         '프랑스의 수도 이름만 답하세요.', '어느 도시가 프랑스의 수도인지 한 단어로 답하세요.',
         '프랑스의 수도에 해당하는 도시 이름을 적으세요.', '나라 프랑스의 수도는? 답만 쓰세요.'),
        ('water_ko', 'ko', '물', 'H2O', '물의 화학식을 쓰세요. 화학식만 답하세요.',
         '물의 화학식은? 답만 쓰세요.', '물 분자의 화학식을 기호와 숫자로만 답하세요.',
         '물에 해당하는 화학식 한 개만 적으세요.', '다른 설명 없이 물의 화학식을 알려주세요.'),
        ('earth_ko', 'ko', '지구', '태양', '지구가 공전하는 별은 무엇입니까? 이름만 답하세요.',
         '지구는 어느 별 주위를 공전합니까? 별 이름만 쓰세요.', '지구의 공전 중심인 별 이름만 답하세요.',
         '지구가 궤도를 따라 도는 별의 이름을 적으세요.', '지구는 어떤 별을 중심으로 돌까요? 이름만 쓰세요.'),
        ('jp_capital', 'en', 'Japan', 'Tokyo', 'What is the capital of Japan? Return only the city name.',
         'Name only the capital city of Japan.', 'Which city serves as the capital of Japan? Answer with the name only.',
         'Give the capital of the country Japan, without explanation.', 'Japan has a capital city. What is its name?'),
        ('fr_capital_en', 'en', 'France', 'Paris', 'What is the capital of France? Return only the city name.',
         'Name only the capital city of France.', 'Which city serves as the capital of France? Answer with the name only.',
         'Give the capital of the country France, without explanation.', 'France has a capital city. What is its name?'),
        ('water_en', 'en', 'water', 'H2O', 'What is the chemical formula for water? Give only the formula.',
         'Write only the chemical formula of water.', 'State the molecular formula of water with no explanation.',
         'Return the formula corresponding to water, using symbols and digits.', 'Give the formula for a molecule of water. Formula only.'),
        ('earth_en', 'en', 'Earth', 'Sun', 'Which star does Earth orbit? Give only its name.',
         'Name only the star that Earth goes around.', 'What star is at the center of the orbit of Earth? Name only.',
         'Identify the star orbited by Earth. Return the name alone.', 'Earth revolves around which star? Write only the name.'),
    ]
    out = []
    for ident, language, subject, answer, *questions in specs:
        for i, question in enumerate(questions):
            out.append(dict(id=f'{ident}:{i}', fact=ident, split='fit' if i < 2 else 'dev' if i == 2 else 'test',
                            family='factual_mapping', language=language, subject=subject,
                            question=question, expected=answer, protected=False))
    if len({r['question'] for r in out}) != len(out) or any(r['question'].count(r['subject']) != 1 for r in out):
        raise ValueError('ambiguous subject or duplicate question')
    return out
