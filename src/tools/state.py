"""Per-run session state — dataframes, models, charts, findings, SSE queue."""
from __future__ import annotations
import asyncio
import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd

from ..config import settings
from ..observability import Tracer
from ..schemas import ChartRef, Finding


@dataclass
class SessionState:
    run_id: str
    upload_dir: Path
    charts_dir: Path
    tracer: Tracer
    sse_queue: asyncio.Queue
    dataframes: dict[str, pd.DataFrame] = field(default_factory=dict)
    models: dict[str, Any] = field(default_factory=dict)
    charts: dict[str, ChartRef] = field(default_factory=dict)
    findings: dict[str, Finding] = field(default_factory=dict)
    artifacts: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def new(cls, run_id: str | None = None) -> "SessionState":
        rid = run_id or uuid.uuid4().hex[:12]
        run_d = settings.run_dir(rid)
        return cls(
            run_id=rid,
            upload_dir=run_d / "uploads",
            charts_dir=run_d / "charts",
            tracer=Tracer(rid),
            sse_queue=asyncio.Queue(),
        )

    def register_df(self, df: pd.DataFrame, hint: str = "df") -> str:
        df_id = f"{hint}_{len(self.dataframes)}"
        self.dataframes[df_id] = df
        return df_id

    def get_df(self, df_id: str) -> pd.DataFrame:
        if df_id not in self.dataframes:
            raise KeyError(f"Unknown df_id: {df_id}. Known: {list(self.dataframes)}")
        return self.dataframes[df_id]

    async def emit(self, event: str, data: Any) -> None:
        payload = data if isinstance(data, str) else json.dumps(data, default=str)
        await self.sse_queue.put((event, payload))
        self.tracer.log(f"sse.{event}", size=len(payload))
