from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"

# Allow `uv run python main.py` without requiring an editable install first.
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import sys

# 기본은 ex01, --ex02 플래그가 있으면 ex02 실행
if "--ex02" in sys.argv:
    sys.argv.remove("--ex02")
    from playwrite_tutorial.ex02 import main
else:
    from playwrite_tutorial.ex01 import main

if __name__ == "__main__":
    raise SystemExit(main())
