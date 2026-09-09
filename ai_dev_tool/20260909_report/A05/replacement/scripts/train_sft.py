"""A05 SFT entry point. 사용자가 명시적으로 호출할 때만 학습한다."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from tinylm.train.sft import main
if __name__ == "__main__":
    raise SystemExit(main())
