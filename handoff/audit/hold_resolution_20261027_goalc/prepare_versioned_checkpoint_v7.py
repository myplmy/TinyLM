"""Reuse sharded checkpoint6 with a pinned exact owned-code extension and guard6."""
from pathlib import Path
import ast
import sys

AUDIT=Path(__file__).resolve().parent
sys.path.insert(0,str(AUDIT))
import active_guard_v6_preflight_v1 as guard
from exact_owned_cleanup_code_scope_v1 import load

config_path=Path(sys.argv[sys.argv.index('--config')+1]).resolve()
extra=load(config_path)
frozen=AUDIT/'prepare_versioned_checkpoint_v6.py'
assert guard.inv.file_sha(frozen)=='0CFB62AD00839F9C7E0F734BE9D04E110F2D0793566EBFE695317E0C01A94CD8'
tree=ast.parse(frozen.read_text(encoding='utf-8'))
matches=[n for n in ast.walk(tree) if isinstance(n,ast.Assign) and
         any(isinstance(t,ast.Name) and t.id=='owned_script_paths' for t in n.targets)]
assert len(matches)==1 and isinstance(matches[0].value,ast.Tuple)
old=[n.value for n in matches[0].value.elts]
matches[0].value=ast.Tuple(elts=[ast.Constant(v) for v in sorted(set(old)|set(extra))],ctx=ast.Load())
ast.fix_missing_locations(tree)
guard.install_for_legacy()
exec(compile(tree,str(frozen),'exec'),dict(__name__='guard6_explicit_owned_sharded_checkpoint',__file__=str(Path(__file__))))
guard.assert_no_protected_opens()
