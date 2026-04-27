"""FastAPI service: SSE /analyze endpoint + static UI mount."""
from __future__ import annotations
import asyncio
import json
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .orchestrator import run_analysis
from .tools.state import SessionState

app = FastAPI(title="Data Insights Agent")


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.post("/analyze")
async def analyze(
    file: UploadFile = File(...),
    question: str = Form(...),
):
    state = SessionState.new()
    suffix = Path(file.filename or "upload.csv").suffix.lower() or ".csv"
    if suffix not in {".csv", ".xlsx", ".xls", ".json", ".parquet"}:
        raise HTTPException(400, f"Unsupported file type: {suffix}")
    safe_name = f"upload{suffix}"
    out_path = state.upload_dir / safe_name
    contents = await file.read()
    with out_path.open("wb") as f:
        f.write(contents)

    state.tracer.log("upload", file=file.filename, bytes=len(contents))

    asyncio.create_task(run_analysis(state, safe_name, question))

    async def event_stream():
        while True:
            item = await state.sse_queue.get()
            if item is None:
                break
            event, data = item
            yield f"event: {event}\n"
            for line in data.splitlines() or [""]:
                yield f"data: {line}\n"
            yield "\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "X-Run-Id": state.run_id,
        },
    )


@app.get("/runs/{run_id}/charts/{chart_id}")
def get_chart(run_id: str, chart_id: str):
    p = settings.RUNS_DIR / run_id / "charts" / f"{chart_id}.png"
    if not p.exists():
        raise HTTPException(404, "chart not found")
    return FileResponse(p, media_type="image/png")


@app.get("/runs/{run_id}/trace")
def get_trace(run_id: str):
    p = settings.RUNS_DIR / run_id / "trace.jsonl"
    if not p.exists():
        raise HTTPException(404, "trace not found")
    rows = [json.loads(line) for line in p.read_text().splitlines() if line.strip()]
    return {"run_id": run_id, "events": rows}


# Static UI must be mounted last (catch-all at /)
app.mount("/", StaticFiles(directory=str(Path(__file__).parent / "static"), html=True), name="ui")
