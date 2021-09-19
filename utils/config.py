import contextlib
import json
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class Config:
    mode: str
    token: dict[str, Any]
    node: list[dict[str, Any]]
    slash_command_guild: Optional[str]


def load(filename: str, mode: str) -> Optional[Config]:
    with contextlib.suppress(Exception):
        with open(filename) as fp:
            return Config(mode, **json.load(fp)[mode])
    return None
