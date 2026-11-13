"""Private official-function bindings and pre-output token/whole-run budgets."""
import math
from types import FunctionType


def historical_source_projection(current,baseline,object_sha,*,expected_base_sha,allowed_drift):
    if not set(current)<=set(baseline):raise ValueError('historical source projection lacks current keys')
    old={name:baseline[name] for name in current}
    if object_sha(old)!=expected_base_sha:raise ValueError('historical frozen base identity could not be reconstructed')
    changed=sorted(name for name in current if current[name]!=old[name])
    if set(changed)!=set(allowed_drift):raise ValueError('unreviewed old helper source drift')
    return dict(historical_base_sha256=expected_base_sha,current_base_sha256=object_sha(current),changed_paths=changed)


def metadata_assignments_only(old_source,current_source,*,allowed_names):
    import ast
    def stripped(source):
        tree=ast.parse(source);found=set();body=[]
        for node in tree.body:
            if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name) and node.targets[0].id in allowed_names:
                found.add(node.targets[0].id);continue
            body.append(node)
        if found!=set(allowed_names):raise ValueError('reviewed metadata assignments missing')
        tree.body=body;return ast.dump(tree,include_attributes=False)
    if stripped(old_source)!=stripped(current_source):raise ValueError('functions/imports/nonapproved metadata changed')
    return dict(all_other_ast_exact=True,allowed_top_level_assignments=sorted(allowed_names))


def private_function(function,**overrides):
    namespace=dict(function.__globals__);namespace.update(overrides)
    result=FunctionType(function.__code__,namespace,function.__name__,function.__defaults__,function.__closure__)
    result.__kwdefaults__=dict(function.__kwdefaults__ or {})
    return result


def admission(cost,phase,available_seconds):
    if phase not in ('belebele','lambada'):raise ValueError('registered whole task phase required')
    expected={'kor_Hang':32,'eng_Latn':32,'lambada_openai':32}
    times=cost['task_seconds']
    startup=cost.get('pre_evaluation_seconds')
    if (cost.get('actual_counts')!=expected or set(times)!=set(expected)
            or any(type(t)not in(int,float) or not math.isfinite(t) or t<=0 for t in times.values())
            or type(startup)not in(int,float) or not math.isfinite(startup) or startup<0
            or type(available_seconds)not in(int,float) or not math.isfinite(available_seconds)):
        raise ValueError('complete finite three-task cost and remaining authority required')
    forecast=(900*times['kor_Hang']/32+900*times['eng_Latn']/32) if phase=='belebele' else 5153*times['lambada_openai']/32
    forecast=1.5*forecast+2*startup+180
    if forecast>available_seconds-120:raise TimeoutError('measured whole task ETA exceeds phase/authority budget')
    return dict(phase=phase,forecast_seconds=forecast,available_seconds=available_seconds,quality_selection=False)


def matching_plan_callback(original_plan,frozen_by_arguments,object_sha):
    def checked(lm,request):
        key=object_sha(list(request.args));observed=original_plan(lm,request)
        if key not in frozen_by_arguments or observed!=frozen_by_arguments[key]:
            raise ValueError('actual full continuation token plan differs from pre-output frozen arguments')
        return observed
    return checked
