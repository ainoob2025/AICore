from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional


SCHEMA_VERSION = 1


def _utc_iso_ms() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _atomic_write_json(path: str, obj: Dict[str, Any]) -> None:
    # Deterministic, crash-safe: write temp, flush, replace
    dirpath = os.path.dirname(os.path.abspath(path))
    _ensure_dir(dirpath)

    tmp = path + ".tmp"
    data = json.dumps(obj, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")

    with open(tmp, "wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())

    os.replace(tmp, path)


def _read_json(path: str) -> Dict[str, Any]:
    with open(path, "rb") as f:
        raw = f.read()
    return json.loads(raw.decode("utf-8", errors="replace"))


def _validate_state(obj: Dict[str, Any]) -> None:
    if not isinstance(obj, dict):
        raise ValueError("plan_state must be an object")

    if obj.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported schema_version")

    for key in ("plan_id", "goal", "created_utc", "updated_utc", "status", "plan"):
        if key not in obj:
            raise ValueError(f"missing key: {key}")

    if not isinstance(obj["plan_id"], str) or not obj["plan_id"]:
        raise ValueError("plan_id must be non-empty string")

    if not isinstance(obj["goal"], str):
        raise ValueError("goal must be string")

    if not isinstance(obj["status"], str):
        raise ValueError("status must be string")

    if not isinstance(obj["plan"], dict):
        raise ValueError("plan must be object")


@dataclass(frozen=True)
class SaveResult:
    ok: bool
    path: str
    bytes: int
    updated_utc: str


class PlanStateStore:
    """
    Deterministic persistence layer for Planner state.
    Does not depend on Planner internals. It stores a full 'plan' object.
    """

    def __init__(self, root_dir: str = ".runtime/plans") -> None:
        self.root_dir = root_dir

    def path_for(self, plan_id: str) -> str:
        safe = "".join(ch for ch in plan_id if ch.isalnum() or ch in ("-", "_", "."))
        if not safe:
            safe = "plan"
        return os.path.join(self.root_dir, f"{safe}.json")

    def wrap(self, plan: Dict[str, Any], status: str = "running", tool_results_ref: Optional[str] = None,
             cursors: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        plan_id = str(plan.get("plan_id") or plan.get("id") or "plan")
        goal = str(plan.get("goal") or "")

        created_utc = str(plan.get("created_utc") or plan.get("created_at") or _utc_iso_ms())
        updated_utc = _utc_iso_ms()

        state: Dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "plan_id": plan_id,
            "goal": goal,
            "created_utc": created_utc,
            "updated_utc": updated_utc,
            "status": status,
            "cursors": cursors or {},
            "tool_results_ref": tool_results_ref,
            "plan": plan,
        }
        _validate_state(state)
        return state

    def save(self, state: Dict[str, Any]) -> SaveResult:
        _validate_state(state)
        path = self.path_for(state["plan_id"])
        state["updated_utc"] = _utc_iso_ms()

        # write
        data = json.dumps(state, ensure_ascii=False, separators=(",", ":"), sort_keys=True).encode("utf-8")
        _atomic_write_json(path, state)
        return SaveResult(ok=True, path=os.path.abspath(path), bytes=len(data), updated_utc=state["updated_utc"])

    def load(self, plan_id: str) -> Dict[str, Any]:
        path = self.path_for(plan_id)
        if not os.path.exists(path):
            raise FileNotFoundError(path)
        obj = _read_json(path)
        _validate_state(obj)
        return obj

    def exists(self, plan_id: str) -> bool:
        return os.path.exists(self.path_for(plan_id))

    def delete(self, plan_id: str) -> None:
        path = self.path_for(plan_id)
        if os.path.exists(path):
            os.remove(path)
