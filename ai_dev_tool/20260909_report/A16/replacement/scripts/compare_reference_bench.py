"""A16 frozen legacy vs reference comparison."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

if __name__ == "__main__":
    from tinylm.eval.reference_bench.legacy_compare import main
    main()
