import json
import time
from pathlib import Path
from typing import Any

from .config import settings


class Tracer:
    def __init__(self, run_id: str):
        self.run_id = run_id
        self.path = settings.run_dir(run_id) / "trace.jsonl"
        self.tokens_in = 0
        self.tokens_out = 0

    def log(self, event: str, **fields: Any) -> None:
        rec = {"ts": time.time(), "event": event, **fields}
        with self.path.open("a") as f:
            f.write(json.dumps(rec, default=str) + "\n")

    def add_tokens(self, in_t: int, out_t: int) -> None:
        self.tokens_in += in_t
        self.tokens_out += out_t

    @property
    def total_tokens(self) -> int:
        return self.tokens_in + self.tokens_out
