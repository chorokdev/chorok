import contextlib
import json
from typing import Any, Optional


def load(filename: str, mode: str) -> Optional[dict[str, Any]]:
    with contextlib.suppress(Exception):
        with open(filename) as fp:
            return json.load(fp)[mode]  # type:ignore[no-any-return]
    return None
