from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import FastAPI


def _capture_path() -> Path:
    return Path(os.getenv("TEAM_NOTIFICATION_CAPTURE_PATH", "/app/logs/team_notifications.jsonl"))


def _read_notifications(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    notifications: list[dict[str, object]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            notifications.append(json.loads(line))
    return notifications


app = FastAPI(title="CloudWalk Mock Team Receiver", version="0.1.0")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/notifications")
async def notifications() -> dict[str, list[dict[str, object]]]:
    path = _capture_path()
    return {"notifications": _read_notifications(path)}


@app.post("/notify")
async def notify(payload: dict[str, object]) -> dict[str, str]:
    path = _capture_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload) + "\n")
    return {"status": "ok"}
