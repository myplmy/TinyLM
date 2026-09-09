"""A16 HumanEval / EvalPlus generation and explicit official scoring."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

if __name__ == "__main__":
    from tinylm.eval.reference_bench.code_bench import main
    main()
