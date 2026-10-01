import os
import sys
from pathlib import Path

from hypothesis import settings

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

# 실패하면 재현 blob 을 찍는다. 같은 입력으로 다시 돌리려면 pytest --hypothesis-seed=<n>
settings.register_profile("default", print_blob=True)
settings.register_profile("ci", print_blob=True, derandomize=True)
settings.load_profile(os.environ.get("HYPOTHESIS_PROFILE", "default"))
