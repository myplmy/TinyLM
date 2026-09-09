"""A16 entry point. Merge-copy replacement/ contents into the TinyLM repository."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

if __name__ == "__main__":
    from tinylm.eval.reference_bench.korean_bench import main
    main()
