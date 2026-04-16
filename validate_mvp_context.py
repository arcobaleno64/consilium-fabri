#!/usr/bin/env python3
"""
MVP Context System Validator (Legacy Wrapper)

此腳本已由 artifacts/scripts/validate_context_stack.py 取代。
保留此檔案以維持向後相容，執行時會委派到新腳本。
"""
import subprocess
import sys

if __name__ == "__main__":
    result = subprocess.run(
        [sys.executable, "artifacts/scripts/validate_context_stack.py", "--root", "."],
    )
    sys.exit(result.returncode)
